import argparse
import grp
import os
import pwd
import sys
from datetime import datetime

from gitcommit import GitCommit, commit_create
from gitindex import add, index_read, rm
from gitingore import check_ignore, gitignore_read
from gitlog import log_graphviz
from gitrefs import list_refs, object_find
from gitrepo import (
    GitRepository,
    gitconfig_read,
    gitconfig_user_get,
    repo_create,
    repo_find,
    repo_file
)
from gitstatus import branch_get_active, tree_to_dict
from gitstore import object_hash, read_object, write_object
from gittree import GitTree, tree_checkout, tree_from_index


def cmd_ls_tree(args):
    repo = repo_find()
    ls_tree(repo, args.tree, args.recursive)


def ls_tree(repo, ref, recursive=None, prefix=""):
    sha = object_find(repo, ref, fmt=b"tree")
    if not sha:
        return
    obj = read_object(repo, sha)
    if not isinstance(obj, GitTree):
        print(f" this object {obj} is not a tree")
        return

    for item in obj.items:
        if len(item.mode) == 5:
            type = item.mode[0:1]
        else:
            type = item.mode[0:2]

        if type == b"04":
            type = "tree"
        elif type == b"10":
            type = "blob"
        elif type == b"12":
            type = "blob"
        elif type == b"16":
            type = "commit"
        else:
            raise Exception(f"Weird tree leaf mode {item.mode}")

        if not (recursive and type == "tree"):  # This is a leaf
            print(
                f"{'0' * (6 - len(item.mode)) + item.mode.decode('ascii')} {type} {item.sha}\t{os.path.join(prefix, item.path)}"
            )
        else:  # This is a branch, recurse
            ls_tree(repo, item.sha, recursive, os.path.join(prefix, item.path))


argparser = argparse.ArgumentParser(description="very dumb git")
argsubparsers = argparser.add_subparsers(title="Commands", dest="command")

argsubparsers.required = True

argsp = argsubparsers.add_parser("init", help="initialize a dumb git repo")

argsp.add_argument(
    "path",
    metavar="directory",
    nargs="?",
    default=".",
    help="Where to create the repository.",
)

catfilesp = argsubparsers.add_parser(
    "cat-file", help="print out the uncompressed object"
)
catfilesp.add_argument(
    "-p",
    "--pretty",
    dest="pretty",
    action="store_true",
    help="Pretty-print the object (auto-detect type).",
)
catfilesp.add_argument(
    "type",
    metavar="type",
    nargs="?",
    choices=["blob", "tree", "tag", "commit"],
    help="Print the type of the object (optional with -p).",
)
catfilesp.add_argument(
    "object", metavar="object", help="print out the object identifier"
)

hashfilesp = argsubparsers.add_parser(
    "hash-object", help="Compute the object ID and optionally crate a blob from a file"
)
hashfilesp.add_argument(
    "-t",
    metavar="type",
    dest="type",
    default="blob",
    choices=["blob", "tree", "tag", "commit"],
    help="Print the type of the object",
)
hashfilesp.add_argument(
    "-w",
    dest="write",
    action="store_true",
    help="Write the hash obejct into the database",
)
hashfilesp.add_argument(
    "path", metavar="path", nargs="?", help="Read object from <file>"
)

argsp = argsubparsers.add_parser("log", help="Display history of a given commit.")
argsp.add_argument("commit", default="HEAD", nargs="?", help="Commit to start at.")
argsp = argsubparsers.add_parser("ls-tree", help="Pretty-print a tree object.")
argsp.add_argument(
    "-r", dest="recursive", action="store_true", help="Recurse into sub-trees"
)

argsp.add_argument("tree", help="A tree-ish object.")
argsp = argsubparsers.add_parser(
    "checkout", help="Checkout a commit inside of a directory."
)

argsp.add_argument("commit", help="The commit or tree to checkout.")

argsp.add_argument("path", help="The EMPTY directory to checkout on.")

