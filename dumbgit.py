import argparse

import os
import sys


from gitcommit import GitCommit
from gitlog import log_graphviz
from gitrefs import object_find
from gitrepo import GitRepository, read_object, repo_create, repo_find, write_object
from gittree import GitBlob, GitTree, tree_checkout
from gitrefs import list_refs
from gittags import create_tag, GitTag

            
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

        match type:  # Determine the type.
            case b"04":
                type = "tree"
            case b"10":
                type = "blob"  # A regular file.
            case b"12":
                type = "blob"  # A symlink. Blob contents is link target.
            case b"16":
                type = "commit"  # A submodule
            case _:
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


def object_hash(fd, fmt, repo=None):
    """Compute object ID and optionally create a blob from a file."""
    data = fd.read()

    # Choose correct object type
    match fmt:
        case b"commit":
            obj = GitCommit(data)
        case b"tree":
            obj = GitTree(data)
        case b"tag":
            obj = GitTag(data)
        case b"blob":
            obj = GitBlob(data)
        case _:
            raise Exception(f"Unknown type {fmt}!")

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
        case "ls-tree":
            cmd_ls_tree(args)
        case "rev-parse":
            cmd_rev_parse(args)
        case "rm":
            cmd_rm(args)
        case "show-refs":
            cmd_show_refs(args)
        case "status":
            cmd_status(args)
        case "tag":
            cmd_tag(args)
        case _:
            print("invalid command.")
