"""sunfounder_stt — Speech-to-Text brick.

Push-to-talk style: press button → record → press again → transcribe.

Three backends via the unified ``STT`` class:

- ``local_standard`` — whisper.cpp GGML model (pywhispercpp)
- ``local_fast``     — faster-whisper CTranslate2 (int8 CPU)
- ``online``         — OpenAI Whisper API (cloud)

Usage::

    from sunfounder_stt import STT
    stt = STT(type="local_fast", language="zh")
"""

from ._version import __version__
from .stt_whisper import WhisperSTT

STT = WhisperSTT  # default engine shortcut

__all__ = ["STT", "__version__"]