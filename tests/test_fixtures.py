import os
import pytest


def test_envopt(pytestconfig, envopt):
    """Test ``envopt`` fixture that is tied to ``--env`` option."""
    input_env = pytestconfig.getoption('env')
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


class TestJail:
    """Test restoring working folders after jailing

    Note that if tests are run in parallel, these results may mean nothing.
    """

    @classmethod
    def setup_class(cls):
        cls.cwd = os.getcwd()

    def test_notintemp(self):
        """Ensure start state."""
        assert os.getcwd() == self.cwd

    @pytest.mark.usefixtures('_jail')
    def test_intemp(self):
        """Ensure that jailing occured"""
        assert not len(os.listdir(os.getcwd()))
        assert os.getcwd() != self.cwd

    def test_notintemppostjail(self):
        """Ensure that start state was recovered"""
        assert os.getcwd() == self.cwd


def test_get_jail_as_string(_jail):
    """Test that the _jail fixture returns the cwd as a string"""
    cwd = os.getcwd()
    cwd_jail = _jail

    assert cwd == cwd_jail
