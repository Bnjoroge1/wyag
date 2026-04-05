from gitrepo import repo_file, repo_dir, read_object
import os
import re



def resolve_ref(repo, ref) -> str | None:
    path = repo_file(repo, ref)
    if not path:
        return None
    
    if not os.path.isfile(path):
        return None
    
    with open(path, "r") as f:
        data = f.read()[:-1]
        
        if data.startswith("ref: "):
            return resolve_ref(repo, data[5:])
        else:
            return data


def list_refs(repo, path=None):
    if not path:
        path = repo_dir(repo, "refs")
    
    if path is None or isinstance(path, Exception):
        return {}
        
    ret = dict()
    
    for f in sorted(os.listdir(path)):
        can = os.path.join(path, f)
        if os.path.isdir(can):
            ret[f] = list_refs(repo, can)
        else:
            ret[f] = resolve_ref(repo, can)
            
    return ret
    

def resolve_object(repo: 'GitRepository', name: str) -> list[str | None] | None:
    """Resolve name to an object hash in repo.

    This function is aware of:

 - the HEAD literal
    - short and long hashes
    - tags
    - branches
    - remote branches"""
    candidates = []
    hashRE = re.compile(r"^[0-9A-Fa-f]{4,40}$")

    # Empty string?  Abort.
    if not name.strip():
        return None

    # Head is nonambiguous
    if name == "HEAD":
        return [ resolve_ref(repo, "HEAD") ]

    # If it's a hex string, try for a hash.
    if hashRE.match(name):
        # This may be a hash, either small or full.  4 seems to be the
        # minimal length for git to consider something a short hash.
        # This limit is documented in man git-rev-parse
        name = name.lower()
        prefix = name[0:2]
        path = repo_dir(repo, "objects", prefix, mkdir=False)
        
        if path:
            rem = name[2:]
            for f in os.listdir(path):
                if f.startswith(rem):
                    # Notice a string startswith() itself, so this
                    # works for full hashes.
                    candidates.append(prefix + f)

    # Try for references.
    as_tag = resolve_ref(repo, "refs/tags/" + name)
    if as_tag: # Did we find a tag?
        candidates.append(as_tag)

    as_branch = resolve_ref(repo, "refs/heads/" + name)
    if as_branch: # Did we find a branch?
        candidates.append(as_branch)

    as_remote_branch = resolve_ref(repo, "refs/remotes/" + name)
    if as_remote_branch: # Did we find a remote branch?
        candidates.append(as_remote_branch)

    return candidates

def object_find(
    repo: "GitRepository", name: str, fmt=None, follow: bool = True
) -> str | None:
    """Find the full SHA-1 hash for a given object name."""

    # For now, we are skipping tag resolution/branch names and just
    # handling direct SHA-1 hashes (the simplest case to start testing).
    sha = resolve_object(repo, name)

    if not sha:
        raise Exception(f"No such reference {name}.")
        return None

    if len(sha) > 1:
        raise Exception(f"Ambiguous reference {name}: Candidates are:\n - {'\n - '.join(sha)}.")

    sha = sha[0]
    if not sha:
        return None

    if not fmt:
        return sha

    while True:
        obj = read_object(repo, sha)
        if not obj:
            return
        #     ^^^^^^^^^^^ < this is a bit agressive: we're reading
        # the full object just to get its type.  And we're doing
        # that in a loop, albeit normally short.  Don't expect
        # high performance here.

        if obj.fmt == fmt:
            return sha

        if not follow:
            return None

        # Follow tags
        if obj.fmt == b'tag':
            if isinstance(obj, GitTag):
                sha = obj.kvlm[b'object'].decode("ascii")
        elif obj.fmt == b'commit' and fmt == b'tree':
            sha = obj.kvlm[b'tree'].decode("ascii")
        else:
            return None