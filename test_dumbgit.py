import os
import zlib
import pytest

from gitrepo import GitRepository, repo_path, repo_dir, repo_file
from gitstore import read_object, write_object
from gittree import GitBlob

@pytest.fixture
def repo(tmp_path):
    """Fixture to create a temporary GitRepository for testing."""
    repo_dir_path = tmp_path / "test_repo"
    repo_dir_path.mkdir()
    gitdir = repo_dir_path / ".git"
    gitdir.mkdir()

    # Initialize a basic repo object with force=True to skip config checks
    return GitRepository(str(repo_dir_path), force=True)


def test_repo_path(repo):
    """Test basic path construction"""
    expected = os.path.join(repo.gitdir, "objects", "e6")
    result = repo_path(repo, "objects", "e6")
    assert result == expected


def test_repo_dir_existing(repo):
    """Test repo_dir when the directory already exists"""
    obj_dir = os.path.join(repo.gitdir, "objects")
    os.mkdir(obj_dir)

    result = repo_dir(repo, "objects")
    assert result == obj_dir


def test_repo_dir_mkdir(repo):
    """Test repo_dir creating a new directory"""
    expected = os.path.join(repo.gitdir, "refs", "tags")

    assert not os.path.exists(expected)

    # Calling with mkdir=True should create it
    result = repo_dir(repo, "refs", "tags", mkdir=True)
    assert result == expected
    assert os.path.isdir(expected)


def test_repo_dir_not_exists_no_mkdir(repo):
    """Test repo_dir when it doesn't exist and mkdir=False"""
    result = repo_dir(repo, "nonexistent")
    assert result is None


def test_repo_dir_is_file(repo):
    """Test repo_dir when the path exists but is a file"""
    file_path = os.path.join(repo.gitdir, "config")
    with open(file_path, "w") as f:
        f.write("config data")

    result = repo_dir(repo, "config")

    # Based on the implementation in libwyag.py, it returns an Exception object
    assert isinstance(result, Exception)
    assert f"Not a directory: {file_path}" in str(result)


def test_repo_file_mkdir(repo):
    """Test that repo_file creates the parent directories when mkdir=True"""
    expected_file = os.path.join(repo.gitdir, "refs", "remotes", "origin", "HEAD")
    expected_dir = os.path.join(repo.gitdir, "refs", "remotes", "origin")

    assert not os.path.exists(expected_dir)

    # Calling repo_file with mkdir=True should create the parent directory
    result = repo_file(repo, "refs", "remotes", "origin", "HEAD", mkdir=True)

    assert result == expected_file
    assert os.path.isdir(expected_dir)


def test_repo_file_no_mkdir_missing_dir(repo):
    """Test repo_file when parent dir is missing and mkdir=False"""
    # Because repo_dir returns None when missing and mkdir=False,
    # repo_file should also return None implicitly
    result = repo_file(repo, "missing", "dir", "file")
    assert result is None


def test_write_object_no_repo():
    """Test that write_object calculates the correct hash and serializes data without a repo"""
    data = b"hello world"
    blob = GitBlob(data)

    # Expected format: b'blob 11\x00hello world'
    # Hash is SHA1 of the above
    import hashlib
    expected_hash = hashlib.sha1(b"blob 11\x00hello world").hexdigest()

    # We pass repo=None so it doesn't write to disk
    result_hash = write_object(blob, repo=None)

    assert result_hash == expected_hash

def test_write_read_object_with_repo(repo):
    """Test writing an object to the repository and reading it back"""
    data = b"test repository data"
    blob = GitBlob(data)

    # Write to repository
    obj_hash = write_object(blob, repo)
    if not obj_hash:
        assert False
        
    # Directly verify the file was written to the correct location
    obj_dir = obj_hash[:2]
    obj_file = obj_hash[2:]
    expected_path = os.path.join(repo.gitdir, "objects", obj_dir, obj_file)

    assert os.path.exists(expected_path)

    # Verify the contents are compressed
    with open(expected_path, "rb") as f:
        compressed_data = f.read()
        raw_data = zlib.decompress(compressed_data)
        assert raw_data == b"blob 20\x00test repository data"

    # Test reading the object back using read_object
    read_obj = read_object(repo, obj_hash)

    assert isinstance(read_obj, GitBlob)
    assert read_obj.serialize() == data

def test_read_nonexistent_object(repo):
    """Test read_object handles missing objects correctly"""
    result = read_object(repo, "0000000000000000000000000000000000000000")
    assert result is None
