// Obtain files from source control system.
if (utils.scm_checkout()) return

// Test with default settings.
// This will skip slow and bigdata tests.
bc0 = new BuildConfig()
bc0.nodetype = "linux-stable"
bc0.name = "default"
bc0.conda_channels = ['http://ssb.stsci.edu/astroconda']
bc0.conda_packages = ['python=3.6', 'pytest=3.8']
bc0.build_cmds = ["python setup.py install"]
bc0.test_cmds = ["pytest tests"]

// Test that slow and bigdata tests are run in "stable" mode.
bc1 = utils.copy(bc0)
bc1.name = "stable"
bc1.env_vars = ['TEST_BIGDATA=https://bytesalad.stsci.edu/artifactory']
bc1.conda_packages = ['python=3.6', 'pytest=3.8', 'requests', 'numpy', 'astropy']
bc1.test_cmds = ["pytest tests --slow --bigdata --env=stable --basetemp=tests_output --junitxml results.xml"]

// Test that slow and bigdata tests are run in "dev" mode.
// Also test another version of Python.
bc2 = utils.copy(bc1)
bc2.name = "dev"
bc2.conda_packages = ['python=3.7', 'pytest=3.8', 'requests', 'numpy']
bc2.build_cmds = ["pip install git+https://github.com/astropy/astropy.git@master#egg=astropy --no-deps",
                  "python setup.py install"]
bc2.test_cmds = ["pytest tests --slow --bigdata --basetemp=tests_output --junitxml results.xml"]

// Doc build test
bc3 = utils.copy(bc0)
bc3.name = "doc"
bc3.conda_channels = ['http://ssb.stsci.edu/astroconda', 'astropy']
bc3.conda_packages = ['python=3.6', 'pytest=3.8', 'numpydoc', 'sphinx-automodapi']
bc3.build_cmds = ["pip install sphinx_rtd_theme",
                  "python setup.py install"]
bc3.test_cmds = ["cd docs; make html"]

// PEP 8 test
bc4 = utils.copy(bc0)
bc4.name = "pep8"
bc4.conda_packages = ['python=3.6', 'flake8']
bc4.build_cmds = []
bc4.test_cmds = ["flake8 --count"]

// Iterate over configurations that define the (distibuted) build matrix.
// Spawn a host of the given nodetype for each combination and run in parallel.
utils.run([bc0, bc1, bc2, bc3, bc4])
