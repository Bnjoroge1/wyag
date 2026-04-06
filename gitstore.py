import zlib
import os
import hashlib
from typing import Optional


from gitrepo import GitRepository, repo_file
from gittags import GitTag
from gitcommit import GitCommit
from gitobject import GitObject
from gittree import GitTree, GitBlob








def read_object(repo: GitRepository, hash: str) -> Optional[GitObject]:
    """return git object that represents the type, either commit etc"""

    path = repo_file(repo, "objects", hash[:2], hash[2:])
    if not hash:
        return None
    if not path or not os.path.exists(path):
        return None
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        raw = zlib.decompress(f.read())

        x = raw.find(b" ")
        fmt = raw[:x]

        y = raw.find(b"\x00", x)
        size = int(raw[x + 1 : y].decode("ascii"))
        if size != len(raw) - y - 1:
            raise Exception(f"Malformed object: {hash}. Bad length")
        if fmt == b"commit":
            c = GitCommit
        elif fmt == b"tree":
            c = GitTree
        elif fmt == b"blob":
            c = GitBlob
        elif fmt == b"tag":
            raise Exception("Tag objects are not implemented yet")
        else:
            raise Exception(f"Unknown type {fmt.decode('ascii')} for object {hash}")
    return c(raw[y + 1 :])
    
def object_hash(fd, fmt, repo=None):
    """Compute object ID and optionally create a blob from a file."""
    data = fd.read()

    # Choose correct object type
    if fmt == b"commit":
        obj = GitCommit(data)
    elif fmt == b"tree":
        obj = GitTree(data)
    elif fmt == b"tag":
        obj = GitTag(data)
    elif fmt == b"blob":
        obj = GitBlob(data)
    else:
        raise Exception(f"Unknown type {fmt}!")

    return write_object(obj, repo)

def write_object(object: GitObject, repo=None):
    data = object.serialize()
    result = object.fmt + b" " + str(len(data)).encode() + b"\x00" + data

    # compute hash
    hash = hashlib.sha1(result).hexdigest()

    if repo:
        # Lazy import to avoid circular import between gitobject <-> gitrepo
        from gitrepo import repo_file

        path = repo_file(repo, "objects", hash[:2], hash[2:], mkdir=True)
        if not path:
            return hash
        if os.path.exists(path):
            return hash
            
        with open(path, "wb") as f:
            f.write(zlib.compress(result))
    return hash
