
from abc import ABC, abstractmethod





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





