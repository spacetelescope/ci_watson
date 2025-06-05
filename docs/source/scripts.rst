.. _ci_watson_scripts:

Scripts
=======

This package also provides the following CLI:

* :ref:`ci_watson_okify`: Assist with okifying new outputs
  as new truths to resolve failing tests; only run this
  when you are very sure the new outputs are correct.

.. _ci_watson_okify:

okify_regtests
--------------

The ``okify_regtests`` command "okifies" a set of failing regression test
results, by overwriting truth files on Artifactory so that a set of
failing regression test results becomes correct. It requires
JFrog CLI (https://jfrog.com/getcli/) configured with valid credentials
(``jf login``) and write access to the desired truth file repository
(``jwst-pipeline``, ``roman-pipeline``, etc.).

To see the syntax and usage, from a terminal, type::

    okify_regtests --help

.. okifyregtestsclihelp::

Example for ``jwst``::

    okify_regtests jwst 956 --dry-run

Example for ``roman``:

    okify_regtests roman 1317
