"""PulseAudio capture via libpulse-simple ctypes.

Fallback when ALSA/PortAudio has no input devices (e.g. Qualcomm SoC
where audio routing requires PipeWire).
"""

import ctypes
import os
import threading

_LIB = None
try:
    _LIB = ctypes.cdll.LoadLibrary("libpulse-simple.so.0")
except OSError:
    pass

PA_STREAM_RECORD = 2
PA_SAMPLE_S16LE = 3


class _SampleSpec(ctypes.Structure):
    """Ctypes mirror of PulseAudio ``pa_sample_spec`` — format, rate, channels."""

    _fields_ = [
        ("format", ctypes.c_int),
        ("rate", ctypes.c_uint32),
        ("channels", ctypes.c_uint8),
    ]


def _setup_signatures():
    """Configure libpulse-simple ctypes argument and return types.

    Returns:
        None
    """
    lib = _LIB
    lib.pa_simple_new.argtypes = [
        ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int,
        ctypes.c_char_p, ctypes.c_char_p,
        ctypes.POINTER(_SampleSpec), ctypes.c_void_p, ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    lib.pa_simple_new.restype = ctypes.c_void_p
    lib.pa_simple_read.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_int),
    ]
    lib.pa_simple_read.restype = ctypes.c_int
    lib.pa_simple_free.argtypes = [ctypes.c_void_p]
    lib.pa_simple_free.restype = None
    lib.pa_strerror.argtypes = [ctypes.c_int]
    lib.pa_strerror.restype = ctypes.c_char_p


if _LIB is not None:
    _setup_signatures()


class PulseAudioCapture:
    """Audio capture via libpulse-simple (PA_STREAM_RECORD).

    Provides a context-manager interface that reads from the PulseAudio
    default source and invokes a callback for each block of audio data,
    matching the pattern used by sounddevice.RawInputStream.

    Args:
        samplerate: Sample rate in Hz (default 16000).
        blocksize: Frames per read (default 1024).
        channels: Number of audio channels (default 1).
        dtype: Sample format string, e.g. ``"int16"`` (default).
        callback: ``callable(bytes, frames, time, status)`` invoked for each
                  audio block. Signature matches sounddevice callback.
    """

    def __init__(self, samplerate=16000, blocksize=1024, channels=1,
                 dtype="int16", callback=None):
        if _LIB is None:
            raise ImportError("libpulse-simple.so.0 not available")
        self._rate = samplerate
        self._blocksize = blocksize
        self._channels = channels
        self._callback = callback
        self._handle = None
        self._thread = None
        self._stop_event = threading.Event()

    def _open(self):
        """Open PulseAudio capture connection if not already open.

        Raises:
            OSError: if pa_simple_new fails.
        """
        if self._handle is not None:
            return
        spec = _SampleSpec(PA_SAMPLE_S16LE, self._rate, self._channels)
        server = os.environ.get("PULSE_SERVER")
        server_b = server.encode() if server else None
        error = ctypes.c_int(0)
        h = _LIB.pa_simple_new(
            server_b, b"sf-voice-cap", PA_STREAM_RECORD,
            None, b"stt", ctypes.byref(spec), None, None, ctypes.byref(error),
        )
        if not h:
            err_msg = _LIB.pa_strerror(error).decode() if _LIB.pa_strerror(error) else "unknown"
            raise OSError(f"pa_simple_new(capture): {err_msg}")
        self._handle = h

    def __enter__(self):
        """Context manager entry — opens capture connection and starts reader thread."""
        self._open()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *args):
        """Context manager exit — stops reader thread and closes connection."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self.close()

    def _read_loop(self):
        """Background read loop — invokes callback with each audio block."""
        bytes_per_read = self._blocksize * self._channels * 2  # 16-bit = 2 bytes
        while not self._stop_event.is_set():
            buf = ctypes.create_string_buffer(bytes_per_read)
            error = ctypes.c_int(0)
            ret = _LIB.pa_simple_read(self._handle, buf, bytes_per_read, ctypes.byref(error))
            if ret < 0:
                break
            try:
                if self._callback:
                    self._callback(bytes(buf), self._blocksize, None, None)
            except Exception:
                pass

    def close(self):
        """Close the PulseAudio capture connection."""
        if self._handle:
            try:
                _LIB.pa_simple_free(self._handle)
            except Exception:
                pass
            self._handle = None

    @staticmethod
    def is_available():
        """Check if PulseAudio capture is available.

        Returns:
            bool: True if libpulse-simple is loaded and PULSE_SERVER env var is set.
        """
        return _LIB is not None and "PULSE_SERVER" in os.environ
