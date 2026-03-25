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
               try:
                    self.conf.read([cf])
               except Exception as e:
                    print(f"Error while trying to read the config file: {e}")
          elif not force:
               raise Exception("config file missing")
          
          if not force:
               vers = int(self.conf.get("core", "repositoryformatversion"))
               if vers != 0:
                    raise Exception(f"Unsupported repository version.")
               
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
     def serialize(self) -> None:
          """Convert to bytes"""
          pass

     @abstractmethod
     def deserialize(self, data: bytes) -> None:
          """CONVERT To python object from bytes"""
          pass

class GitBlob(GitObject):
     fmt = b'blob'
     def init(self):
          return super().init()

     def serialize(self):
          return self.blobdata
     def deserialize(self, data):
          self.blobdata = data

class GitCommit(GitObject):
     fmt = b'commit'
     def init(self):
          super().init()
          self.kvlm = dict()

     def serialize(self):
          #convert python dict to git commit format
          return kvlm_serialize(self.kvlm)
     
     def deserialize(self, data):
          self.kvlm = kvlm_parse(data)


argparser = argparse.ArgumentParser(description="very dumb git")
argsubparsers = argparser.add_subparsers(title="Commands", dest="command")

argsubparsers.required = True

argsp = argsubparsers.add_parser("init", help = "initialize a dumb git repo")

argsp.add_argument("path",
                   metavar="directory",
                   nargs="?",
                   default=".",
                   help="Where to create the repository.")

catfilesp = argsubparsers.add_parser("cat-file", help="print out the uncompressed object")
catfilesp.add_argument("type", 
                       metavar="type",
                       choices= ["blob", "tree", "tag", "commit"],
                       help="Print the type of the object")
catfilesp.add_argument("object",
                       metavar="object", 
                       help = "print out the object identifier")

hashfilesp = argsubparsers.add_parser("hash-object", help="Compute the object ID and optionally crate a blob from a file")
hashfilesp.add_argument("-t",
                        metavar="type",
                        dest="type",
                        default="blob",
                        choices=["blob", "tree", "tag", "commit"],
                        help="Print the type of the object")
hashfilesp.add_argument("-w",
                        dest="write",
                        action="store_true",
                        help="Write the hash obejct into the database")
hashfilesp.add_argument("path", 
                        metavar="path",
                        nargs="?",
                        help="Read object from <file>")

argsp = argsubparsers.add_parser("log", help="Display history of a given commit.")
argsp.add_argument("commit",
                   default="HEAD",
                   nargs="?",
                   help="Commit to start at.")
def cmd_log(args):
    repo = repo_find()

    print("digraph wyaglog{")
    print("  node[shape=rect]")
    log_graphviz(repo, object_find(repo, args.commit), set())
    print("}")

def log_graphviz(repo, sha, seen):

    if sha in seen:
        return
    seen.add(sha)

    commit = read_object(repo, sha)
    if not commit:
         print("please provide a commit hash")
         return
    if not isinstance(commit, GitCommit):
         print(f"You did not pass a valid gitcommit {commit.deserialize(commit)}")
         return
    message = commit.kvlm[None].decode("utf8").strip()
    message = message.replace("\\", "\\\\")
    message = message.replace("\"", "\\\"")

    if "\n" in message: # Keep only the first line
        message = message[:message.index("\n")]

    print(f"  c_{sha} [label=\"{sha[0:7]}: {message}\"]")
    assert commit.fmt==b'commit'

    if not b'parent' in commit.kvlm.keys():
        # Base case: the initial commit.
        return

    parents = commit.kvlm[b'parent']

    if type(parents) != list:
        parents = [ parents ]

    for p in parents:
        p = p.decode("ascii")
        print (f"  c_{sha} -> c_{p};")
        log_graphviz(repo, p, seen)

