from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gitrepo import GitRepository


class GitObject(ABC):
    """Base class for all objects"""
    fmt: bytes

    def __init__(self, data: bytes | None = None):
        if data is None:
            self.init()
        else:
            self.deserialize(data)

    @abstractmethod
    def init(self) -> None:
        """Initialize a new empty object."""
        pass

    @abstractmethod
    def serialize(self) -> bytes:
        """Convert to bytes"""
        pass

    @abstractmethod
    def deserialize(self, data: bytes) -> None:
        """CONVERT To python object from bytes"""
        pass


def object_find(
    repo: "GitRepository", name: str, fmt=None, follow: bool = True
) -> str | None:
    """Find the full SHA-1 hash for a given object name."""

    # For now, we are skipping tag resolution/branch names and just
    # handling direct SHA-1 hashes (the simplest case to start testing).
    return name