ref_sp = argsubparsers.add_parser("show-refs", help="List references.")

argsp = argsubparsers.add_parser(
    "tag",
    help="List and create tags")

argsp.add_argument("-a",
                   action="store_true",
                   dest="create_tag_object",
                   help="Whether to create a tag object")

argsp.add_argument("name",
                   nargs="?",
                   help="The new tag's name")

argsp.add_argument("object",
                   default="HEAD",
                   nargs="?",
                   help="The object the new tag will point to")

argsp = argsubparsers.add_parser(
    "rev-parse",
    help="Parse revision (or other objects) identifiers")

argsp.add_argument("--dumbgit-type",
                   metavar="type",
                   dest="type",
                   choices=["blob", "commit", "tag", "tree"],
                   default=None,
                   help="Specify the expected type")

argsp.add_argument("name",
                   help="The name to parse")
argsp = argsubparsers.add_parser("ls-files", help = "List all the stage files")
argsp.add_argument("--verbose", action="store_true", help="Show everything.")
argsp = argsubparsers.add_parser("check-ignore", help = "Check path(s) against ignore rules.")
argsp.add_argument("path", nargs="+", help="Paths to check")
argsp = argsubparsers.add_parser("status", help = "Show the working tree status.")
argsp = argsubparsers.add_parser("rm", help="Remove files from the working tree and the index.")
argsp.add_argument("path", nargs="+", help="Files to remove")
argsp = argsubparsers.add_parser("add", help = "Add files contents to the index.")
argsp.add_argument("path", nargs="+", help="Files to add")
argsp = argsubparsers.add_parser("commit", help="Record changes to the repository.")

argsp.add_argument("-m",
                   metavar="message",
                   dest="message",
                   help="Message to associate with this commit.")

def cmd_add(args):
    repo = repo_find()
    add(repo, args.path)
    
def cmd_rm(args):
    repo = repo_find()
    rm(repo, args.path)
    
def cmd_status(_):
    repo = repo_find()
    index = index_read(repo)

    cmd_status_branch(repo)
    cmd_status_head_index(repo, index)
    print()
    cmd_status_index_worktree(repo, index)

def cmd_status_branch(repo):
    branch = branch_get_active(repo)
    if branch:
        print(f"On branch {branch}.")
    else:
        print(f"HEAD detached at {object_find(repo, 'HEAD')}")
        
def cmd_check_ignore(args):
    repo = repo_find()
    rules = gitignore_read(repo)
    for path in args.path:
        if check_ignore(rules, path):
            print(path)

def cmd_status_head_index(repo, index):
    print("Changes to be committed:")

    head = tree_to_dict(repo, "HEAD")
    for entry in index.entries:
        if entry.name in head:
            if head[entry.name] != entry.sha:
                print("  modified:", entry.name)
            del head[entry.name] # Delete the key
        else:
            print("  added:   ", entry.name)

    # Keys still in HEAD are files that we haven't met in the index,
    # and thus have been deleted.
    for entry in head.keys():
        print("  deleted: ", entry)
        
def cmd_status_index_worktree(repo, index):
    print("Changes not staged for commit:")

    ignore = gitignore_read(repo)

    gitdir_prefix = repo.gitdir + os.path.sep

    all_files = list()

    # We begin by walking the filesystem
    for (root, _, files) in os.walk(repo.worktree, True):
        if root==repo.gitdir or root.startswith(gitdir_prefix):
            continue
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, repo.worktree)
            all_files.append(rel_path)

    # We now traverse the index, and compare real files with the cached
    # versions.

    for entry in index.entries:
        full_path = os.path.join(repo.worktree, entry.name)

        # That file *name* is in the index

        if not os.path.exists(full_path):
            print("  deleted: ", entry.name)
        else:
            stat = os.stat(full_path)

            # Compare metadata
            ctime_ns = entry.ctime[0] * 10**9 + entry.ctime[1]
            mtime_ns = entry.mtime[0] * 10**9 + entry.mtime[1]
            if (stat.st_ctime_ns != ctime_ns) or (stat.st_mtime_ns != mtime_ns):
                # If different, deep compare.
                # @FIXME This *will* crash on symlinks to dir.
                with open(full_path, "rb") as fd:
                    new_sha = object_hash(fd, b"blob", None)
                    # If the hashes are the same, the files are actually the same.
                    same = entry.sha == new_sha

                    if not same:
                        print("  modified:", entry.name)

        if entry.name in all_files:
            all_files.remove(entry.name)

    print()
    print("Untracked files:")

    for f in all_files:
        # @TODO If a full directory is untracked, we should display
        # its name without its contents.
        if not check_ignore(ignore, f):
            print(" ", f)
            
