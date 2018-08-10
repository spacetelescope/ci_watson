"""Helper module for HST tests."""

__all__ = ['ref_from_image', 'raw_from_asn']


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
    # NOTE: Add additional mapping as needed.
    # Map mandatory CRDS reference file for instrument/detector combo.
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
