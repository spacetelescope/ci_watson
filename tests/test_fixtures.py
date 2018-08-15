import os
import pytest


def test_envopt(pytestconfig, envopt):
    """Test ``envopt`` fixture that is tied to ``--env`` option."""
    input_env = pytestconfig.getoption('env')
    assert input_env in ('dev', 'stable')
    assert envopt == input_env


# https://docs.pytest.org/en/latest/fixture.html
# Not that different from cleandir example.
@pytest.mark.usefixtures('_jail')
class TestDirectoryInit:
    """Test ``_jail`` fixture."""
    def test_cwd_starts_empty(self):
        assert os.listdir(os.getcwd()) == []
        with open("myfile", "w") as f:
            f.write("hello")

    @pytest.mark.parametrize('x', [1, 2])
    def test_cwd_again_starts_empty(self, x):
        assert os.listdir(os.getcwd()) == []
