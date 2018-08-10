import pytest
from ci_watson.artifactory_helpers import get_bigdata, BigdataError


@pytest.mark.slow
def test_skip_slow(pytestconfig):
    if not pytestconfig.getoption('slow'):
        pytest.fail('@pytest.mark.slow was not skipped')


@pytest.mark.bigdata
def test_skip_bigdata(pytestconfig):
    if not pytestconfig.getoption('bigdata'):
        pytest.fail('@pytest.mark.bigdata was not skipped')

    # User use bigdata option and decorator but has no big data access.
    else:
        with pytest.raises(BigdataError):
            get_bigdata('foo', 'bar')
