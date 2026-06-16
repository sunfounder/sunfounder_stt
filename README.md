# sunfounder_stt

Speech-to-Text brick — push-to-talk recording via ALSA, transcription via Whisper.

## Engines

All backends accessed through a single `STT` class — switch by changing the `type=` parameter:

```python
from sunfounder_stt import STT
```

| `type=` | Engine | Online | Notes |
|---|---|---|---|
| `local_fast` **(default)** | faster-whisper CTranslate2 | No | int8 CPU, auto-downloads ~72 MB |
| `local_standard` | whisper.cpp GGML | No | needs `model=` path, e.g. `/app/models/ggml-tiny.bin` (42 MB) |
| `online` | OpenAI Whisper API | Yes | needs `API_KEY` and internet |

## Usage

### local_fast — faster-whisper (default, recommended)

```python
from sunfounder_stt import STT

stt = STT(type="local_fast", language="zh")

# Button press
stt.start_listening()
# ... user speaks ...

# Button release
stt.stop_listening()
text = stt.get_result()  # blocks until done, returns transcribed text
```

### local_standard — whisper.cpp GGML

```python
stt = STT(type="local_standard", model="/app/models/ggml-tiny.bin", language="zh")
# same API: start_listening() / stop_listening() / get_result()
```

### online — OpenAI Whisper API

```python
STT.API_KEY = "sk-..."
stt = STT(type="online", language="zh")
# same API
```

## API Reference

| Method | Description |
|---|---|
| `start_listening()` | Spawn `arecord -D hw:0,2` and begin capturing PCM |
| `stop_listening()` | Terminate capture, save WAV, trigger transcription |
| `get_result(timeout=30) -> str` | Block until transcription completes (empty string on timeout) |
| `is_ready() -> bool` | Has transcription completed? (non-blocking) |
| `reset()` | Discard pending recording and result |

### Constructor parameters

| Parameter | Default | Description |
|---|---|---|
| `type` | `"local_fast"` | Backend: `"local_fast"`, `"local_standard"`, or `"online"` |
| `model` | `None` | Model path for local backends (`"tiny"` if omitted) |
| `language` | `"en"` | Language code, e.g. `"zh"`, `"en"`, `"auto"` |
| `samplerate` | `16000` | Audio sample rate in Hz |

## Audio Capture

Audio is captured via ALSA direct: `arecord -D hw:0,2` (S16_LE, 16000 Hz, mono). PCM saved as WAV to `/app/audio_output/stt_last.wav`.

The Qualcomm Codec capture mixer is configured at container startup by `setup_audio_output()` in `robot_shield`.

Host pre-requisite:
```bash
systemctl --user stop pipewire pipewire-pulse wireplumber
```

## Dependencies

- `faster-whisper` (for `local_fast`; default)
- `pywhispercpp` (for `local_standard`)
- `requests` (for `online`)
- `arecord` from alsa-utils (system package)
