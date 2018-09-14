"""Helper module for JWST tests."""
import pytest

__all__ = ['require_crds_context']


# This is not in the plugin due to CRDS dependency.
def require_crds_context(required_context):
    """
    Ensure CRDS context is a certain level.

    Parameters
    ----------
    required_context : int
        The minimal level required.

    Returns
    -------
    decor : ``pytest.mark.skipif`` decorator
        Decorator to skip if ``CRDS_CONTEXT`` is not at lest a certain level.

    """
    import re
    import crds

    current_context_string = crds.get_context_name('jwst')
    match = re.match(r"jwst_(\d\d\d\d)\.pmap", current_context_string)
    current_context = int(match.group(1))

    return pytest.mark.skipif(
        current_context < required_context,
        reason='CRDS context {} less than required context {}'.format(
            current_context_string, required_context
        )
    )
