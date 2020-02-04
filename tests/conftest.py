from pytest_astropy_header.display import (PYTEST_HEADER_MODULES,
                                           TESTED_VERSIONS)


def pytest_configure(config):
    PYTEST_HEADER_MODULES.pop('h5py')
    PYTEST_HEADER_MODULES.pop('Pandas')
    PYTEST_HEADER_MODULES['astropy'] = 'astropy'
    PYTEST_HEADER_MODULES['requests'] = 'requests'

    from ci_watson.version import version
    TESTED_VERSIONS['ci-watson'] = version
