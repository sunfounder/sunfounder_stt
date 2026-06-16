"""STT via OpenAI Whisper — unified entry for all backends.

One file, one class, three backends::

    from sunfounder_stt import STT

    # local — whisper.cpp
    stt = STT(type="local_standard", model="/app/models/ggml-tiny.bin", language="zh")

    # local — faster-whisper
    stt = STT(type="local_fast", language="zh")

    # online — OpenAI Whisper API
    STT.API_KEY = "sk-..."
    stt = STT(type="online")
"""

import io
import os
import tempfile

import requests

from ._stt_base import STTBase


class WhisperSTT(STTBase):
    """Unified Whisper STT.

    Args:
        type: ``"local_standard"`` (whisper.cpp, default),
              ``"local_fast"`` (faster-whisper),
              ``"online"`` (OpenAI Whisper API).
        model: model name or path (only for local_standard / local_fast).
        language: language code, e.g. ``"zh"``, ``"en"``, ``"auto"``.
    """

    TYPES = ("local_standard", "local_fast", "online")
    API_KEY = ""
    WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"

    def __init__(self, type="local_standard", model=None, language="auto", **kwargs):
        super().__init__(language=language, **kwargs)
        if type not in self.TYPES:
            raise ValueError(f"Unknown type: {type}, expected one of {self.TYPES}")
        self._type = type
        self._model_arg = model
        self._engine = None  # lazy init

    # ---- public ----

    def _transcribe(self):
        if self._engine is None:
            self._engine = self._init_engine()

        audio = b"".join(self._frames)
        if not audio:
            self._result = ""
            self._ready = True
            return

        if self._type == "online":
            self._transcribe_online(audio)
        else:
            self._transcribe_local(audio)

    # ---- engine init ----

    def _init_engine(self):
        if self._type == "local_standard":
            import os as _os
            from pywhispercpp.model import Model
            model = self._model_arg or "tiny"
            # Suppress whisper.cpp init dump (model architecture, memory, etc.)
            _stderr = _os.dup(2)
            _os.close(2)
            _os.open(_os.devnull, _os.O_WRONLY)
            try:
                m = Model(model, print_progress=False)
            finally:
                _os.dup2(_stderr, 2)
                _os.close(_stderr)
            return m
        elif self._type == "local_fast":
            from faster_whisper import WhisperModel
            model_size = self._model_arg or "tiny"
            return WhisperModel(model_size, device="cpu", compute_type="int8")
        elif self._type == "online":
            return None  # stateless, uses requests

    # ---- local (ggml / ct2) ----

    def _transcribe_local(self, audio):
        wav_bytes = self._pcm_to_wav(audio)
        if self._type == "local_standard":
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            try:
                tmp.write(wav_bytes)
                tmp.close()
                segments = self._engine.transcribe(tmp.name, language=self.language)
                self._result = " ".join(s.text for s in segments).strip()
            finally:
                os.unlink(tmp.name)
        else:  # local_fast
            wav_file = io.BytesIO(wav_bytes)
            segments, _ = self._engine.transcribe(wav_file, language=self.language)
            self._result = " ".join(s.text for s in segments).strip()
        self._ready = True

    # ---- online ----

    def _transcribe_online(self, audio):
        wav_bytes = self._pcm_to_wav(audio)
        try:
            resp = requests.post(
                self.WHISPER_URL,
                files={"file": ("audio.wav", wav_bytes, "audio/wav")},
                data={"model": "whisper-1", "language": self.language},
                headers={"Authorization": f"Bearer {self.API_KEY}"},
                timeout=30,
            )
            resp.raise_for_status()
            self._result = resp.json().get("text", "").strip()
        except Exception as e:
            self._result = ""
            print(f"[STT] online error: {e}", flush=True)
        self._ready = True
