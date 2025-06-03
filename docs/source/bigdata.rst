.. _bigdata_setup:

Big Data
========

The ``--bigdata`` option is used together with the environment variable,
``TEST_BIGDATA``, as used by
:func:`~ci_watson.artifactory_helpers.get_bigdata_root`. For local testing,
set this variable to where you downloaded your Artifactory data.
For remote testing (e.g., with GitHub Actions), set it to your Artifactory path
in the GitHub Actions workflow file, as appropriate. For more details,
please refer to STScI Innerspace document for
"Users Guide: Running Regression Tests".
