# sunfounder_stt

Speech-to-Text brick — push-to-talk recording via ALSA, transcription via Whisper.

## How it works

```
Button long-press → start recording → speak → release → transcribe → get text
```

The caller (e.g. `main.py`) monitors the USR button via I2C register `REG_USR_KEY_SIGNAL` (0x0C)
and calls `start_listening()` / `stop_listening()` accordingly.

## Engines

All backends are accessed through a single unified class — switch by changing the `type=` parameter:

```python
from sunfounder_stt import STT
```

| `type=` | Engine | Online | Notes |
|---|---|---|---|
| `local_fast` **(default)** | faster-whisper CTranslate2 | No | int8 CPU, auto-downloads ~72 MB |
| `local_standard` | whisper.cpp GGML | No | needs `model=` path, e.g. `/app/models/ggml-tiny.bin` (42 MB) |
| `online` | OpenAI Whisper API | Yes | needs `API_KEY` and internet |

## Dependencies

- `faster-whisper` (for `local_fast`; default)
- `pywhispercpp` (for `local_standard`)
- `requests` (for `online`)
- `arecord` from alsa-utils (system package, for audio capture)

The container must have `/dev/snd/pcmC0D2c` accessible and the capture mixer configured (see Audio setup below).

## Usage

### Local — faster-whisper (default, recommended)

```python
from sunfounder_stt import STT

stt = STT(type="local_fast", language="zh")

# Button press
stt.start_listening()
# ... user speaks ...

# Button release
stt.stop_listening()

text = stt.get_result()  # blocks until done, returns "今天天气怎么样？"
```

### Local — whisper.cpp (GGML)

```python
stt = STT(type="local_standard", model="/app/models/ggml-tiny.bin", language="zh")
# same API: start_listening() / stop_listening() / get_result()
```

### Online — OpenAI Whisper API

```python
STT.API_KEY = "sk-..."
stt = STT(type="online", language="zh")
# same API
```

## API reference

| Method | Description |
|---|---|
| `start_listening()` | Spawn `arecord -D hw:0,2` and start capturing PCM |
| `stop_listening()` | Terminate capture, save WAV to `/app/audio_output/stt_last.wav`, trigger transcription |
| `get_result(timeout=30) -> str` | Block until transcription completes, return text (empty string on timeout) |
| `is_ready() -> bool` | Has transcription completed? (non-blocking) |
| `reset()` | Discard pending recording and result |
| `set_wake_words(words)` | No-op — included for API compatibility |

### Constructor parameters

| Parameter | Default | Description |
|---|---|---|
| `type` | `"local_standard"` | Backend: `"local_standard"`, `"local_fast"`, or `"online"` |
| `model` | `None` | Model name/path for local backends (`"tiny"` if omitted) |
| `language` | `"en"` | Language code, e.g. `"zh"`, `"en"`, `"auto"` |
| `samplerate` | `16000` | Audio sample rate in Hz |

## Audio setup

Audio capture uses ALSA direct via `arecord -D hw:0,2` (S16_LE, 16000 Hz, mono).
The Qualcomm Codec capture mixer is configured automatically at container startup
by `setup_audio_output()` in `python-libraries/robot_shield/audio.py`.

Host pre-requisite:
```bash
systemctl --user stop pipewire pipewire-pulse wireplumber
```
