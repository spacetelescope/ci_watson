"""Helper module for HST tests."""

import os
import glob
import shutil
import warnings

import crds


__all__ = ['ref_from_image', 'raw_from_asn', 'download_crds']

CRDS_SERVER_URL = "https://hst-crds.stsci.edu"
HST_INSTRUMENTS = ['acs', 'wfc3', 'stis', 'cos', 'wfpc2']


def _get_reffile(hdr, key):
    """Get ref file from given key in given FITS header."""
    ref_file = None
    if key in hdr:  # Keyword might not exist
        ref_file = hdr[key].strip()
        if ref_file.upper() == 'N/A':  # Not all ref file is defined
            ref_file = None
    return ref_file


def ref_from_image(input_image, reffile_lookup):
    """
    Return a list of reference filenames, as defined in the primary
    header of the given input image, necessary for calibration.

    Parameters
    ----------
    input_image : str
        FITS image to extract info from.

    reffile_lookup : list of str
        List of primary header keywords to check. Example::

            ['IDCTAB', 'OFFTAB', 'NPOLFILE', 'D2IMFILE']

    Returns
    -------
    ref_files : list of str
        List of reference files needed for the test with given
        input file.

    """
    from astropy.io import fits

    ref_files = []
    hdr = fits.getheader(input_image, ext=0)

    for reffile in reffile_lookup:
        s = _get_reffile(hdr, reffile)
        if s is not None:
            ref_files.append(s)

    return ref_files


def raw_from_asn(asn_file, suffix='_raw.fits'):
    """
    Return a list of RAW input files in a given ASN.

    Parameters
    ----------
    asn_file : str
        Filename for the ASN file.

    suffix : str
        Suffix to append to the filenames in ASN table.

    Returns
    -------
    raw_files : list of str
        A list of input files to process.

    """
    from astropy.table import Table

    raw_files = []
    tab = Table.read(asn_file, format='fits')

    for row in tab:
        if row['MEMTYPE'].startswith('PROD'):
            continue
        pfx = row['MEMNAME'].lower().strip().replace('\x00', '')
        raw_files.append(pfx + suffix)

    return raw_files


def download_crds(refname, timeout=30, verbose=False):
    """
    Download a CRDS file from HTTP to current directory.

    Parameters
    ----------
    refname : str
        Filename. Examples::

            '012345678_bia.fits'
            'jref$012345678_bia.fits'
            '/path/to/012345678_bia.fits'

        But only filename with ``dir$name`` format would
        proceed to download stage.

    timeout : int or `None`
        Number of seconds before timeout error is raised.
        If `None`, no timeout happens but this is not recommended.

    verbose : bool
        If `True`, print messages to screen.
        This is useful for debugging.

    """
    refdir = None
    fname = refname
    warnings.warn('Deprecation Warning: `timeout` parameter no longer needed.')

    # Expand IRAF-style dir shortcut.
    if '$' in refname:
        refdir, fname = refname.split('$')
        if refdir in os.environ:
            refname = os.path.join(os.environ[refdir], fname)
        else:
            refname = fname

    # CRDS file for given name never changes, so no need to re-download
    # if already copied over prior or directly accessible on disk somewhere.
    if os.path.isfile(refname):
        if verbose:
            print('{} already exists, skipping download'.format(refname))
        return

    # Do not know where to download.
    if refdir is None:
        raise ValueError('Unknown HTTP destination for {}'.format(refname))

    # need to insure CRDS has been cached locally
    if 'CRDS_SERVER_URL' not in os.environ:
        os.environ['CRDS_SERVER_URL'] = CRDS_SERVER_URL
        os.environ['CRDS_PATH'] = '.' + os.sep
    # Make sure expected output directory is present in local directory
    tmpbase = os.path.join('references', 'hst')
    tmpref = os.path.join(tmpbase, HST_INSTRUMENTS[0])
    try:
        if not os.path.exists(tmpref):
            os.makedirs(tmpref)
        for inst in HST_INSTRUMENTS[1:]:
            tmppath = os.path.join(tmpbase, inst)
            if not os.path.exists(tmppath):
                os.mkdir(tmppath)

        # run the command to sync this CRDS file with local directory
        sync_cmd = crds.sync.SyncScript('sync --files ' + fname)
        sync_cmd.sync_explicit_files()  # copies file into subdir

        # Move the sync'd reference file to locally defined directory now
        # We need to find it first, though, since we are not sure what
        # instrument that reference file was for...
        tmpfile = glob.glob(os.path.join(tmpbase, '*', '*.fits'))[0]
        shutil.move(tmpfile, refname)

        if verbose:
            print('Downloaded {} from {}'.format(refname, CRDS_SERVER_URL))

    except Exception:
        print(f"Failed to download {fname}")

    finally:
        # delete tmp CRDS directories now, if possible.
        try:
            shutil.rmtree('references')
        except Exception:
            pass
