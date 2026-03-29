import configparser
import os
import zlib

import hashlib

from gitcommit import GitCommit
from gitobject import GitObject
from gittree import GitBlob, GitTree


class GitRepository:
    """A git repo"""

    def __init__(self, path: str, force: bool = False) -> None:
        # will take worktree path.
        # force:disables all checks because we want to create a repo with invalid filesystem locations.
        self.worktree: str = path
        self.gitdir: str = os.path.join(path, ".git")

        if not (force or os.path.isdir(self.gitdir)):
            raise Exception(f"Not a gip repo: {self.gitdir}")

        # Git config allows duplicate keys; Python's configparser defaults to
        # strict parsing and raises DuplicateOptionError. We mimic git's
        # behavior by allowing duplicates (last value wins) and disabling
        # interpolation.
        self.conf: configparser.ConfigParser = configparser.ConfigParser(
            interpolation=None,
            strict=False,
            allow_no_value=True,
        )

        cf: str | None = repo_file(self, "config")
        if cf and os.path.exists(cf):
            try:
                self.conf.read([cf])
            except Exception as e:
                print(f"Error while trying to read the config file: {e}")
                return
        elif not force:
            raise Exception("config file missing")

        if not force:
            vers = int(self.conf.get("core", "repositoryformatversion"))
            if vers != 0:
                raise Exception("Unsupported repository version.")


def read_object(repo: GitRepository, hash: str) -> GitObject | None:
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
        match fmt:
            case b"commit":
                c = GitCommit
            case b"tree":
                c = GitTree
            case b"blob":
                c = GitBlob
            case b"tag":
                raise Exception("Tag objects are not implemented yet")
            case _:
                raise Exception(f"Unknown type {fmt.decode('ascii')} for object {hash}")
    return c(raw[y + 1 :])

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
            return
            with open(path, "wb") as f:
                f.write(zlib.compress(result))
    return hash

def repo_path(repo: GitRepository, *path: str) -> str:
    """compute path under repo's gitdir"""
    return os.path.join(repo.gitdir, *path)


def repo_file(repo: GitRepository, *path, mkdir: bool = False) -> str | None:
    """same as repo_path but create_dirname(*path) if asbsent.
         For
         example, repo_file(r, \"refs\", \"remotes\", \"origin\", \"HEAD\") will create
    .git/refs/remotes/origin.
    """
    if repo_dir(repo, *path[:-1], mkdir=mkdir):
        return repo_path(repo, *path)


def repo_dir(
    repo: GitRepository, *path, mkdir: bool = False
) -> str | None | Exception:
    """same as repo path but mkdir *path if absent if mkdir"""
    path = repo_path(repo, *path)

    if os.path.exists(path):
        if os.path.isdir(path):
            return path
        else:
            return Exception(f"Not a directory: {path}")
    if mkdir:
        os.makedirs(path)
        return path
    else:
        return None


def repo_default_config():
    ret = configparser.ConfigParser(
        interpolation=None, strict=False, allow_no_value=True
    )

    ret.add_section("core")
    ret.set("core", "repositoryformatversion", "0")
    ret.set("core", "filemode", "false")
    ret.set("core", "bare", "false")

    return ret


def repo_find(path=".", required=True) -> GitRepository | None:
    path = os.path.realpath(path)

    if os.path.isdir(os.path.join(path, ".git")):
        return GitRepository(path)

    # If we haven't returned, recurse in parent, if w
    parent = os.path.realpath(os.path.join(path, ".."))

    if parent == path:
        # Bottom case
        # os.path.join("/", "..") == "/":
        # If parent==path, then path is root.
        if required:
            raise Exception("No git directory.")
        else:
            return None

    # Recursive case
    return repo_find(parent, required)


def repo_create(path: str) -> GitRepository | None:
    repo = GitRepository(path, True)

    if os.path.exists(repo.worktree):
        if not os.path.isdir(repo.worktree):
            raise Exception(f"{path} is not a directory")
        if os.path.exists(repo.gitdir) and os.listdir(repo.gitdir):
            raise Exception(f"{path} is not empty")
    else:
        os.makedirs(repo.worktree)

    assert repo_dir(repo, "branches", mkdir=True)
    assert repo_dir(repo, "objects", mkdir=True)
    assert repo_dir(repo, "refs", "tags", mkdir=True)
    assert repo_dir(repo, "refs", "heads", mkdir=True)
    
    repo_f = repo_file(repo, "description")
    if not repo_f:
        return
    with open(repo_f, "w") as f:
        f.write("Unnamed repository: edit this file description \n")
        
    head_p = repo_file(repo, "HEAD")
    
    if not head_p:
        return
        
    with open(head_p, "w") as f:
        f.write("ref: refs/heads/master \n")
    
    conf_p = repo_file(repo, "config")
    if not conf_p:
        return
        
    with open(conf_p, "w") as f:
        config = repo_default_config()
        config.write(f)

    return repo
