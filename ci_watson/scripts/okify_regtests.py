import json
import os
import shutil
import subprocess
import tempfile
from argparse import ArgumentParser
from contextlib import contextmanager
from enum import Enum
from glob import glob
from pathlib import Path

import asdf
import readchar
from colorama import Fore

JSON_SPEC_FILE_SUFFIX = "_okify.json"
ASDF_BREADCRUMB_FILE_SUFFIX = "_rtdata.asdf"
TERMINAL_WIDTH = shutil.get_terminal_size((80, 20)).columns


class Observatory(Enum):
    jwst = "jwst"
    roman = "roman"

    def __str__(self):
        return self.value

    @property
    def runs_directory(self) -> str:
        """directory on Artifactory where run results are stored"""
        if self == Observatory.jwst:
            return "jwst-pipeline-results/"
        elif self == Observatory.roman:
            return "roman-pipeline-results/regression-tests/runs/"
        else:
            raise NotImplementedError(f"runs directory not defined for '{self}'")


def artifactory_copy(json_spec_file: os.PathLike, dry_run: bool = False):
    """
    copy files with `jf rt cp` based on instructions in the specfile

    :param json_spec_file: JSON file indicating file transfer patterns and targets (see https://docs.jfrog-applications.jfrog.io/jfrog-applications/jfrog-cli/cli-for-jfrog-artifactory/using-file-specs)
    :param dry_run: do nothing (passes `--dry-run` to JFrog CLI)
    :raises CalledProcessError: if JFrog command fails
    """

    jfrog_args = []

    if dry_run:
        jfrog_args.append("--dry-run")

    subprocess.run(
        ["jfrog", "rt", "cp", *jfrog_args, f"--spec={Path(json_spec_file).absolute()}"],
        check=True,
    )


def artifactory_folder_replace_copy(json_spec_file: os.PathLike, dry_run: bool = False):
    """
    copy files with `jf rt cp` based on instructions in the specfile, deleting the destination folder first

    :param json_spec_file: JSON file indicating file transfer patterns and targets (see https://docs.jfrog-applications.jfrog.io/jfrog-applications/jfrog-cli/cli-for-jfrog-artifactory/using-file-specs)
    :param dry_run: do nothing (passes `--dry-run` to JFrog CLI)
    :raises CalledProcessError: if JFrog command fails
    """

    jfrog_args = ["--quiet=true"]
    if dry_run:
        jfrog_args.append("--dry-run")

    # Since two different jfrog operations are required, need to read in
    # the spec to perform the delete.
    with open(json_spec_file) as file_handle:
        spec = json.load(file_handle)

    folder_pattern = spec["files"][0]["pattern"] + "/"
    folder_target = spec["files"][0]["target"]

    # Remove the target
    subprocess.run(
        [
            "jfrog",
            "rt",
            "del",
            *jfrog_args,
            f"{folder_target}{Path(folder_pattern).stem}",
        ],
        check=True,
    )

    artifactory_copy(json_spec_file, dry_run)


def artifactory_dispatch(
    json_spec_file: os.PathLike,
    replace_whole_folders: bool = False,
    dry_run: bool = False,
):
    """
    Perform the indicated artifactory operation

    :param json_spec_file: JSON file indicating file transfer patterns and targets (see https://docs.jfrog-applications.jfrog.io/jfrog-applications/jfrog-cli/cli-for-jfrog-artifactory/using-file-specs)
    :param replace_whole_folders: delete entire folders before copying
    :param dry_run: do nothing (passes `--dry-run` to JFrog CLI)
    :raises CalledProcessError: if JFrog command fails
    """

    if not replace_whole_folders:
        artifactory_copy(json_spec_file, dry_run=dry_run)
    else:
        artifactory_folder_replace_copy(json_spec_file, dry_run=dry_run)


def artifactory_download_run_files(
    runs_directory: os.PathLike | str, run_number: int, suffix: str
) -> list[Path]:
    """
    Download files with the given suffix from the given run.

    :param runs_directory: repository path where run directories are stored, i.e. `jwst-pipeline-results/` or `roman-pipeline-results/regression-tests/runs/`
    :param run_number: GitHub Actions job number of regression test run
    :param suffix: filename suffix to search for
    :returns: list of downloaded files on the local file system
    :raises CalledProcessError: if JFrog command fails

    Some example searches would be:

    .. code-block:: shell

        jfrog rt search jwst-pipeline-results/*_GITHUB_CI_*-586/*_okify.json
        jfrog rt search roman-pipeline-results/*/*_okify.json --props='build.number=540;build.name=RT :: romancal'

    """

    subprocess.run(
        [
            "jfrog",
            "rt",
            "dl",
            str(Path(runs_directory) / f"*_GITHUB_CI_*-{run_number}" / f"*{suffix}"),
        ],
        check=True,
        capture_output=True,
    )

    return sorted(Path().rglob(f'*{suffix}'))


