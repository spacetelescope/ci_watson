# ci_watson

[![DOI](https://zenodo.org/badge/143923649.svg)](https://zenodo.org/doi/10.5281/zenodo.12699836)
[![CI Status](https://github.com/spacetelescope/ci_watson/workflows/CI/badge.svg)](https://github.com/spacetelescope/ci_watson/actions)
[![Documentation Status](https://readthedocs.org/projects/ci-watson/badge/?version=latest)](https://ci-watson.readthedocs.io/en/latest/?badge=latest)

CI helper for STScI regression tests.
If you ask nicely, it might also help you solve crimes.

Nightly regression test results are available only from within the STScI
network at this time.

## Installation

```console
pip install ci-watson
```

## Scripts

### `okify_regtests`

```console
usage: okify_regtests [-h] [--dry-run] {jwst,roman} run-number

"okifies" a set of failing regression test results, by overwriting truth files on
Artifactory so that a set of failing regression test results becomes correct. Requires
JFrog CLI (https://jfrog.com/getcli/) configured with credentials (`jf login`) and write
access to the desired truth file repository (`jwst-pipeline`, `roman-pipeline`, etc.).

positional arguments:
  {jwst,roman}  Observatory to overwrite truth files for on Artifactory
  run-number    GitHub Actions job number of regression test run (see
                https://github.com/spacetelescope/RegressionTests/actions)

options:
  -h, --help    show this help message and exit
  --dry-run     do nothing (passes the `--dry-run` flag to JFrog CLI)
```

#### examples

```console
okify_regtests jwst 956 --dry-run
okify_regtests roman 1317
```
