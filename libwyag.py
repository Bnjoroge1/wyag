import argparse
import configparser
from datetime import datetime
from typing import TextIO
from pathlib import Path
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
               






     






def main(argv=sys.argv[1:]):
     args = argparser.parse_args(argv)
     match args.command:
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
     assert repo_dir(repo, "refs", "tags", mkidr=True)
     assert repo_dir(repo, "refs", "heads", mkdir=True)


     with open(repo_file(repo, "description"), "w") as f:
          f.write("Unnamed repository: edit this file description")

     with open(repo_file(repo, "HEAD"), "w") as f:
          f.write("ref: refs/heads/master \n")

     with open(repo_file(repo, "config"), "w") as f:
          config = repo_default_config()
          config.write(f)

     return repo