def cmd_ls_files(args):
    repo = repo_find()
    index = index_read(repo)
    if args.verbose:
        print(f"Index file format v{index.version}, containing {len(index.entries)} entries.")

    for e in index.entries:
        print(e.name)
        if args.verbose:
            entry_type = { 0b1000: "regular file",
                           0b1010: "symlink",
                           0b1110: "git link" }[e.mode_type]
            print(f"  {entry_type} with perms: {e.mode_perms:o}")
            print(f"  on blob: {e.sha}")
            print(f"  created: {datetime.fromtimestamp(e.ctime[0])}.{e.ctime[1]}, modified: {datetime.fromtimestamp(e.mtime[0])}.{e.mtime[1]}")
            print(f"  device: {e.dev}, inode: {e.ino}")
            try:
                print(f"  user: {pwd.getpwuid(e.uid).pw_name} ({e.uid})  group: {grp.getgrgid(e.gid).gr_name} ({e.gid})")
            except NameError:
                # These modules are not available on Windows, so just use the less-nice info.
                print(f"  user: {e.uid}  group: {e.gid}")
            print(f"  flags: stage={e.flag_stage} assume_valid={e.flag_assume_valid}")
            
def cmd_rev_parse(args):
    if args.type:
        fmt = args.type.encode()
    else:
        fmt = None

    repo = repo_find()

    print (object_find(repo, args.name, fmt, follow=True))
    
def cmd_tag(args):
    repo = repo_find()
    if not repo:
        return

    if args.name:
        create_tag(repo,
                   args.name,
                   args.object,
                   create_tag_object = args.create_tag_object)
    else:
        refs = list_refs(repo)
        show_ref(repo, refs["tags"], with_hash=False)
      
def create_tag(repo:'GitRepository', name: str, ref: str, create_tag_object=False):
    # get the GitObject from the object reference
    sha = object_find(repo, ref)
    if not sha:
        return

    if create_tag_object:
        # create tag object (commit)
        tag = GitTag()
        tag.kvlm = dict()
        tag.kvlm[b'object'] = sha.encode()
        tag.kvlm[b'type'] = b'commit'
        tag.kvlm[b'tag'] = name.encode()
        # Feel free to let the user give their name!
        # Notice you can fix this after commit, read on!
        tag.kvlm[b'tagger'] = b'dumbgit <dumbgit@example.com>'
        # …and a tag message!
        tag.kvlm[None] = b"A tag generated by dumbgit, which won't let you customize the message!\n"
        tag_sha = write_object(tag, repo)
        # create reference
        ref_create(repo, "tags/" + name, tag_sha)
    else:
        # create lightweight tag (ref)
        ref_create(repo, "tags/" + name, sha)

def ref_create(repo, ref_name, sha) -> None:
    rep = repo_file(repo, "refs/" + ref_name)
    if not rep:
        return None
    with open(rep, "w") as fp:
        fp.write(sha + "\n")
        
def cmd_show_refs(args):
    repo = repo_find()
    refs = list_refs(repo)
    show_ref(repo, refs, prefix="refs")

