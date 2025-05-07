import os
import pathlib
import dataclasses

import git


@dataclasses.dataclass
class GitInfo:
    git_relative_dir: str | None = None
    git_local_branch: str | None = None
    git_local_sha: str | None = None
    git_remote_url: str | None = None
    git_remote_branch: str | None = None
    git_remote_sha: str | None = None


def get_git_info(path: str | None = None) -> GitInfo | None:
    if not path:
        path = os.path.curdir
    try:
        repo = git.Repo(path, search_parent_directories=True)
    except git.InvalidGitRepositoryError:
        return None

    # Get relative path and convert it to POSIX
    relative_dir = pathlib.Path(path).relative_to(repo.working_tree_dir)
    posix_relative_dir = relative_dir.as_posix()
    info = GitInfo(
        git_relative_dir=posix_relative_dir,
        git_local_branch=repo.head.reference.name,
        git_local_sha=repo.head.reference.commit.hexsha,
    )
    tracking_branch: git.RemoteReference | None = repo.head.reference.tracking_branch()
    if tracking_branch:
        info.git_remote_branch = tracking_branch.remote_head
        info.git_remote_sha = tracking_branch.commit.hexsha
        info.git_remote_url = repo.remote(tracking_branch.remote_name).url

    return info