def artifactory_download_regtest_artifacts(
    observatory: Observatory, run_number: int
) -> tuple[list[Path], list[Path]]:
    """
    Download both JSON spec files and ASDF breadcrumb files from Artifactory associated with a regression test run
    (via a job number), and return a list of their downloaded locations on the local file system.

    :param observatory: observatory to use
    :param run_number: GitHub Actions job number of regression test run
    :returns: two lists of downloaded files on the local file system; JSON specfiles, and ASDF breadcrumb files
    :raises CalledProcessError: if JFrog command fails
    """

    specfiles = artifactory_download_run_files(
        observatory.runs_directory, run_number, JSON_SPEC_FILE_SUFFIX
    )
    asdffiles = artifactory_download_run_files(
        observatory.runs_directory, run_number, ASDF_BREADCRUMB_FILE_SUFFIX
    )

    if len(specfiles) != len(asdffiles):
        raise RuntimeError("Different number of `_okify.json` and `_rtdata.asdf` files")

    for a, b in zip(specfiles, asdffiles):
        if str(a).replace(JSON_SPEC_FILE_SUFFIX, "") != str(b).replace(
            ASDF_BREADCRUMB_FILE_SUFFIX, ""
        ):
            raise RuntimeError(
                "The `_okify.json` and `_rtdata.asdf` files are not matched"
            )

    return specfiles, asdffiles


@contextmanager
def pushd(newdir: os.PathLike):
    """
    transient context that emulates `pushd` with `chdir`
    """

    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)


def main():
    parser = ArgumentParser(
        description='"okifies" a set of failing regression test results, by overwriting '
        "truth files on Artifactory so that a set of failing regression test results becomes correct. "
        "Requires JFrog CLI (https://jfrog.com/getcli/) configured with credentials (`jf login`) "
        "and write access to the desired truth file repository (`jwst-pipeline`, `roman-pipeline`, etc.)."
    )
    (
        parser.add_argument(
            "observatory",
            type=Observatory,
            choices=list(Observatory),
            help="Observatory to overwrite truth files for on Artifactory",
        ),
    )
    parser.add_argument(
        "run_number",
        help="GitHub Actions job number of regression test run (see https://github.com/spacetelescope/RegressionTests/actions)",
        metavar="run-number",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="do nothing (passes the `--dry-run` flag to JFrog CLI)",
    )

    args = parser.parse_args()

    run = args.run_number

    observatory = args.observatory

    # Create and chdir to a temporary directory to store specfiles
    with tempfile.TemporaryDirectory() as tmp_path:
        print(f"Downloading test logs to {tmp_path}")
        with pushd(tmp_path):
            # Retrieve all the okify specfiles for failed tests.
            json_spec_files, asdf_breadcrumb_files = (
                artifactory_download_regtest_artifacts(observatory, run)
            )

            number_failed_tests = len(json_spec_files)

            print(f"{number_failed_tests} failed tests to okify")

            for index, (json_spec_file, asdf_breadcrumb_file) in enumerate(
                zip(json_spec_files, asdf_breadcrumb_files)
            ):
                # Print traceback and OKify info for this test failure
                with asdf.open(asdf_breadcrumb_file) as asdf_breadcrumb:
                    # okify_op only useful for JWST
                    okify_op = (
                        asdf_breadcrumb.tree["okify_op"]
                        if observatory == Observatory.jwst
                        else "file_copy"
                    )
                    traceback = asdf_breadcrumb.tree["traceback"]
                    remote_results_path = Path(
                        asdf_breadcrumb.tree["remote_results_path"]
                    )
                    output = Path(asdf_breadcrumb.tree["output"])
                    truth_remote = asdf_breadcrumb.tree["truth_remote"]
                    try:
                        test_name = asdf_breadcrumb.tree["test_name"]
                    except KeyError:
                        test_name = "test_name"

                print(
                    f"{Fore.RED}"
                    + (f" {test_name} ".center(TERMINAL_WIDTH, "—"))
                    + f"{Fore.RESET}"
                )
                print(traceback)
                print(f"{Fore.RED}" + ("—" * TERMINAL_WIDTH) + f"{Fore.RESET}")
                print(f"{Fore.GREEN}OK: {remote_results_path / output.name}")
                print(f"--> {truth_remote}{Fore.RESET}")
                print(
                    f"{Fore.RED}"
                    + (
                        f"[ test {index + 1} of {number_failed_tests} ]".center(
                            TERMINAL_WIDTH, "—"
                        )
                    )
                    + f"{Fore.RESET}"
                )

                # Ask if user wants to okify this test
                commands = {
                    "o": ("okify", Fore.GREEN),
                    "s": ("skip", Fore.CYAN),
                    "q": ("quit", Fore.MAGENTA),
                }
                while True:
                    print(
                        ", ".join(
                            f"{color}'{command}' to {verb}{Fore.RESET}"
                            for command, (verb, color) in commands.items()
                        )
                        + ": "
                    )
                    # Get the keyboard character input without pressing return
                    result = readchar.readkey()
                    if result not in commands:
                        print(f"Unrecognized command '{result}', try again")
                    else:
                        break
                if result == "q":
                    break
                elif result == "s":
                    pass
                else:
                    artifactory_dispatch(
                        json_spec_file,
                        replace_whole_folders=okify_op == "folder_copy",
                        dry_run=args.dry_run,
                    )
                    print("")


if __name__ == "__main__":
    main()
