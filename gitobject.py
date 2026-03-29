import hashlib
import os
import zlib
from abc import ABC, abstractmethod

from gitrepo import GitRepository


class GitObject(ABC):
    """Base class for all objects"""

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
    repo: GitRepository, name: str, fmt=None, follow: bool = True
) -> str | None:
    """Find the full SHA-1 hash for a given object name."""

    # For now, we are skipping tag resolution/branch names and just
    # handling direct SHA-1 hashes (the simplest case to start testing).
    return name


def write_object(object: GitObject, repo=None):
    data = object.serialize()
    result = object.fmt + b" " + str(len(data)).encode() + b"\x00" + data

    # compute hash
    hash = hashlib.sha1(result).hexdigest()

    if repo:
        # Lazy import to avoid circular import between gitobject <-> gitrepo
        from gitrepo import repo_file

        path = repo_file(repo, "objects", hash[:2], hash[2:], mkdir=True)
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(zlib.compress(result))
    return hash
