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
  Additional setup is required for these tests to run successfully
  (see :ref:`bigdata_setup`).
  It is up to the author of the test to perform such setup properly.
* ``--env`` option and ``envopt`` fixture to set the test environment to
  ``"dev"`` or ``"stable"``. This plugin only sets the value. It is up to
  the author of the test to use this environment setting properly.
* ``_jail`` fixture to enable a test to run in a pristine temporary working
  directory. This is particularly useful for pipeline tests.
  
Configuration Options
---------------------

``inputs_root``/``results_root`` - The 'bigdata' remote repository name/local
data root directory for testing input/output files. Setting the value of
either option will make it availble to tests via the ``pytestconfig`` fixture.
Test code can then obtain the name of the artifactory repository/local data
root directory to use when accessing locations needed for running tests.

Note: If used, these values should appear in either ``pytest.ini`` OR the appropriate
section in ``setup.cfg``, *not both*.

Example configuration within ``setup.cfg``::

  [tool:pytest]
  inputs_root = my_data_repo
  results_root = my_results_repo

Example configuration within ``pytest.ini``::

  [pytest]
  inputs_root = my_data_repo
  results_root = my_results_repo

The value(s) defined in the pytest configuration file may be accessed as a list
by test code via the ``pytestconfig`` fixture which must be passed in as an
argument to the test method or function that will use the value.

Example of accessing configuration values within test code itself::

  def test_important_thing(pytestconfig):
      setup_cfg_inputs_root = pytestconfig.getini('inputs_root')[0]
      assert setup_cfg_inputs_root == 'my_data_repo'
      
From within a fixture or a test class the configuration values must be accessed using a slightly different approach::

    import pytest
    inputs_root = pytest.config.getini('inputs_root')[0]

.. _bigdata_setup:

Setting Up For Big Data
=======================

The ``--bigdata`` option is used together with the environment variable,
``TEST_BIGDATA``, as used by
:func:`~ci_watson.artifactory_helpers.get_bigdata_root`. For local testing,
set this variable to where you downloaded your Artifactory data.
For remote testing (e.g., with Jenkins CI), set it to your Artifactory path
in ``Jenkinsfile`` or ``JenkinsfileRT``, as appropriate. For more details,
please refer to STScI Innerspace document for
"Users Guide: Running Regression Tests".


Reference/API
=============

.. automodapi:: ci_watson.artifactory_helpers
    :no-inheritance-diagram:

.. automodapi:: ci_watson.hst_helpers
    :no-inheritance-diagram:

.. automodapi:: ci_watson.jwst_helpers
    :no-inheritance-diagram:
