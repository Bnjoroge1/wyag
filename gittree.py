import os

from gitobject import GitObject


def tree_parse(raw) -> list:
    pos = 0
    max = len(raw)
    ret = []
    while pos < max:
        pos, data = tree_parse_one(raw, pos)
        ret.append(data)

    return ret


def tree_parse_one(raw, start=0):
    # Find the space terminator of the mode
    x = raw.find(b" ", start)
    assert x - start == 5 or x - start == 6

    # Read the mode
    mode = raw[start:x]
    if len(mode) == 5:
        # Normalize to six bytes.
        mode = b"0" + mode

    # Find the NULL terminator of the path
    y = raw.find(b"\x00", x)
    # and read the path
    path = raw[x + 1 : y]

    # Read the SHA…
    raw_sha = int.from_bytes(raw[y + 1 : y + 21], "big")
    # and convert it into an hex string, padded to 40 chars
    # with zeros if needed.
    sha = format(raw_sha, "040x")
    return y + 21, GitTreeLeaf(mode, path.decode("utf8"), sha)


def tree_leaf_sort_key(leaf):
    if leaf.mode.startswith(b"4"):  # directory
        return leaf.path + "/"
    else:
        return leaf.path


def tree_serialize(obj) -> bytes:
    obj.items.sort(key=tree_leaf_sort_key)
    ret = b""
    for i in obj.items:
        ret += i.mode
        ret += b" "
        ret += i.path.encode("utf8")
        ret += b"\x00"
        sha = int(i.sha, 16)
        ret += sha.to_bytes(20, byteorder="big")
    return ret


class GitTreeLeaf:
    def __init__(self, mode, path, sha):
        self.mode = mode
        self.path = path
        self.sha = sha


class GitTree(GitObject):
    fmt = b"tree"

    def deserialize(self, data):
        self.items = tree_parse(data)

    def serialize(self):
        return tree_serialize(self)

    def init(self):
        self.items = list()


class GitBlob(GitObject):
    fmt = b"blob"

    def init(self):
        return super().init()

    def serialize(self):
        return self.blobdata

    def deserialize(self, data):
        self.blobdata = data


def tree_checkout(repo, tree, path):
    # Lazy import to avoid circular import (gitrepo imports gittree)
    from gitrepo import read_object

    for item in tree.items:
        obj = read_object(repo, item.sha)
        if not obj:
            return
        dest = os.path.join(path, item.path)

        if obj.fmt == b"tree":
            os.mkdir(dest)
            tree_checkout(repo, obj, dest)
        elif obj.fmt == b"blob":
            # @TODO Support symlinks (identified by mode 12****)
            with open(dest, "wb") as f:
                f.write(obj.blobdata)
