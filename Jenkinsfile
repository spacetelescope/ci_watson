// Obtain files from source control system.
if (utils.scm_checkout()) return

// Test with default settings, this will skip slow and bigdata tests.
bc0 = new BuildConfig()
bc0.nodetype = "linux-stable"
bc0.name = "default"
bc0.conda_channels = ['http://ssb.stsci.edu/astroconda']
bc0.conda_packages = ['python=3.6', 'pytest']
bc0.build_cmds = ["python setup.py install"]
bc0.test_cmds = ["pytest tests"]

// Test that slow and bigdata tests are run.
// Also test stable env and another version of Python.
bc1 = utils.copy(bc0)
bc1.name = "runslow"
bc1.conda_packages[0] = "python=3.7"
bc1.test_cmds = ["pytest tests --slow --bigdata --env=stable"]

// Doc build test
bc2 = utils.copy(bc0)
bc2.name = "doc"
bc2.conda_channels = ['http://ssb.stsci.edu/astroconda', 'astropy']
bc2.conda_packages = ['python=3.6', 'pytest', 'numpydoc', 'sphinx-automodapi']
bc2.build_cmds = ["pip install sphinx_rtd_theme",
                  "python setup.py install"]
bc2.test_cmds = ["cd docs; make html"]

// Iterate over configurations that define the (distibuted) build matrix.
// Spawn a host of the given nodetype for each combination and run in parallel.
utils.run([bc0, bc1, bc2])
