"""ALSA direct PCM capture via ctypes.

Minimal wrapper around libasound — no PortAudio, no PulseAudio.
Used inside Docker containers where /dev/snd is passed through
but the host's sound server socket is not available.
"""

import ctypes as _ct


_LIBASOUND = None
try:
    _LIBASOUND = _ct.cdll.LoadLibrary("libasound.so.2")
    _LIBASOUND.snd_strerror.restype = _ct.c_char_p
except OSError:
    pass


def is_available() -> bool:
    """Check if ALSA direct capture is available.

    Returns:
        bool: ``True`` if ``libasound.so.2`` was loaded successfully.
    """
    return _LIBASOUND is not None


class AlsaCapture:
    """Blocking ALSA PCM capture via ctypes.

    Args:
        device:     ALSA PCM device name, e.g. ``"hw:0,2"``.
        samplerate: sample rate in Hz (default 16000).
        blocksize:  frames per read (default 480 = 30 ms @ 16 kHz).
        channels:   number of channels (default 1).
    """

    def __init__(self, device="hw:0,2", samplerate=16000, blocksize=480,
                 channels=1):
        if not is_available():
            raise OSError("libasound.so.2 not found — ALSA capture unavailable")
        self._device = device.encode()
        self._samplerate = samplerate
        self._blocksize = blocksize
        self._channels = channels
        self._handle = _ct.c_void_p()
        self._running = False
        self._callback = None

    # ---- context manager ----

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

    # ---- public API ----

    def open(self):
        lib = _LIBASOUND
        ret = lib.snd_pcm_open(
            _ct.byref(self._handle), self._device,
            0,   # SND_PCM_STREAM_CAPTURE
            0,   # blocking mode
        )
        if ret < 0:
            err = lib.snd_strerror(ret).decode() if ret < 0 else "unknown"
            raise OSError(f"ALSA open failed: {err}")

        hw = _ct.c_void_p()
        lib.snd_pcm_hw_params_malloc(_ct.byref(hw))
        lib.snd_pcm_hw_params_any(self._handle, hw)
        lib.snd_pcm_hw_params_set_access(self._handle, hw, 3)   # RW_INTERLEAVED
        lib.snd_pcm_hw_params_set_format(self._handle, hw, 2)    # S16_LE
        lib.snd_pcm_hw_params_set_channels(self._handle, hw, self._channels)
        rate = _ct.c_uint(self._samplerate)
        lib.snd_pcm_hw_params_set_rate_near(self._handle, hw,
                                            _ct.byref(rate), None)
        lib.snd_pcm_hw_params(self._handle, hw)
        lib.snd_pcm_hw_params_free(hw)
        self._running = True

    def close(self):
        self._running = False
        if self._handle:
            _LIBASOUND.snd_pcm_drop(self._handle)
            _LIBASOUND.snd_pcm_close(self._handle)
            self._handle = None

    def read(self) -> bytes:
        """Read one block of PCM frames. Returns empty bytes on error."""
        if not self._running:
            return b""
        lib = _LIBASOUND
        buf = (_ct.c_int16 * (self._blocksize * self._channels))()
        frames = lib.snd_pcm_readi(self._handle, buf, self._blocksize)
        if frames > 0:
            return bytes(buf[:frames * self._channels])
        if frames == -32:  # EPIPE = overrun
            lib.snd_pcm_prepare(self._handle)
        return b""

    def read_loop(self, callback):
        """Blocking read loop — call from a background thread.

        Args:
            callback: ``callable(bytes)`` invoked for each frame block.
        """
        while self._running:
            data = self.read()
            if data:
                callback(data)
