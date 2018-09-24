"""
Helpers for Artifactory or local big data handling.
"""
import copy
import json
import os
import re
import shutil
from collections import Iterable

__all__ = ['BigdataError', 'get_bigdata_root', 'get_bigdata',
           'generate_upload_schema']

RE_URL = re.compile(r"\w+://\S+")

UPLOAD_SCHEMA = {"files": [
                    {"pattern": "",
                     "target": "",
                     "props": None,
                     "recursive": "false",
                     "flat": "true",
                     "regexp": "false",
                     "explode": "false",
                     "excludePatterns": []}]}


class BigdataError(Exception):
    """Exception related to big data access."""
    pass


def _is_url(url):
    """Determine if URL can be resolved without error."""
    if RE_URL.match(url) is None:
        return False

    import requests

    # requests.head does not work with Artifactory landing page.
    r = requests.get(url, allow_redirects=True)
    # TODO: Can we simply return r.ok here?
    if r.status_code >= 400:
        return False
    return True


def _download(url, dest, timeout=30):
    """Simple HTTP/HTTPS downloader."""
    import requests

    dest = os.path.abspath(dest)

    with requests.get(url, stream=True, timeout=timeout) as r:
        with open(dest, 'w+b') as data:
            for chunk in r.iter_content(chunk_size=0x4000):
                data.write(chunk)

    return dest


def get_bigdata_root(repo='', envkey='TEST_BIGDATA'):
    """
    Find and returns the path to the nearest big datasets.
    """
    if envkey not in os.environ:
        raise BigdataError(
            'Environment variable {} is undefined'.format(envkey))

    val = os.environ[envkey]

    if RE_URL.match(val) is not None:
            val = os.path.join(val, repo)

    if isinstance(val, str):
        paths = [val]
    else:
        paths = val

    for path in paths:
        if os.path.exists(path) or _is_url(path):
            return path

    return None


def get_bigdata(*args, repo='', copy_local=True):
    """
    Acquire requested data from a managed resource
    to the current directory.

    Parameters
    ----------
    args : tuple of str
        Location of file relative to ``TEST_BIGDATA``.

    repo : str
        Name of repository on Artifactory where data is located.  This will be
        appended to whatever was specified in ``TEST_BIGDATA`` to complete
        the URL for finding the data for the test, if ``TEST_BIGDATA`` was
        specified as a URL in the first place. Default: ''

    copy_local : bool
        Switch to control whether or not to copy a file found on local directory
        into the test output directory when running the test.  Default: True

    Returns
    -------
    dest : str
        Absolute path to local copy of data
        (i.e., ``/path/to/example.fits``).

    Examples
    --------
    >>> import os
    >>> print(os.getcwd())
    /path/to
    >>> from ci_watson.artifactory_helpers import get_bigdata
    >>> filename = get_bigdata('abc', '123', 'example.fits')
    >>> print(filename)
    /path/to/example.fits

    """
    src = os.path.join(get_bigdata_root(repo=repo), *args)
    filename = os.path.basename(src)
    dest = os.path.abspath(os.path.join(os.curdir, filename))
    is_url = _is_url(src)

    if os.path.exists(src) and not is_url:
        # Found src file on locally accessible directory
        if src == dest:
            raise BigdataError('Source and destination paths are identical: '
                               '{}'.format(src))
        if copy_local:
            shutil.copy2(src, dest)
        else:
            dest = os.path.abspath(src)

    elif is_url:
        _download(src, dest)

    else:
        raise BigdataError('Failed to retrieve data: {}'.format(src))

    return dest


def generate_upload_schema(pattern, target, testname, recursive=False):
    """
    Write out JSON file to upload Jenkins results from test to
    Artifactory storage area.

    This function relies on the JFROG JSON schema for uploading data into
    artifactory using the Jenkins plugin.  Docs can be found at
    https://www.jfrog.com/confluence/display/RTF/Using+File+Specs

    Parameters
    ----------
    pattern : str or list of strings
        Specifies the local file system path to test results which should be
        uploaded to Artifactory. You can specify multiple artifacts by using
        wildcards or a regular expression as designated by the regexp property.

    target : str
        Specifies the target path in Artifactory in the following format::

            [repository_name]/[repository_path]

    testname : str
        Name of test that generate the results. This will be used to create the
        name of the JSON file to enable these results to be uploaded to
        Artifactory.

    recursive : bool, optional
        Specify whether or not to identify files listed in sub-directories
        for uploading.  Default: `False`

    """
    jsonfile = "{}_results.json".format(testname)
    recursive = repr(recursive).lower()

    if isinstance(pattern, Iterable):
        # Populate schema for this test's data
        upload_schema = {"files": []}

        for p in pattern:
            temp_schema = copy.deepcopy(UPLOAD_SCHEMA["files"][0])
            temp_schema.update({"pattern": p, "target": target,
                                "recursive": recursive})
            upload_schema["files"].append(temp_schema)

    else:
        # Populate schema for this test's data
        upload_schema = copy.deepcopy(UPLOAD_SCHEMA)
        upload_schema["files"][0].update({"pattern": pattern, "target": target,
                                          "recursive": recursive})

    # Write out JSON file with description of test results
    with open(jsonfile, 'w') as outfile:
        json.dump(upload_schema, outfile)
