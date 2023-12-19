"""
backup_repos.py - back up a list of repositories from GitHub
------------------------------------------------------------

This script will clone the latest tagged release from each of the listed
repositories and add them to a compressed zip file, with the tag number
and datestamp included in the filename.

In the case that the repo has no tags, the tag name is replaced with
'repo_content'

Instructions:

# Add the url of the repo to the list at the bottom of the script
# Run the script using the commands below.

Dependencies:

* gitpython: https://gitpython.readthedocs.io/en/stable/index.html

Usage::

    python backup_repos.py


"""


import os
import shutil
import zipfile
import git
from datetime import datetime


def rmtree_onerror(func, path, exc_info):
    """
    Handle errors encountered during deletion with shutil.rmtree.
    Retry with different permissions to improve deletion success.
    """
    os.chmod(path, 0o777)
    func(path)


def get_latest_release_zip(repo_url, folder_path):
    # Parse the GitHub repository URL to get the repository name
    repo_name = repo_url.split("/")[-1].split(".")[0]

    # Create a folder if it doesn't exist
    os.makedirs(folder_path, exist_ok=True)

    # Clone the repository
    repo = git.Repo.clone_from(repo_url, f"{folder_path}/{repo_name}")

    # Check if there are any tags in the repository
    if not repo.tags:
        print(f"No tags found in the repository '{repo_url}'.")
        print("Creating a zip based on the repository content.")
        zip_file_name = (
            f'{repo_name}_repo_content_{datetime.now().strftime("%Y%m%d")}.zip'
        )
    else:
        # Get the latest release
        latest_release = repo.tags[-1]
        zip_file_name = f'{repo_name}_release_{latest_release.name}_{datetime.now().strftime("%Y%m%d")}.zip'   # noqa E501

    # Compress the latest release files into a zip file
    with zipfile.ZipFile(f"{folder_path}/{zip_file_name}", "w") as zip_file:
        for root, _, files in os.walk(f"{folder_path}/{repo_name}"):
            for file in files:
                file_path = os.path.join(root, file)
                zip_file.write(
                    file_path, os.path.relpath(file_path, f"{folder_path}/{repo_name}")  # noqa E501
                )

    repo.close()

    # Clean up: Delete the cloned repository
    shutil.rmtree(f"{folder_path}/{repo_name}", onerror=rmtree_onerror)


if __name__ == "__main__":

    repos = [
        "https://github.com/GeoscienceAustralia/tcrm",
        "https://github.com/GeoscienceAustralia/tcha",
        "https://github.com/GeoscienceAustralia/nhi-process",
        "https://github.com/GeoscienceAustralia/nhi-pylib",
        "https://github.com/GeoscienceAustralia/hazimp",
        "https://github.com/GeoscienceAustralia/nhi-tsed",
    ]
    for repo in repos:
        output_folder = r"X:\georisk\HaRIA_B_Wind\software"
        get_latest_release_zip(repo, output_folder)
