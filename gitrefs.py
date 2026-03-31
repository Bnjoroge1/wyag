from gitrepo import repo_file, repo_dir
import os



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
    