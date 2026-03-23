import argparse
import configparser
from datetime import datetime
from typing import TextIO
from pathlib import Path
from abc import ABC, abstractmethod
try:
    import grp, pwd
except ModuleNotFoundError:
    pass 
from fnmatch import fnmatch
import hashlib
from math import ceil
import os
import re
import sys
import zlib

argparser = argparse.ArgumentParser(description="very dumb git")
argsubparsers = argparser.add_subparsers(title="Commands", dest="command")

argsubparsers.required = True

argsp = argsubparsers.add_parser("init", help = "initialize a dumb git repo")

argsp.add_argument("path",
                   metavar="directory",
                   nargs="?",
                   default=".",
                   help="Where to create the repository.")

def cmd_init(args):
    repo_create(args.path)

class GitRepository:
     """ A git repo"""

     def __init__(self, path: str, force: bool=False) -> None:
          #will take worktree path.
          #force:disables all checks because we want to create a repo with invalid filesystem locations.
          self.worktree: Path = path 
          self.gitdir: Path = os.path.join(path, ".git")

          if not (force or os.path.isdir(self.gitdir)):
               raise Exception(f"Not a gip repo: {self.gitdir}")
          
          self.conf: configparser.ConfigParser = configparser.ConfigParser()
          cf:Path = repo_file(self, "config")
          if cf and os.path.exists(cf):
               self.conf.read([cf])
          elif not force:
               raise Exception("config file missing")
          
          if not force:
               vers = int(self.conf.get("core", "repositoryformatversion"))
               if vers != 0:
                    raise Exception(f"Unsupported repository version.")
               
class GitObject(ABC):
     """Base class for all objects"""
     def __init__(self, data: bytes | None):
          if not self.data:
               self.init()
          else:
               self.deserialize()
          
     @abstractmethod
     def init(self) -> None:
          """Initialize a new empty object."""
          pass

     @abstractmethod
     def serialize(self) -> None:
          """Convert to bytes"""
          pass

     @abstractmethod
     def deserialize(self, data: bytes) -> None:
          """CONVERT To python object from bytes"""
          pass



def read_object(repo: GitRepository, hash: bytes) -> GitObject:
     """return git object that represents the type, either commit etc"""
     
     path = repo_file(repo, "objects", hash[:2], hash[2:])
     
     if not os.path.exists(path):
          return None
     if not os.path.isdir(path):
          return None
     with open(path, "rb") as f:
          raw = zlib.decompress(f.read())

          x = raw.find(b' ')
          fmt = raw[:x]

          y = raw.find(b'x\00')
          size = int(raw[x:y].decode('ascii'))
          if size != len(raw) -y -1:
               raise Exception(f"Malformed object: {hash}. Bad length")
          match fmt:
               case b'commit': c=GitCommit
               case b'tree': c=GitTree
               case b'blob': c=GitBlob
               case b'tag': c=GitTag
               case _:
                    raise Exception(f"Unknown type {fmt.decode('ascii')} for object {hash}")
     return c(raw[y+1:])
     


def write_object(object: GitObject, repo=None):
     data = object.serialize()
     result = object.fmt + b' ' + str(len(data)).encode() + b'\x00' + data

     #compute hash
     hash = hashlib.sha1(result).hexdigest()

     if repo:
          path = repo_file(repo, "objects", hash[:2], hash[2:], mkdir=True)
          if not os.path.exists(path):
               with open(path, "rb") as f:
                    f.write(zlib.compress(result))
     return hash




def main(argv=sys.argv[1:]):
     args = argparser.parse_args(argv)
     match args.command:
          case "init":
               cmd_init(args)
          case "add":
               cmd_add(args)
          case "cat-file":
               cmd_cat_file(args)
          case "check-igore":
               cmd_check_ignore(args)
          case "checkout":
               cmd_checkout(args)
          case "commit":
               cmd_commit(args)
          case "hash-object":
               cmd_hash_object(args)
          case "log":
               cmd_log(args)
          case "ls-files":
               cmd_ls_files(args)
          case "ls-trees":
               cmd_ls_trees(args)
          case "rev-parse":
               cmd_rev_parse(args)
          case "rm":
               cmd_rm(args)
          case "show-ref":
               cmd_show_ref(args)
          case "status":
               cmd_status(args)
          case "tag":
               cmd_tag(args)
          case _ :
               print("invalid command.")


          
     


def repo_path(repo: GitRepository, *path: list) -> Path:
     """compute path under repo's gitdir"""
     return os.path.join(repo.gitdir, *path)

def repo_file(repo: GitRepository, *path: list, mkdir: bool = False) -> Path | None:
     """same as repo_path but create_dirname(*path) if asbsent.
     For
     example, repo_file(r, \"refs\", \"remotes\", \"origin\", \"HEAD\") will create
.git/refs/remotes/origin.
     """
     if repo_dir(repo, *path[:-1], mkdir=mkdir):
          return repo_path(repo, *path)
     
def repo_dir(repo: GitRepository, *path: list, mkdir: bool =False) -> Path | None:
     """same as repo path but mkdir *path if absent if mkdir"""
     path = repo_path(repo, *path)
     
     if os.path.exists(path):
          if (os.path.isdir(path)):
               return path
          else:
               return Exception(f"Not a directory: {path}")
     if mkdir:
          os.makedirs(path)
          return path
     else:
          return None
def repo_default_config():
    ret = configparser.ConfigParser()

    ret.add_section("core")
    ret.set("core", "repositoryformatversion", "0")
    ret.set("core", "filemode", "false")
    ret.set("core", "bare", "false")

    return ret
def repo_find(path=".", required=True):
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

def repo_create(path: Path) -> None:
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


     with open(repo_file(repo, "description"), "w") as f:
          f.write("Unnamed repository: edit this file description \n")

     with open(repo_file(repo, "HEAD"), "w") as f:
          f.write("ref: refs/heads/master \n")

     with open(repo_file(repo, "config"), "w") as f:
          config = repo_default_config()
          config.write(f)

     return repo
