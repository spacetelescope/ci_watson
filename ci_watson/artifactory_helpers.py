"""
Helpers for Artifactory or local big data handling.
"""
import getpass
import datetime
import sys
import copy
import json
import os
import re
import shutil
from io import StringIO
from collections import Iterable

from difflib import unified_diff
from astropy.io import fits
from astropy.io.fits import FITSDiff, HDUDiff

__all__ = ['BigdataError', 'get_bigdata_root', 'get_bigdata',
           'generate_upload_schema', 'compare_outputs',
           'get_hdu', 'build_hdulist']

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


def check_url(url):
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


def get_bigdata_root(envkey='TEST_BIGDATA'):
    """
    Find and returns the path to the nearest big datasets.
    """
    if envkey not in os.environ:
        raise BigdataError(
            'Environment variable {} is undefined'.format(envkey))

    val = os.environ[envkey]

#    if RE_URL.match(val) is not None:
#    val = os.path.join(val, repo)

    if isinstance(val, str):
        paths = [val]
    else:
        paths = val

    for path in paths:
        if os.path.exists(path) or check_url(path):
            return path

    return None


def get_bigdata(*args, docopy=True):
    """
    Acquire requested data from a managed resource
    to the current directory.

    Parameters
    ----------
    args : tuple of str
        Location of file relative to ``TEST_BIGDATA``.

    docopy : bool
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
    src = os.path.join(get_bigdata_root(), *args)
    filename = os.path.basename(src)
    dest = os.path.abspath(os.path.join(os.curdir, filename))
    is_url = check_url(src)

    if not docopy:
        return os.path.abspath(src)

    if os.path.exists(src) and not is_url:
        # Found src file on locally accessible directory
        if src == dest:
            raise BigdataError('Source and destination paths are identical: '
                               '{}'.format(src))
        shutil.copy2(src, dest)

    elif is_url:
        _download(src, dest)

    else:
        raise BigdataError('Failed to retrieve data: {}'.format(src))

    return dest


def compare_outputs(outputs, raise_error=True, **kwargs):
    """
    Compare output with "truth" using appropriate
    diff routine; namely,
        ``fitsdiff`` for FITS file comparisons
        ``unified_diff`` for ASCII products.

    Only after all elements of `outputs` have been
    processed will the method report any success or failure, with
    failure of any one comparison *not* preventing the rest of the
    comparisons to be performed.

    Parameters
    ----------
    outputs : list of tuple or dicts
        This list defines what outputs from running the test will be
        compared.  Three distinct types of values as list elements
        are supported::

          - 2-tuple : (test output filename, truth filename)
          - 3-tuple : (test output filename, truth filename, HDU names)
          - dict : {'files':[], 'pars':()}

        If filename contains extension such as '[hdrtab]' (no quotes),
        it will be interpreted as specifying comparison of just that HDU.

    raise_error : bool
        Raise ``AssertionError`` if difference is found.

    kwargs : keyword-value pairs
        These user-specified inputs will use these values for the
        parameters that control the operation of the diff
        functions used in the comparison; namely, FITSDiff and HDUDiff.
        This also includes the specification of the location of the
        comparison files and where the results should be stored.
        The currently supported attributes which can be overidden,
        along with type of values accepted, includes::

          - ignore_keywords : list
          - ignore_hdus : list
          - ignore_fields : list
          - rtol : float
          - atol : float
          - results_root : string
          - input_path : list

        where `input_path` would be the list of directory names in the full
        full path to the data.  For example, with `get_bigdata_root` pointing
        to '`\grp\test_data`, a file at ::

            `\grp\test_data\pipeline\dev\ins\test_1\test_a.py`

        would require `input_path` of ::

             `["pipeline","dev","ins","test_1"]`


    Returns
    -------
    report : str
        Report from ``fitsdiff``.
        This is part of error message if ``raise_error=True``.

    Syntax
    ------
    There are multiple use cases for this method, specifically
    related to how `outputs` are defined upon calling this method.
    The specification of the `outputs` can be any combination of the
    following patterns.

    1. 2-tuple inputs
        >>> outputs = [('file1.fits', 'file1_truth.fits')]

        This definition indicates that `file1.fits` should be compared
        as a whole with `file1_truth.fits`.

    2. 2-tuple inputs with extensions
        >>> outputs = [('file1.fits[hdrtab]',
                        'file1_truth.fits[hdrtab]')]

        This definition indicates that only the HDRTAB extension from
        `file1.fits` will be compared to the HDRTAB extension from
        `file1_truth.fits`.

    3.  3-tuple inputs
        >>> outputs = [('file1.fits', 'file1_truth.fits',
                        ['primary','sci','err','groupdq', 'pixeldq'])]

        This definition indicates that only the extensions specified
        in the list as the 3rd element of the tuple should be compared
        between the two files.  This will cause a temporary FITS
        HDUList object comprising only those extensions specified in
        the list to be generated for each file and those HDUList objects
        will then be compared.

    4.  dictionary of inputs and parameters
        >>> outputs = {'files':('file1.fits', 'file1_truth.fits'),
                       'pars':{'ignore_keywords':self.ignore_keywords+['ROOTNAME']}
                      }

        This definition indicates that all keywords defined by self.ignore_keywords
        along with ROOTNAME will be ignored during the comparison between the
        files specified in 'files'.  Any input parameter for FITSDiff
        or HDUDiff can be specified as part of the `pars` dictionary.
        In addition, the input files listed in `files` can also include
        an extension specification, such as '[hdrtab]', to limit the
        comparison to just that extension.

    Example:
    This example from an actual test definition demonstrates
    how multiple input defintions can be used at the same time.::

        outputs = [( # Compare psfstack product
                    'jw99999-a3001_t1_nircam_f140m-maskbar_psfstack.fits',
                    'jw99999-a3001_t1_nircam_f140m-maskbar_psfstack_ref.fits'
                   ),
                   (
                    'jw9999947001_02102_00002_nrcb3_a3001_crfints.fits',
                    'jw9999947001_02102_00002_nrcb3_a3001_crfints_ref.fits'
                   ),
                   {'files':( # Compare i2d product
                            'jw99999-a3001_t1_nircam_f140m-maskbar_i2d.fits',
                            'jw99999-a3001_t1_nircam_f140m-maskbar_i2d_ref.fits'
                     ),
                     'pars': {'ignore_hdus':self.ignore_hdus+['HDRTAB']}
                   },
                   {'files':( # Compare the HDRTAB in the i2d product
                    'jw99999-a3001_t1_nircam_f140m-maskbar_i2d.fits[hdrtab]',
                    'jw99999-a3001_t1_nircam_f140m-maskbar_i2d_ref.fits[hdrtab]'
                   ),
                    'pars': {'ignore_keywords':
                             self.ignore_keywords+['NAXIS1', 'TFORM*'],
                             'ignore_fields':self.ignore_keywords}
                   }
                  ]
    .. NOTE::
    Note that each entry in the list gets interpreted and processed
    separately.
    """
    all_okay = True
    creature_report = ''
    # Create instructions for uploading results to artifactory for use
    # as new comparison/truth files
    testpath, testname = os.path.split(os.path.abspath(os.curdir))
    # organize results by day test was run...could replace with git-hash
    whoami = getpass.getuser() or 'nobody'
    dt = datetime.datetime.now().strftime("%d%b%YT")
    ttime = datetime.datetime.now().strftime("%H_%M_%S")
    user_tag = 'NOT_CI_{}_{}'.format(whoami, ttime)
    build_tag = os.environ.get('BUILD_TAG',  user_tag)
    build_suffix = os.environ.get('BUILD_MATRIX_SUFFIX', 'standalone')
    testdir = "{}_{}_{}".format(testname, build_tag, build_suffix)

    updated_outputs = []
    extn_list = None
    for entry in outputs:
        # Parse any user-specified kwargs
        ignore_keywords = kwargs.get('ignore_keywords', [])
        ignore_hdus = kwargs.get('ignore_hdus', [])
        ignore_fields = kwargs.get('ignore_fields', [])
        rtol = kwargs.get('rtol', None)
        atol = kwargs.get('atol', None)
        input_path = kwargs.get('input_path', [])
        results_root = kwargs.get('results_root', None)
        docopy = kwargs.get('docopy', True)

        num_entries = len(entry)
        if isinstance(entry, dict):
            actual = entry['files'][0]
            desired = entry['files'][1]
            diff_pars = entry['pars']
            ignore_keywords = diff_pars.get('ignore_keywords', ignore_keywords)
            ignore_hdus = diff_pars.get('ignore_hdus', ignore_hdus)
            ignore_fields = diff_pars.get('ignore_fields', ignore_fields)
            rtol = diff_pars.get('rtol', rtol)
            atol = diff_pars.get('atol', atol)
        elif num_entries == 2:
            actual, desired = entry
        elif num_entries == 3:
            actual, desired, extn_list = entry

        if actual.endswith(']'):
            actual_name, actual_extn = actual.split('[')
            actual_extn = actual_extn.replace(']','')
        else:
            actual_name = actual
            actual_extn = None

        if desired.endswith(']'):
            desired_name, desired_extn = desired.split('[')
            desired_extn = desired_extn.replace(']','')
        else:
            desired_name = desired
            desired_extn = None

        # Get "truth" image
        s = get_bigdata(*input_path, desired_name,
                        docopy=docopy)
        if s is not None:
            desired = s
            if desired_extn is not None:
                desired = "{}[{}]".format(desired, desired_extn)
        print("\nComparing:\n {} \nto\n {}".format(actual, desired))
        if actual.endswith('fits'):
            # Build HDULists for comparison based on user-specified extensions
            if extn_list is not None:
                actual_hdu = build_hdulist(actual, extn_list)
                desired_hdu = build_hdulist(desired, extn_list)
            else:
                actual_hdu = actual
                desired_hdu = desired
            # Working with FITS files...
            fdiff = FITSDiff(actual_hdu, desired_hdu, rtol=rtol, atol=atol,
                             ignore_hdus=ignore_hdus,
                             ignore_keywords=ignore_keywords)
            creature_report += fdiff.report()
            if not fdiff.identical:
                # Only keep track of failed results which need to
                # be used to replace the truth files (if OK).
                updated_outputs.append((actual, desired))
            if not fdiff.identical and all_okay:
                all_okay = False
        elif desired_extn is not None:
            # Specific element of FITS file specified
            actual_hdu = get_hdu(actual)
            desired_hdu = get_hdu(desired)

            # Working with FITS Binary table with header...
            fdiff = HDUDiff(actual_hdu, desired_hdu, rtol=rtol, atol=atol,
                             ignore_keywords=ignore_keywords,
                             ignore_fields=ignore_fields)
            creature_report += fdiff.report()
            if not fdiff.identical:
                # Only keep track of failed results which need to
                # be used to replace the truth files (if OK).
                updated_outputs.append((actual_name, desired_name))
            if not fdiff.identical and all_okay:
                all_okay = False
        else:
            # ASCII-based diff
            with open(actual) as afile:
                actual_lines = afile.readlines()
            with open(desired) as dfile:
                desired_lines = dfile.readlines()
            udiff = unified_diff(actual_lines, desired_lines,
                                 fromfile=actual, tofile=desired)

            old_stdout = sys.stdout
            udiffIO = StringIO()
            sys.stdout = udiffIO
            sys.stdout.writelines(udiff)
            sys.stdout = old_stdout
            udiff_report = udiffIO.getvalue()
            creature_report += udiff_report
            if len(udiff_report) > 2 and all_okay:
                all_okay = False
            if len(udiff_report) > 2:
                # Only keep track of failed results which need to
                # be used to replace the truth files (if OK).
                updated_outputs.append((actual, desired))

    if not all_okay and results_root is not None:
        tree = os.path.join(results_root, input_loc,
                        dt, testdir) + os.sep

        # Write out JSON file to enable retention of different results
        new_truths = [os.path.basename(i[1]) for i in updated_outputs]
        for files, new_truth in zip(updated_outputs, new_truths):
            print("Renaming {} as new 'truth' file: {}".format(
                  files[0], new_truth))
            shutil.move(files[0], new_truth)
        log_pattern = [os.path.join(os.path.dirname(x), '*.log') for x in new_truths]
        generate_upload_schema(pattern=new_truths + log_pattern,
                       testname=testname,
                       target= tree)

    if not all_okay and raise_error:
        raise AssertionError(os.linesep + creature_report)

    return creature_report


def get_hdu(filename):
    """Return the HDU for the file and extension specified in the filename.

       This routine expects the filename to be of the format:
           <filename>.fits[extn]

        For example, "jw99999-a3001_t1_nircam_f140m-maskbar_i2d.fits[hdrtab]"
    """
    froot, fextn = filename.split('[')
    fextn = fextn.replace(']','')
    fits_file = fits.open(froot)
    return fits_file[fextn]

def build_hdulist(filename, extn_list):
    """Create a new HDUList object based on extensions specified in extn_list"""
    f = fits.open(filename)
    fhdu = [f[extn] for extn in extn_list]

    return fhdu


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
