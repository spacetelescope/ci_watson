.. ci_watson documentation master file, created by
   sphinx-quickstart on Tue Aug  7 16:43:10 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. _ci_watson_index:

*********
ci_watson
*********

``ci_watson`` is a test helper for Continuous Integration (CI) testing
at STScI using GitHub Actions and Artifactory.

This package has two components:

* ``pytest`` plugin containing markers and fixtures.
* Generic CI helpers for STScI tests using GitHub Actions and Artifactory.

To install the stable version of this package from PyPI::

  pip install ci-watson

To cite this package, please use its Zenodo DOI available at
https://zenodo.org/doi/10.5281/zenodo.12699836 .

.. toctree::
    :maxdepth: 1
    :hidden:

    plugin
    bigdata
    scripts
    ref_api

.. grid:: 2

    .. grid-item-card::

        .. button-ref:: plugin
            :expand:
            :color: primary
            :click-parent:

            ``pytest`` plugin

    .. grid-item-card::

        .. button-ref:: bigdata
            :expand:
            :color: primary
            :click-parent:

            Handling big data

    .. grid-item-card::

        .. button-ref:: scripts
            :expand:
            :color: primary
            :click-parent:

            Scripts (e.g., okify_regtests)

    .. grid-item-card::

        .. button-ref:: ref_api
            :expand:
            :color: primary
            :click-parent:

            Reference/API
