"""
Helpers for Artifactory or local big data handling.
"""
import copy
from datetime import datetime
import json
import os
import re
import shutil
import sys
import time
from difflib import unified_diff
from io import StringIO

try:
    from astropy.io import fits
    from astropy.io.fits import FITSDiff, HDUDiff
    from astropy.utils.introspection import minversion
    HAS_ASTROPY = True
except ImportError:
    HAS_ASTROPY = False

if HAS_ASTROPY and minversion('astropy', '3.1'):
    ASTROPY_LT_3_1 = False
else:
    ASTROPY_LT_3_1 = True

__all__ = ['BigdataError', 'check_url', 'get_bigdata_root', 'get_bigdata',
           'compare_outputs', 'generate_upload_params',
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

TODAYS_DATE = datetime.now().strftime("%Y-%m-%d")
TIMEOUT = int(os.environ.get("TEST_BIGDATA_TIMEOUT", 30))
CHUNK_SIZE = int(os.environ.get("TEST_BIGDATA_CHUNK_SIZE", 16384))
RETRY_MAX = int(os.environ.get("TEST_BIGDATA_RETRY_MAX", 3))
RETRY_DELAY = int(os.environ.get("TEST_BIGDATA_RETRY_DELAY", 5))

# Negative value disables timeout (i.e. hang forever)
if TIMEOUT < 0:
    TIMEOUT = None
# Timeout length cannot be zero
elif not TIMEOUT:
    TIMEOUT = 1

# Prevent chunks from being smaller than the usual physical block size
if CHUNK_SIZE < 512:
    CHUNK_SIZE = 512

# Prevent infinite retry loops
if RETRY_MAX < 0:
    RETRY_MAX = 0

# Prevent infinite retry wait
if RETRY_DELAY < 0:
    RETRY_DELAY = 0


class BigdataError(Exception):
    """Exception related to big data access."""
    pass


def retry(retries=RETRY_MAX, delay=RETRY_DELAY, trap=(Exception,)):
    """Execute a function again on error

    Parameters
    ----------
    retries: int
        Maximum number of attempts

    delay: int, float, None
        Maximum time to wait per attempt (seconds)

    trap: tuple of type Exception
        Type of exceptions to trap. Untrapped exceptions raise normally.
        Default: `Exception` (all exceptions)
    """
    def decorator(fn):
        def wrapper(*args, **kwargs):
            retry = 0
            while retry < retries:
                try:
                    return fn(*args, **kwargs)
                except trap as e:
                    print("{}: {}: will try again in {} second(s) "
                          "[attempt: {} of {}]".format(
                            fn, e, delay, retry + 1, retries), file=sys.stderr)
                    retry += 1
                    time.sleep(delay)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


@retry()
def check_url(url, timeout=TIMEOUT):
    """Determine if URL can be resolved without error."""
    if RE_URL.match(url) is None:
        return False

    # Optional import: requests is not needed for local big data setup.
    import requests

    # requests.head does not work with Artifactory landing page.
    r = requests.get(url, allow_redirects=True, timeout=timeout)
    # TODO: Can we simply return r.ok here?
    if r.status_code >= 400:
        return False
    return True


@retry()
def _download(url, dest, timeout=TIMEOUT, chunk_size=CHUNK_SIZE):
    """Simple HTTP/HTTPS downloader."""
    # Optional import: requests is not needed for local big data setup.
    import requests

    dest = os.path.abspath(dest)

    with requests.get(url, stream=True, timeout=timeout) as r:
        with open(dest, 'w+b') as data:
            for chunk in r.iter_content(chunk_size=chunk_size):
                data.write(chunk)

    return dest


def get_bigdata_root(envkey='TEST_BIGDATA'):
    """
    Find and returns the path to the nearest big datasets.

    Parameters
    ----------
    envkey : str
        Environment variable name. It must contain a string
        defining the root Artifactory URL or path to local
        big data storage.

    """
    if envkey not in os.environ:
        raise BigdataError(
            'Environment variable {} is undefined'.format(envkey))

    path = os.environ[envkey]

    if os.path.exists(path) or check_url(path):
        return path

    return None


def get_bigdata(*args, docopy=True, timeout=TIMEOUT, chunk_size=CHUNK_SIZE):
    """
    Acquire requested data from a managed resource
    to the current directory.

    Parameters
    ----------
    args : tuple of str
        Location of file relative to ``TEST_BIGDATA``.

    docopy : bool
        Switch to control whether or not to copy a file
        into the test output directory when running the test.
        If you wish to open the file directly from remote
        location or just to see path to source, set this to `False`.
        Default: `True`

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
    >>> get_bigdata('abc', '123', 'example.fits', docopy=False)
    /remote/root/abc/123/example.fits

    """
    src = os.path.join(get_bigdata_root(), *args)
    src_exists = os.path.exists(src)
    src_is_url = check_url(src)

    # No-op
    if not docopy:
        if src_exists or src_is_url:
            return os.path.abspath(src)
        else:
            raise BigdataError('Failed to find data: {}'.format(src))

    filename = os.path.basename(src)
    dest = os.path.abspath(os.path.join(os.curdir, filename))

    if src_exists:
        # Found src file on locally accessible directory
        if src == dest:  # pragma: no cover
            raise BigdataError('Source and destination paths are identical: '
                               '{}'.format(src))
        shutil.copy2(src, dest)

    elif src_is_url:
        _download(src, dest, timeout, chunk_size)

    else:
        raise BigdataError('Failed to retrieve data: {}'.format(src))

    return dest


def compare_outputs(outputs, raise_error=True, ignore_keywords=[],
                    ignore_hdus=[], ignore_fields=[], rtol=0.0, atol=0.0,
                    input_path=[], docopy=True, results_root=None,
                    verbose=True):
    """
    Compare output with "truth" using appropriate
    diff routine; namely:

    * ``fitsdiff`` for FITS file comparisons.
    * ``unified_diff`` for ASCII products.

    Only after all elements of ``outputs`` have been
    processed will the method report any success or failure, with
    failure of any one comparison *not* preventing the rest of the
    comparisons to be performed.

    Parameters
    ----------
    outputs : list of tuple or dict
        This list defines what outputs from running the test will be
        compared.  Three distinct types of values as list elements
        are supported:

        * 2-tuple : ``(test output filename, truth filename)``
        * 3-tuple : ``(test output filename, truth filename, HDU names)``
        * dict : ``{'files': (output, truth), 'pars': {key: val}}``

        If filename contains extension such as ``[hdrtab]``,
        it will be interpreted as specifying comparison of just that HDU.

    raise_error : bool
        Raise ``AssertionError`` if difference is found.

    ignore_keywords : list of str
        List of FITS header keywords to be ignored by
        ``FITSDiff`` and ``HDUDiff``.

    ignore_hdus : list of str
        List of FITS HDU names to ignore by ``FITSDiff``.
        This is only available for ``astropy>=3.1``.

    ignore_fields : list of str
        List FITS table column names to be ignored by
        ``FITSDiff`` and ``HDUDiff``.

    rtol, atol : float
        Relative and absolute tolerance to be used by
        ``FITSDiff`` and ``HDUDiff``.

    input_path : list or tuple
        A series of sub-directory names under :func:`get_bigdata_root`
        that leads to the path of the 'truth' files to be compared
        against. If not provided, it assumes that 'truth' is in the
        working directory. For example, with :func:`get_bigdata_root`
        pointing to ``/grp/test_data``, a file at::

            /grp/test_data/pipeline/dev/ins/test_1/test_a.py

        would require ``input_path`` of::

            ["pipeline", "dev", "ins", "test_1"]

    docopy : bool
        If `True`, 'truth' will be copied to output directory before
        comparison is done.

    results_root : str or `None`
        If not `None`, for every failed comparison, the test output
        is automatically renamed to the given 'truth' in the output
        directory and :func:`generate_upload_schema` will be called
        to generate a JSON scheme for Artifactory upload.
        If you do not need this functionality, use ``results_root=None``.

    verbose : bool
        Print extra info to screen.

    Returns
    -------
    creature_report : str
        Report from FITS or ASCII comparator.
        This is part of error message if ``raise_error=True``.

    Examples
    --------
    There are multiple use cases for this method, specifically
    related to how ``outputs`` are defined upon calling this method.
    The specification of the ``outputs`` can be any combination of the
    following patterns:

    1. 2-tuple inputs::

           outputs = [('file1.fits', 'file1_truth.fits')]

       This definition indicates that ``file1.fits`` should be compared
       as a whole with ``file1_truth.fits``.

    2. 2-tuple inputs with extensions::

           outputs = [('file1.fits[hdrtab]', 'file1_truth.fits[hdrtab]')]

       This definition indicates that only the HDRTAB extension from
       ``file1.fits`` will be compared to the HDRTAB extension from
       ``file1_truth.fits``.

    3. 3-tuple inputs::

           outputs = [('file1.fits', 'file1_truth.fits', ['primary', 'sci'])]

       This definition indicates that only the PRIMARY and SCI extensions
       should be compared between the two files. This creates a temporary
       ``HDUList`` object comprising only the given extensions for comparison.

    4. Dictionary of inputs and parameters::

           outputs = [{'files': ('file1.fits', 'file1_truth.fits'),
                       'pars': {'ignore_keywords': ['ROOTNAME']}}]

        This definition indicates that ROOTNAME will be ignored during
        the comparison between the files specified in ``'files'``.
        Any input parameter for ``FITSDiff`` or ``HDUDiff`` can be specified
        as part of the ``'pars'`` dictionary.
        In addition, the input files listed in ``'files'`` can also include
        an extension specification, such as ``[hdrtab]``, to limit the
        comparison to just that extension.

    This example from an actual test definition demonstrates
    how multiple input defintions can be used at the same time::

        outputs = [
            ('jw99999_nircam_f140m-maskbar_psfstack.fits',
             'jw99999_nircam_f140m-maskbar_psfstack_ref.fits'
            ),
            ('jw9999947001_02102_00002_nrcb3_a3001_crfints.fits',
             'jw9999947001_02102_00002_nrcb3_a3001_crfints_ref.fits'
            ),
            {'files': ('jw99999_nircam_f140m-maskbar_i2d.fits',
                       'jw99999_nircam_f140m-maskbar_i2d_ref.fits'),
             'pars': {'ignore_hdus': ['HDRTAB']},
            {'files': ('jw99999_nircam_f140m-maskbar_i2d.fits',
                       'jw99999_nircam_f140m-maskbar_i2d_ref.fits',
                       ['primary','sci','dq']),
             'pars': {'rtol': 0.000001}
            },
            {'files': ('jw99999_nircam_f140m-maskbar_i2d.fits[hdrtab]',
                       'jw99999_nircam_f140m-maskbar_i2d_ref.fits[hdrtab]'),
             'pars': {'ignore_keywords': ['NAXIS1', 'TFORM*'],
                      'ignore_fields': ['COL1', 'COL2']}
            }]

    .. note:: Each ``outputs`` entry in the list gets interpreted and processed
              separately.

    """
    if ASTROPY_LT_3_1:
        if len(ignore_hdus) > 0:  # pragma: no cover
            raise ValueError('ignore_hdus cannot be used for astropy<3.1')
        default_kwargs = {'rtol': rtol, 'atol': atol,
                          'ignore_keywords': ignore_keywords,
                          'ignore_fields': ignore_fields}
    else:
        default_kwargs = {'rtol': rtol, 'atol': atol,
                          'ignore_keywords': ignore_keywords,
                          'ignore_fields': ignore_fields,
                          'ignore_hdus': ignore_hdus}

    all_okay = True
    creature_report = ''
    updated_outputs = []  # To track outputs for Artifactory JSON schema

    for entry in outputs:
        diff_kwargs = copy.deepcopy(default_kwargs)
        extn_list = None
        num_entries = len(entry)

        if isinstance(entry, dict):
            entry_files = entry['files']
            actual = entry_files[0]
            desired = entry_files[1]
            if len(entry_files) > 2:
                extn_list = entry_files[2]
            diff_kwargs.update(entry.get('pars', {}))
        elif num_entries == 2:
            actual, desired = entry
        elif num_entries == 3:
            actual, desired, extn_list = entry
        else:
            all_okay = False
            creature_report += '\nERROR: Cannot handle entry {}\n'.format(
                entry)
            continue

        # TODO: Use regex?
        if actual.endswith(']'):
            if extn_list is not None:
                all_okay = False
                creature_report += (
                    '\nERROR: Ambiguous extension requirements '
                    'for {} ({})\n'.format(actual, extn_list))
                continue
            actual_name, actual_extn = actual.split('[')
            actual_extn = actual_extn.replace(']', '')
        else:
            actual_name = actual
            actual_extn = None

        if desired.endswith(']'):
            if extn_list is not None:
                all_okay = False
                creature_report += (
                    '\nERROR: Ambiguous extension requirements '
                    'for {} ({})\n'.format(desired, extn_list))
                continue
            desired_name, desired_extn = desired.split('[')
            desired_extn = desired_extn.replace(']', '')
        else:
            desired_name = desired
            desired_extn = None

        # Get "truth" image
        try:
            desired = get_bigdata(*input_path, desired_name, docopy=docopy)
        except BigdataError:
            all_okay = False
            creature_report += '\nERROR: Cannot find {} in {}\n'.format(
                desired_name, input_path)
            continue

        if desired_extn is not None:
            desired_name = desired
            desired = "{}[{}]".format(desired, desired_extn)

        if verbose:
            print("\nComparing:\n {} \nto\n {}".format(actual, desired))

        if actual.endswith('.fits') and desired.endswith('.fits'):
            # Build HDULists for comparison based on user-specified extensions
            if extn_list is not None:
                with fits.open(actual) as f_act:
                    with fits.open(desired) as f_des:
                        actual_hdu = fits.HDUList(
                            [f_act[extn] for extn in extn_list])
                        desired_hdu = fits.HDUList(
                            [f_des[extn] for extn in extn_list])
                        fdiff = FITSDiff(actual_hdu, desired_hdu,
                                         **diff_kwargs)
                        creature_report += '\na: {}\nb: {}\n'.format(
                            actual, desired)  # diff report only gives hash
            # Working with FITS files...
            else:
                fdiff = FITSDiff(actual, desired, **diff_kwargs)

            creature_report += fdiff.report()

            if not fdiff.identical:
                all_okay = False
                # Only keep track of failed results which need to
                # be used to replace the truth files (if OK).
                updated_outputs.append((actual, desired))

        elif actual_extn is not None or desired_extn is not None:
            if 'ignore_hdus' in diff_kwargs:  # pragma: no cover
                diff_kwargs.pop('ignore_hdus')  # Not applicable

            # Specific element of FITS file specified
            with fits.open(actual_name) as f_act:
                with fits.open(desired_name) as f_des:
                    actual_hdu = f_act[actual_extn]
                    desired_hdu = f_des[desired_extn]
                    fdiff = HDUDiff(actual_hdu, desired_hdu, **diff_kwargs)

            creature_report += '\na: {}\nb: {}\n'.format(actual, desired)
            creature_report += fdiff.report()

            if not fdiff.identical:
                all_okay = False
                # Only keep track of failed results which need to
                # be used to replace the truth files (if OK).
                updated_outputs.append((actual_name, desired_name))

        else:
            # ASCII-based diff
            with open(actual) as afile:
                actual_lines = afile.readlines()
            with open(desired) as dfile:
                desired_lines = dfile.readlines()

            udiff = unified_diff(actual_lines, desired_lines,
                                 fromfile=actual, tofile=desired)
            udiffIO = StringIO()
            udiffIO.writelines(udiff)
            udiff_report = udiffIO.getvalue()
            udiffIO.close()

            if len(udiff_report) == 0:
                creature_report += ('\na: {}\nb: {}\nNo differences '
                                    'found.\n'.format(actual, desired))
            else:
                all_okay = False
                creature_report += udiff_report
                # Only keep track of failed results which need to
                # be used to replace the truth files (if OK).
                updated_outputs.append((actual, desired))

    if not all_okay and results_root is not None:  # pragma: no cover
        schema_pattern, tree, testname = generate_upload_params(
            results_root, updated_outputs, verbose=verbose)
        generate_upload_schema(schema_pattern, tree, testname)

    if not all_okay and raise_error:
        raise AssertionError(os.linesep + creature_report)

    return creature_report


def generate_upload_params(results_root, updated_outputs, verbose=True):
    """
    Generate pattern, target, and test name for :func:`generate_upload_schema`.

    This uses ``BUILD_TAG`` and ``BUILD_MATRIX_SUFFIX`` on Jenkins CI to create
    meaningful Artifactory target path. They are optional for local runs.
    Other attributes like user, time stamp, and test name are also
    automatically determined.

    In addition to renamed outputs, ``*.log``is also inserted into the
    ``schema_pattern``.

    Parameters
    ----------
    results_root : str
        See :func:`compare_outputs` for more info.

    updated_outputs : list
        List containing tuples of ``(actual, desired)`` of failed
        test output comparison to be processed.

    verbose : bool
        Print extra info to screen.

    Returns
    -------
    schema_pattern, tree, testname
        Analogous to ``pattern``, ``target``, and ``testname`` that are
        passed into :func:`generate_upload_schema`, respectively.

    """
    import getpass

    # Create instructions for uploading results to artifactory for use
    # as new comparison/truth files
    testname = os.path.split(os.path.abspath(os.curdir))[1]

    # Meaningful test dir from build info.
    # TODO: Organize results by day test was run. Could replace with git-hash
    whoami = getpass.getuser() or 'nobody'
    user_tag = 'NOT_CI_{}'.format(whoami)
    build_tag = os.environ.get('BUILD_TAG', user_tag)
    build_matrix_suffix = os.environ.get('BUILD_MATRIX_SUFFIX', '0')
    subdir = '{}_{}_{}'.format(TODAYS_DATE, build_tag, build_matrix_suffix)
    tree = os.path.join(results_root, subdir, testname) + os.sep
    schema_pattern = []
    # Upload all log files
    schema_pattern.append('*.log')

    # Write out JSON file to enable retention of different results.
    # Also rename outputs as new truths.
    for test_result, truth in updated_outputs:
        new_truth = os.path.basename(truth)
        shutil.move(test_result, new_truth)
        schema_pattern.append(os.path.abspath(new_truth))
        if verbose:
            print("Renamed {} as new 'truth' file: {}".format(
                os.path.abspath(test_result), os.path.abspath(new_truth)))

    return schema_pattern, tree, testname


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

    if not isinstance(pattern, str):
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
        json.dump(upload_schema, outfile, indent=2)
