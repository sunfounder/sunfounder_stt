"""STT base class — button-controlled recording -> transcription.

No VAD, no wake-word, no keyboard.  The caller (e.g. main.py) reads
the USR button via I2C and calls ``start_listening()`` / ``stop_listening()``.
"""

import io
import subprocess
import sys
import threading
import time
import wave


def _dbg(msg: str) -> None:
    """Print a debug message to stderr with ``[STT]`` prefix.

    Args:
        msg: Debug message string.

    Returns:
        None
    """
    print(f"[STT] {msg}", file=sys.stderr, flush=True)


class STTBase:
    """Base class for push-to-talk speech-to-text.

    Subclasses implement ``_transcribe()``.

    Args:
        samplerate: audio sample rate (default 16000).
        language:   language code passed to the transcription engine.
    """

    def __init__(self, samplerate=16000, language="en"):
        """Initialize STT base.

        Args:
            samplerate: Audio sample rate in Hz (default 16000).
            language: Language code passed to the transcription engine
                      (e.g. ``"zh"``, ``"en"``).
        """
        self.samplerate = samplerate
        self.language = language
        self._frames = []           # accumulated PCM frame blocks
        self._recording = False
        self._result = None
        self._ready = False
        self._proc = None
        self._reader_thread = None

    # ---- public API ----

    def start_listening(self):
        """Spawn arecord and begin capturing raw PCM.

        Launches ``arecord -D hw:0,2`` to capture S16_LE mono audio at the
        configured sample rate. A background reader thread accumulates PCM
        frames into ``self._frames``.

        Returns:
            None
        """
        if self._recording:
            return
        self._frames = []
        self._result = None
        self._ready = False
        self._recording = True

        self._proc = subprocess.Popen(
            ["arecord", "-D", "hw:0,2", "-t", "raw",
             "-f", "S16_LE", "-r", str(self.samplerate), "-c", "1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

        def _reader():
            chunk = int(self.samplerate * 0.03) * 2  # 30ms of S16_LE mono
            while self._recording:
                data = self._proc.stdout.read(chunk)
                if not data:
                    break
                self._frames.append(data)

        self._reader_thread = threading.Thread(target=_reader, daemon=True)
        self._reader_thread.start()

    def stop_listening(self):
        """Terminate arecord, save WAV, and start transcription.

        Kills the ``arecord`` process, joins the reader thread, concatenates
        accumulated PCM frames, saves a WAV file to
        ``/app/audio_output/stt_last.wav``, and spawns :meth:`_transcribe` in
        a background thread.

        Returns:
            None
        """
        if not self._recording:
            return
        self._recording = False

        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()
            self._proc = None

        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=2)
            self._reader_thread = None

        audio = b"".join(self._frames)
        if audio:
            self._frames = [audio]  # replace with single block for _transcribe()
            wav = self._pcm_to_wav(audio)
            with open("/app/audio_output/stt_last.wav", "wb") as f:
                f.write(wav)
            _dbg(f"saved {len(audio)} bytes pcm -> /app/audio_output/stt_last.wav")
        else:
            _dbg("no audio captured")

        threading.Thread(target=self._transcribe, daemon=True).start()

    def get_result(self, timeout=30) -> str:
        """Block until transcription completes and return the result.

        Polls :meth:`is_ready` at 50 ms intervals.

        Args:
            timeout: Maximum number of seconds to wait (default 30).

        Returns:
            str: Transcribed text, or ``""`` on timeout / empty audio.
        """
        deadline = time.time() + timeout
        while not self._ready:
            if time.time() > deadline:
                _dbg("get_result timed out")
                break
            time.sleep(0.05)
        self._ready = False
        result = self._result
        self._result = None
        return result or ""

    def is_ready(self) -> bool:
        """Check if a transcription result is available.

        Returns:
            bool: ``True`` if transcription has completed and result can be read
                  via :meth:`get_result`.
        """
        return self._ready

    def reset(self):
        """Reset to idle — stop recording and discard pending results.

        If currently recording, stops capture (terminates arecord, waits for
        reader thread). Clears accumulated audio frames and transcription state.

        Returns:
            None
        """
        if self._recording:
            self.stop_listening()
        self._frames = []
        self._result = None
        self._ready = False

    def set_wake_words(self, words):
        """No-op kept for API compatibility with wake-word based STT engines.

        Args:
            words: Ignored.
        """
        pass  # no-op for API compatibility

    # ---- internal ----

    def _transcribe(self):
        """Run the engine-specific transcription.

        Must be implemented by subclasses. Called in a background thread
        after :meth:`stop_listening` converts PCM to WAV.

        Raises:
            NotImplementedError: If the subclass does not override this method.
        """
        raise NotImplementedError

    # ---- helpers ----

    def _pcm_to_wav(self, pcm: bytes) -> bytes:
        """Convert raw PCM (S16_LE mono) to WAV bytes in memory.

        Args:
            pcm: Raw S16_LE mono PCM audio bytes.

        Returns:
            bytes: Complete WAV file with RIFF header.
        """
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.samplerate)
            wf.writeframes(pcm)
        buf.seek(0)
        return buf.read()