def object_hash(fd, fmt, repo=None):
    """Compute object ID and optionally create a blob from a file."""
    data = fd.read()

    # Choose correct object type
    match fmt:
        case b'commit': obj=GitCommit(data)
        case b'tree': obj=GitTree(data)
        case b'tag': obj=GitTag(data)
        case b'blob': obj=GitBlob(data)
        case _: raise Exception(f"Unknown type {fmt}!")

    return write_object(obj, repo)


def cmd_hash_object(args):
     if args.write:
          repo = repo_find()
     else:
          repo = None
          
     if args.path:
          with open(args.path, "rb") as fd:
               sha = object_hash(fd, args.type.encode(), repo)
               print(sha)
     else:
          # Read raw bytes from stdin
          sha = object_hash(sys.stdin.buffer, args.type.encode(), repo)
          print(sha)




def cmd_init(args):
    repo_create(args.path)
def cmd_cat_file(args):
     repo = repo_find()
     cat_file(repo, args.object, fmt=args.type.encode())

def cat_file(repo: GitRepository, obj: GitObject, fmt=None):
     obj = read_object(repo, object_find(repo, obj, fmt=fmt))

def object_find(repo, name, fmt=None, follow=True):
    """Find the full SHA-1 hash for a given object name."""
    
    # For now, we are skipping tag resolution/branch names and just
    # handling direct SHA-1 hashes (the simplest case to start testing).
    return name




def kvlm_parse(raw, start=0, dct=None):
    if not dct:
        dct = dict()
        # You CANNOT declare the argument as dct=dict() or all call to
        # the functions will endlessly grow the same dict.

    # This function is recursive: it reads a key/value pair, then call
    # itself back with the new position.  So we first need to know
    # where we are: at a keyword, or already in the messageQ

    # We search for the next space and the next newline.
    spc = raw.find(b' ', start)
    nl = raw.find(b'\n', start)

    # If space appears before newline, we have a keyword.  Otherwise,
    # it's the final message, which we just read to the end of the file.

    # Base case
    # =========
    # If newline appears first (or there's no space at all, in which
    # case find returns -1), we assume a blank line.  A blank line
    # means the remainder of the data is the message.  We store it in
    # the dictionary, with None as the key, and return.
    if (spc < 0) or (nl < spc):
        assert nl == start
        dct[None] = raw[start+1:]
        return dct

    # Recursive case
    # ==============
    # we read a key-value pair and recurse for the next.
    key = raw[start:spc]

    # Find the end of the value.  Continuation lines begin with a
    # space, so we loop until we find a "\n" not followed by a space.
    end = start
    while True:
        end = raw.find(b'\n', end+1)
        if raw[end+1] != ord(' '): break

    # Grab the value
    # Also, drop the leading space on continuation lines
    value = raw[spc+1:end].replace(b'\n ', b'\n')

    # Don't overwrite existing data contents
    if key in dct:
        if type(dct[key]) == list:
            dct[key].append(value)
        else:
            dct[key] = [ dct[key], value ]
    else:
        dct[key]=value

    return kvlm_parse(raw, start=end+1, dct=dct)

def kvlm_serialize(kvlm):
    '''serializing the key value list message to the git format'''
    ret = b''

    # Output fields
    for k in kvlm.keys():
        # Skip the message itself
        if k == None: continue
        val = kvlm[k]
        # Normalize to a list
        if type(val) != list:
            val = [ val ]

        for v in val:
            ret += k + b' ' + (v.replace(b'\n', b'\n ')) + b'\n'

    # Append message
    ret += b'\n' + kvlm[None]

    return ret

def read_object(repo: GitRepository, hash: str) -> GitObject:
     """return git object that represents the type, either commit etc"""
     
     path = repo_file(repo, "objects", hash[:2], hash[2:])
     
     if not path or not os.path.exists(path):
          return None
     if not os.path.isfile(path):
          return None
     with open(path, "rb") as f:
          raw = zlib.decompress(f.read())

          x = raw.find(b' ')
          fmt = raw[:x]

          y = raw.find(b'\x00', x)
          size = int(raw[x+1:y].decode('ascii'))
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
               with open(path, "wb") as f:
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
