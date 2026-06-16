# CLAUDE.md

This file provides guidance to Claude Code when working with the `sunfounder_stt` library.

## Overview

`sunfounder_stt` provides push-to-talk speech-to-text with three interchangeable backends, all through a single `STT` class. Designed for embedded Linux (QCM2290) with ALSA audio capture.

```
PTT button → start_listening() → arecord hw:0,2 → stop_listening() → _transcribe() → get_result()
```

## Public API

Exported from `sunfounder_stt/__init__.py`:

| Symbol | Purpose |
|---|---|
| `STT` | Main class (alias for `WhisperSTT`) |
| `__version__` | Version string |

### `STT` constructor

```python
from sunfounder_stt import STT

stt = STT(type="local_fast", language="zh")                 # faster-whisper (current)
stt = STT(type="local_standard", model="/app/models/ggml-tiny.bin", language="zh")  # whisper.cpp
stt = STT(type="online")                                    # OpenAI Whisper API
```

| Parameter | Default | Description |
|---|---|---|
| `type` | `"local_standard"` | `"local_standard"` / `"local_fast"` / `"online"` |
| `model` | `None` | Model path (local_standard) or size (local_fast). Auto-defaults to `"tiny"` |
| `language` | `"auto"` | Language code: `"zh"`, `"en"`, etc. |

### PTT lifecycle methods (inherited from `STTBase`)

| Method | Description |
|---|---|
| `start_listening()` | Spawns `arecord -D hw:0,2 -t raw -f S16_LE -r 16000 -c 1`, starts reader thread |
| `stop_listening()` | Kills `arecord`, converts PCM→WAV, saves to `/app/audio_output/stt_last.wav`, spawns `_transcribe()` in background |
| `get_result(timeout=30)` | Blocks until transcription ready, returns `str` (empty on timeout/silence) |
| `is_ready()` | Returns `True` if transcription complete |
| `reset()` | Stop recording, discard pending results |

## Three backends

| `type=` | Engine | Python package | Model |
|---|---|---|---|
| `local_standard` | whisper.cpp GGML | `pywhispercpp` | `/app/models/ggml-tiny.bin` (42MB) |
| `local_fast` | faster-whisper CTranslate2 | `faster_whisper` | int8 CPU, auto-download ~72MB |
| `online` | OpenAI Whisper API | `requests` | `whisper-1` (cloud) |

### Engine init details

- **local_standard**: Suppresses stderr during `Model()` init (whisper.cpp dumps architecture/memory info to stderr). Uses `os.dup2()` trick to redirect then restore.
- **local_fast**: `WhisperModel(model_size, device="cpu", compute_type="int8")` — CPU-only, int8 quantized.
- **online**: Stateless, uses `requests.post()` to `api.openai.com/v1/audio/transcriptions`. Requires `STT.API_KEY = "sk-..."` (class-level attribute).

### `_transcribe()` flow

1. Concatenates accumulated PCM `_frames` into single `bytes`
2. Converts PCM → WAV via `_pcm_to_wav()` (uses `wave` module)
3. Calls engine-specific transcribe method
4. Sets `self._result` and `self._ready = True`

### PCM → WAV helper

`_pcm_to_wav(pcm: bytes) -> bytes`: Wraps raw S16_LE mono PCM in a RIFF WAV container using Python's `wave` module. No external tools needed.

## Internal modules (not exported)

| Module | Purpose |
|---|---|
| `_stt_base.py` | `STTBase` — recording lifecycle, PCM→WAV, `get_result()` blocking wait |
| `_alsa_capture.py` | `AlsaCapture` — direct ALSA via `ctypes` on `libasound.so.2` |
| `_pulse_audio_capture.py` | `PulseAudioCapture` — PulseAudio fallback via `libpulse-simple` ctypes |

## Audio capture architecture

Primary path (used by `STTBase`):
```
arecord -D hw:0,2   →   S16_LE, 16000Hz, mono   →   raw PCM frames
```

`AlsaCapture` and `PulseAudioCapture` are alternative capture backends used by the legacy `openai_stt.py` module (sounddevice → PulseAudio → ALSA fallback chain). They are NOT used by the main `STT` class but are kept for compatibility.

## Dependencies

- **`[project] dependencies`**: `requests>=2.25`
- **`[project.optional-dependencies] local_standard`**: `pywhispercpp>=0.1`
- **`[project.optional-dependencies] local_fast`**: `faster-whisper>=1.0`
- **System**: `arecord` (alsa-utils), ALSA `hw:0,2` capture device
- **No Arduino Bridge dependency** — this library is pure Python + ALSA

## Testing

```bash
# Local faster-whisper (needs -it for keyboard interaction)
docker exec -it uno-q-ai-robot-puls-main-1 python -u /app/python-libraries/sunfounder_stt/examples/stt_whisper_local.py

# Online OpenAI
docker exec uno-q-ai-robot-puls-main-1 python /app/python-libraries/sunfounder_stt/examples/stt_whisper_online.py
```

## Code conventions

- `_dbg()` helper in `_stt_base.py` prints to stderr with `[STT]` prefix, `flush=True`
- Engine is lazy-initialized on first `_transcribe()` call, not in `__init__`
- All audio output goes to `/app/audio_output/` (container path)
- `start_listening()` / `stop_listening()` are idempotent — calling twice is safe
