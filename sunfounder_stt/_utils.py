"""Internal utilities — command runner, executable checks, stderr suppression."""


def run_command(cmd: str, user: str = None, group: str = None) -> tuple:
    """Run a shell command and return status and output.

    Args:
        cmd: Shell command string to execute.
        user: Optional username to run as (requires root).
        group: Optional group name to run as.

    Returns:
        tuple: ``(returncode: int, stdout: str)`` — exit code and decoded output.
    """
    import subprocess
    p = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        user=user,
        group=group)
    result = p.stdout.read().decode('utf-8')
    status = p.wait()
    return status, result


def check_executable(executable: str) -> bool:
    """Check if an executable is on PATH.

    Args:
        executable: Executable name (e.g. ``"arecord"``).

    Returns:
        bool: ``True`` if the executable is found on the system PATH.
    """
    from shutil import which
    executable_path = which(executable)
    found = executable_path is not None
    return found


def is_installed(cmd: str) -> bool:
    """Check if a command is installed via ``which``.

    Args:
        cmd: Command name to check.

    Returns:
        bool: ``True`` if ``which <cmd>`` exits with code 0.
    """
    status, _ = run_command(f"which {cmd}")
    if status in [0, ]:
        return True
    else:
        return False


def redirect_error_2_null() -> int:
    """Redirect stderr to /dev/null, returning the saved stderr fd.

    Suppresses ALSA/PortAudio warning messages that would otherwise
    leak to the console. Call :func:`cancel_redirect_error` to restore.

    Returns:
        int: The original stderr file descriptor (pass to ``cancel_redirect_error``).
    """
    import os, sys
    # https://github.com/spatialaudio/python-sounddevice/issues/11

    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    sys.stderr.flush()
    os.dup2(devnull, 2)
    os.close(devnull)
    return old_stderr


def cancel_redirect_error(old_stderr: int) -> None:
    """Restore stderr from a saved file descriptor.

    Args:
        old_stderr: The fd returned by :func:`redirect_error_2_null`.

    Returns:
        None
    """
    import os, sys
    sys.stderr.flush()
    os.dup2(old_stderr, 2)
    os.close(old_stderr)


class ignore_stderr():
    """Context manager that suppresses stderr within a ``with`` block.

    Usage::

        with ignore_stderr():
            p = pyaudio.PyAudio()  # ALSA warnings silenced
    """

    def __init__(self) -> None:
        """Save the current stderr and redirect to /dev/null."""
        self.old_stderr = redirect_error_2_null()

    def __enter__(self) -> None:
        """Enter the context — stderr already redirected.

        Returns:
            None
        """
        pass

    def __exit__(self, exc_type: type, exc_val: Exception, exc_tb: object) -> None:
        """Exit the context — restore original stderr.

        Returns:
            None
        """
        cancel_redirect_error(self.old_stderr)
