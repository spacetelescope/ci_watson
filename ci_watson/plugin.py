"""
These are automatically available when ``ci_watson`` is used as a
pytest plugin.
"""
import os
import pytest

__all__ = []


def pytest_addoption(parser):
    """
    These pytest hooks allow us to mark tests and run the marked tests with
    specific command line options.
    """
    # Add option to run slow tests
    parser.addoption(
        "--slow",
        action="store_true",
        help="run slow tests"
    )

    # Add option to use big data sets
    parser.addoption(
        "--bigdata",
        action="store_true",
        help="use big data sets (intranet)"
    )

    # Choose to test under dev or stable
    parser.addoption(
        "--env",
        default="dev",
        help="specify what environment to test"
    )

    # Data file input/output source/destination customization.
    parser.addini(
        "inputs_root",
        "Root dir (or data repository name) for test input files.",
        type="args",
        default=None,
    )

    parser.addini(
        "results_root",
        "Root dir (or data repository name) for test result/output files.",
        type="args",
        default=None,
    )


def pytest_configure(config):
    config.getini('markers').append(
        'slow: Run tests that are resource intensive')

    config.getini('markers').append(
        'bigdata: Run tests that require intranet access')


def pytest_runtest_setup(item):
    if 'slow' in item.keywords and not item.config.getvalue("slow"):
        pytest.skip("need --slow option to run")

    if 'bigdata' in item.keywords and not item.config.getvalue("bigdata"):
        pytest.skip("need --bigdata option to run")


@pytest.fixture(scope='function')
def _jail(tmpdir):
    """Perform test in a pristine temporary working directory."""
    old_dir = os.getcwd()
    os.chdir(tmpdir.strpath)
    try:
        yield tmpdir.strpath
    finally:
        os.chdir(old_dir)


@pytest.fixture(scope='session')
def envopt(request):
    """Get the ``--env`` command-line option specifying test environment"""
    return request.config.getoption("env")
