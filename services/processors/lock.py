"""Lock manager to prevent concurrent processor runs."""
from pathlib import Path
from datetime import datetime, timezone
import fcntl
import os


class LockError(Exception):
    """Raised when a lock cannot be acquired."""
    pass


class LockManager:
    """Manages file-based locks for processors."""

    def __init__(self, locks_path: Path):
        self.locks_path = locks_path
        self.locks_path.mkdir(parents=True, exist_ok=True)
        self._locks: dict[str, int] = {}  # processor_name -> file descriptor

    def acquire(self, processor_name: str) -> bool:
        """Acquire lock for a processor. Returns True if acquired."""
        lock_file = self.locks_path / f"{processor_name}.lock"
        try:
            fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Write lock info
            os.write(fd, f"locked at {datetime.now(timezone.utc).isoformat()}\n".encode())
            self._locks[processor_name] = fd
            return True
        except (BlockingIOError, OSError):
            return False

    def release(self, processor_name: str) -> None:
        """Release lock for a processor."""
        if processor_name in self._locks:
            fd = self._locks.pop(processor_name)
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
            # Remove lock file
            lock_file = self.locks_path / f"{processor_name}.lock"
            lock_file.unlink(missing_ok=True)

    def is_locked(self, processor_name: str) -> bool:
        """Check if a processor is currently locked."""
        lock_file = self.locks_path / f"{processor_name}.lock"
        if not lock_file.exists():
            return False
        try:
            fd = os.open(str(lock_file), os.O_RDONLY)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(fd, fcntl.LOCK_UN)
                return False
            except BlockingIOError:
                return True
            finally:
                os.close(fd)
        except OSError:
            return False
