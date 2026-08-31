0.13.1 (2016-08-13)
===================

- fixes an issue brought up by @melanieclarke where running ``okify_regtests jwst`` would fail 
  because ``argparse`` apparently looks for the enum _value_ instead of the name when matching [#110]

0.13.0 (2026-08-27)
===================

- standardize regression test results output to ``regression-tests/runs/`` [#101]
  This affects the location that ``okify_regtests`` looks for results directories on Artifactory.

0.12.0 (2026-08-04)
===================

- Switch ``slow`` marker to use upstream ``pytest-skip-slow`` plugin instead of
  the one defined in ``ci-watson``. [#105]

0.11.0 (2026-02-06)
===================

- ``okify_regtests`` no longer supports ``okify_op="folder_copy"``
  for JWST regression tests because it is no longer used downstream. [#92]
- Prompt the user to confirm they want to okify a rerun [#96]

0.10.0 (2025-06-18)
===================

- ``okify_regtests`` now supports new ``okify_op="sdp_pool_copy"``
  for JWST regression tests. [#86]

0.9.0 (2025-06-05)
==================

- Add ``resource_tracker`` and ``log_tracked_resources`` fixtures. [#74]
- Add new ``--version`` and ``--output-dir`` options for
  ``okify_regtests`` CLI. [#84]

0.8.0 (2024-12-09)
==================

- fix Ruff configuration [#67]
- move build configuration into ``pyproject.toml`` [#68]
- write ``okify_regtests`` script, generalizing ``jwst`` and ``romancal`` versions [#69]

0.7.0 (2024-07-09)
==================

- Removed deprecated timeout keyword from ``download_crds``. [#58]
