from shutil import rmtree
from cybulde.utils.utils import run_shell_command


def get_cmd_to_get_raw_data(
        version: str,
        data_local_save_dir: str,
        dvc_remote_repo: str,
        dvc_data_folder: str,
        github_user_name: str,
        github_access_token: str
) -> str:
    """ Get shell command to download raw data from DVC store

    Parameters
    ----------
    version : str
        Version of the data to download
    data_local_save_dir : str
        Local directory to save the data
    dvc_remote_repo : str
        DVC remote repository URL
    dvc_data_folder : str
        DVC data folder path
    github_user_name : str
        GitHub user name
    github_access_token : str
        GitHub access token

    Returns
    -------
    str
        Shell command to download raw data from DVC store
    """
    without_https = dvc_remote_repo.replace("https://", "")
    dvc_remote_repo = f"https://{github_user_name}:{github_access_token}@{without_https}"
    command = f"dvc get {dvc_remote_repo} {dvc_data_folder} --rev {version} -o {data_local_save_dir}"
    return command


def get_raw_data_with_version(
    version: str,
    data_local_save_dir: str,
    dvc_remote_repo: str,
    dvc_data_folder: str,
    github_user_name: str,
    github_access_token: str
) -> None:
    rmtree(data_local_save_dir, ignore_errors=True)
    command = get_cmd_to_get_raw_data(
        version,
        data_local_save_dir,
        dvc_remote_repo,
        dvc_data_folder,
        github_user_name,
        github_access_token
    )
    run_shell_command(command)
