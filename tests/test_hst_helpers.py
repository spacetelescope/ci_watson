import pytest

from ci_watson.hst_helpers import raw_from_asn, download_crds

try:
    from astropy.table import Table
    HAS_ASTROPY = True
except ImportError:
    HAS_ASTROPY = False


@pytest.mark.skipif(not HAS_ASTROPY, reason='Need astropy to run')
def test_raw_from_asn(_jail):
    # Make a dummy input file (to avoid package data headache)
    tab = Table()
    tab['MEMNAME'] = ['J6LQ01NAQ', 'J6LQ01NDQ', 'J6LQ01011']
    tab['MEMTYPE'] = ['EXP-CRJ', 'EXP-CRJ', 'PROD-CRJ']
    tab['MEMPRSNT'] = [True, True, True]
    datafile = 'dummy_asn.fits'
    tab.write(datafile, format='fits', overwrite=True)

    raw_files = raw_from_asn(datafile)
    assert raw_files == ['j6lq01naq_raw.fits', 'j6lq01ndq_raw.fits']

    # Make sure do not download existing file.
    # This will fail if download is attemped.
    download_crds(datafile)
