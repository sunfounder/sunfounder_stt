"""sunfounder_stt — Speech-to-Text brick.

Push-to-talk style: press button → record → press again → transcribe.

Three backends via the unified ``STT`` class:

- ``local_standard`` — whisper.cpp GGML model (pywhispercpp)
- ``local_fast``     — faster-whisper CTranslate2 (int8 CPU)
- ``online``         — OpenAI Whisper API (cloud)

Usage::

    from sunfounder_stt import STT

    # local — whisper.cpp GGML (fastest, 42 MB model)
    stt = STT(type="local_standard", model="/app/models/ggml-tiny.bin", language="zh")

    # local — faster-whisper CTranslate2 (int8 CPU, auto-download ~72 MB)
    stt = STT(type="local_fast", language="zh")

    # online — OpenAI Whisper API
    STT.API_KEY = "sk-..."
    stt = STT(type="online")

    # PTT lifecycle
    stt.start_listening()
    # ... user speaks ...
    stt.stop_listening()
    text = stt.get_result(timeout=30)
    print(text)
"""

from ._version import __version__
from .stt_whisper import WhisperSTT

STT = WhisperSTT  # default engine shortcut

__all__ = ["STT", "__version__"]