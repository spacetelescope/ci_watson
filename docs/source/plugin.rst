.. _ci_watson_plugin:

Plugin
======

.. note::

   The ``--slow`` option conflicts in marker name with ``--run-slow``
   provided by ``pytest-astropy``. If you have both ``ci-watson``
   and ``pytest-astropy`` installed, you need to provide *both*
   option flags to enable tests marked as slow. See
   https://github.com/spacetelescope/ci_watson/issues/83 ,

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
* ``resource_tracker`` and ``log_tracked_resources`` fixtures to track
  memory and runtime and log them in the junit XML results file.

Configuration Options
---------------------

``inputs_root``/``results_root`` - The 'bigdata' remote repository name/local
data root directory for testing input/output files. Setting the value of
either option will make it availble to tests via the ``pytestconfig`` fixture.
Test code can then obtain the name of the artifactory repository/local data
root directory to use when accessing locations needed for running tests.

.. note::

    If used, these values should appear in either ``pytest.ini`` OR the appropriate
    section in ``pyproject.toml``, *not both*.

Example configuration within ``pyproject.toml``::

    [tool.pytest.ini_options]
    inputs_root = my_data_repo
    results_root = my_results_repo

Example configuration within ``pytest.ini``::

    [pytest]
    inputs_root = my_data_repo
    results_root = my_results_repo

The value(s) defined in the pytest configuration file may be accessed as a list
by test code via the ``pytestconfig`` fixture which must be passed in as an
argument to the test method or function that will use the value.

Example of accessing configuration values within test code itself:

.. code-block:: python

    def test_important_thing(pytestconfig):
        setup_cfg_inputs_root = pytestconfig.getini('inputs_root')[0]
        assert setup_cfg_inputs_root == 'my_data_repo'

From within a fixture or a test class the configuration values must be accessed
using a slightly different approach:

.. code-block:: python

    import pytest
    inputs_root = pytest.config.getini('inputs_root')[0]