def show_ref(repo, refs, with_hash=True, prefix=""):
    if prefix:
        prefix = prefix + '/'
    for k, v in refs.items():
        if isinstance(v, str) and with_hash:
            print (f"{v} {prefix}{k}")
        elif isinstance(v, str):
            print (f"{prefix}{k}")
        else:
            show_ref(repo, v, with_hash=with_hash, prefix=f"{prefix}{k}")

def cmd_log(args):
    repo = repo_find()
    if not repo:
        return

    print("digraph wyaglog{")
    print("  node[shape=rect]")
    
    obj = object_find(repo, args.commit)
    if not obj:
        return
    log_graphviz(repo, obj , set())
    print("}")




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

def cmd_commit(args):
    repo = repo_find()
    index = index_read(repo)
    # Create trees, grab back SHA for the root tree.
    tree = tree_from_index(repo, index)

    # Create the commit object itself
    commit = commit_create(repo,
                           tree,
                           object_find(repo, "HEAD"),
                           gitconfig_user_get(gitconfig_read()),
                           datetime.now(),
                           args.message)
    commit_sha = write_object(commit, repo)
    # Update HEAD so our commit is now the tip of the active branch.
    active_branch = branch_get_active(repo)
    if active_branch: # If we're on a branch, we update refs/heads/BRANCH
        with open(repo_file(repo, os.path.join("refs/heads", active_branch)), "w") as fd:
            fd.write(commit_sha + "\n")
    else: # Otherwise, we update HEAD itself.
        with open(repo_file(repo, "HEAD"), "w") as fd:
            fd.write("\n")
            
def cmd_init(args):
    repo_create(args.path)


def cmd_cat_file(args):
    repo = repo_find()
    if not repo:
        return
    if args.pretty:
        cat_file(repo, args.object, fmt=None)
    else:
        if not args.type:
            raise Exception("cat-file requires <type> unless -p/--pretty is specified")
        cat_file(repo, args.object, fmt=args.type.encode())


def cat_file(repo: GitRepository, obj_name: str, fmt=None):
    if not obj_name:
        print(f" object{obj_name} does not exit")
        return None

    # If fmt is None, we are in "pretty" mode: resolve the object without
    # forcing a type, then print its serialized bytes.
    sha = object_find(repo, obj_name, fmt=fmt)
    if not sha:
        return

    obj = read_object(repo, sha)
    if not obj:
        raise Exception(f"Object {sha} does not exist")

    sys.stdout.buffer.write(obj.serialize())


def cmd_checkout(args):
    repo = repo_find()
    if not repo:
        return
    obj_name= object_find(repo, args.commit)
    if not obj_name:
        return
    obj = read_object(repo, obj_name)
    if not obj:
        return

    # If the object is a commit, we grab its tree
    
    if isinstance(obj, GitCommit): 
        obj = read_object(repo, obj.kvlm[b"tree"].decode("ascii"))

    # Verify that path is an empty directory
    if os.path.exists(args.path):
        if not os.path.isdir(args.path):
            raise Exception(f"Not a directory {args.path}!")
        if os.listdir(args.path):
            #Using empty dirs
            raise Exception(f"Not empty {args.path}!")
    else:
        os.makedirs(args.path)

    tree_checkout(repo, obj, os.path.realpath(args.path))


def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)
    commands = {
        "init": cmd_init,
        "add": cmd_add,
        "cat-file": cmd_cat_file,
        "check-ignore": cmd_check_ignore,
        "checkout": cmd_checkout,
        "commit": cmd_commit,
        "hash-object": cmd_hash_object,
        "log": cmd_log,
        "ls-files": cmd_ls_files,
        "ls-tree": cmd_ls_tree,
        "rev-parse": cmd_rev_parse,
        "rm": cmd_rm,
        "show-refs": cmd_show_refs,
        "status": cmd_status,
        "tag": cmd_tag,
    }

    handler = commands.get(args.command)
    if handler is None:
        print("invalid command.")
        return

    handler(args)
