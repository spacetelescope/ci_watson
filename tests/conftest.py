# For easy inspection on what dependencies were used in test.
def pytest_report_header(config):
    import sys

    s = "\nFull Python Version: \n{0}\n\n".format(sys.version)

    try:
        import warnings
        from astropy.utils.introspection import resolve_name
    except ImportError:
        return s

    for module_name in ('requests', 'numpy', 'astropy'):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                module = resolve_name(module_name)
        except ImportError:
            s += "{0}: not available\n".format(module_name)
        else:
            try:
                version = module.__version__
            except AttributeError:
                version = 'unknown (no __version__ attribute)'
            s += "{0}: {1}\n".format(module_name, version)

    return s
