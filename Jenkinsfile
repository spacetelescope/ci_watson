// Obtain files from source control system.
if (utils.scm_checkout()) return

// Test with default settings, this will skip slow and bigdata tests.
bc0 = new BuildConfig()
bc0.nodetype = "linux-stable"
bc0.build_mode = "default"
bc0.build_cmds = ["conda config --add channels http://ssb.stsci.edu/astroconda",
                  "conda install -q -y pytest",
                  "python setup.py install"]
bc0.test_cmds = ["pytest tests"]

// Test that slow and bigdata tests are run.
// Also test stable env.
bc1 = utils.copy(bc0)
bc1.build_mode = "runslow"
bc1.test_cmds = ["pytest tests --slow --bigdata --env=stable"]

// Iterate over configurations that define the (distibuted) build matrix.
// Spawn a host of the given nodetype for each combination and run in parallel.
utils.run([bc0, bc1])
