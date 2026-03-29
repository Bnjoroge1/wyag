from gitrepo import read_object

def log_graphviz(repo, sha, seen):

    if sha in seen:
        return
    seen.add(sha)

    # Lazy import to avoid circular imports at module import time.
    from gitrepo import read_object

    commit = read_object(repo, sha)
    if not commit:
        print("please provide a commit hash")
        return
    # Avoid circular imports: we don't type-check against GitCommit here.
    if not hasattr(commit, "kvlm") or not hasattr(commit, "fmt"):
        print("You did not pass a valid commit object")
        return
    message = commit.kvlm[None].decode("utf8").strip()
    message = message.replace("\\", "\\\\")
    message = message.replace('"', '\\"')

    if "\n" in message:  # Keep only the first line
        message = message[: message.index("\n")]

    print(f'  c_{sha} [label="{sha[0:7]}: {message}"]')
    assert commit.fmt == b"commit"

    if not b"parent" in commit.kvlm.keys():
        # Base case: the initial commit.
        return

    parents = commit.kvlm[b"parent"]

    if not isinstance(parents, list):
        parents = [parents]

    for p in parents:
        p = p.decode("ascii")
        print(f"  c_{sha} -> c_{p};")
        log_graphviz(repo, p, seen)
