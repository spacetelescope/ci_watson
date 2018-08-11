.. ci_watson documentation master file, created by
   sphinx-quickstart on Tue Aug  7 16:43:10 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

*********
ci_watson
*********

``ci_watson`` is a test helper for Continuous Integration (CI) testing
at STScI using Jenkins and Artifactory.

This package has two components:

* ``pytest`` plugin containing markers and fixtures.
* Generic CI helpers for STScI tests using Jenkins and Artifactory.


Plugin
======

The plugin portion of ``ci_watson`` contains:

* ``--slow`` option and ``@pytest.mark.slow`` decorator to run or skip
  tests that are resource intensive. What counts as resource intensive
  is up to the author of the test.
* ``--bigdata`` option and ``@pytest.mark.bigdata`` decorator to run or skip
  tests that require intranet (Artifactory, Central Storage, etc) access.
  Additional setup is required for these tests to run successfully.
  It is up to the author of the test to perform such setup properly.
* ``--env`` option and ``envopt`` fixture to set the test environment to
  ``"dev"`` or ``"stable"``. This plugin only sets the value. It is up to
  the author of the test to use this environment setting properly.
* ``_jail`` fixture to enable a test to run in a pristine temporary working
  directory. This is particularly useful for pipeline tests.


Reference/API
=============

.. automodapi:: ci_watson.artifactory_helpers
    :no-inheritance-diagram:

.. automodapi:: ci_watson.hst_helpers
    :no-inheritance-diagram:

.. automodapi:: ci_watson.jwst_helpers
    :no-inheritance-diagram:
