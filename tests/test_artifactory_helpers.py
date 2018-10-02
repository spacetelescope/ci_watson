"""
Tests requiring internet connection are treated as if they are big data tests.
We could use pytest-remotedata plugin but requiring another plugin to test
a plugin package is a little too meta.
"""
import json
import os

import pytest

from ci_watson.artifactory_helpers import (
    HAS_ASTROPY, ASTROPY_LT_3_1, BigdataError, get_bigdata_root, get_bigdata,
    check_url, compare_outputs, generate_upload_params, generate_upload_schema)


@pytest.mark.bigdata
@pytest.mark.parametrize(
    ('val', 'ans'),
    [('/local/path', False),
     ('https://google.com', True),
     ('https://github.com/spacetelescopehstcalblahblah', False)])
def test_check_url(val, ans):
    assert check_url(val) is ans


class TestBigdataRoot:
    def setup_class(self):
        self.key = 'FOOFOO'

    def teardown_class(self):
        if self.key in os.environ:
            del os.environ[self.key]

    def test_no_env(self):
        if self.key in os.environ:
            del os.environ[self.key]
        with pytest.raises(BigdataError):
            get_bigdata_root(envkey=self.key)

    @pytest.mark.bigdata
    def test_has_env_url(self):
        path = 'https://google.com'
        os.environ[self.key] = path
        assert get_bigdata_root(envkey=self.key) == path

    def test_has_env_local(self):
        path = os.path.abspath(os.curdir)
        os.environ[self.key] = path
        assert get_bigdata_root(envkey=self.key) == path

    def test_no_path(self):
        os.environ[self.key] = '/some/fake/path'
        assert get_bigdata_root(envkey=self.key) is None


@pytest.mark.bigdata
class TestGetBigdata:
    def setup_class(self):
        self.root = get_bigdata_root()

    def test_nocopy(self, _jail):
        args = ('ci-watson', 'dev', 'input', 'j6lq01010_asn.fits')
        dest = get_bigdata(*args, docopy=False)
        assert dest == os.path.abspath(os.path.join(self.root, *args))
        assert len(os.listdir()) == 0

    @pytest.mark.parametrize('docopy', [True, False])
    def test_no_data(self, docopy):
        with pytest.raises(BigdataError):
            get_bigdata('fake', 'path', 'somefile.txt', docopy=docopy)

    def test_get_data(self, _jail):
        """
        This tests download when TEST_BIGDATA is pointing to Artifactory.
        And tests copy when it is pointing to local path.
        """
        args = ('ci-watson', 'dev', 'input', 'j6lq01010_asn.fits')
        dest = get_bigdata(*args)
        assert dest == os.path.abspath(os.path.join(os.curdir, args[-1]))


@pytest.mark.bigdata
@pytest.mark.usefixtures('_jail')
@pytest.mark.skipif(not HAS_ASTROPY or ASTROPY_LT_3_1,
                    reason='requires astropy>=3.1 to run')
class TestCompareOutputs:
    """
    Test a few common comparison scenarios.

    FITSDiff and HDUDiff are tested in Astropy, so here we simply
    test if they report differences or not, but we do not check
    the content too closely.

    .. note:: Upload schema functions are tested separately elsewhere.

    """
    def setup_class(self):
        self.inpath = ('ci-watson', 'dev', 'input')

    def test_raise_error_fits(self):
        """Test mismatched extensions from the same file."""
        get_bigdata(*self.inpath, 'j6lq01010_asn.fits', docopy=True)
        outputs = [('j6lq01010_asn.fits[PRIMARY]', 'j6lq01010_asn.fits[asn]')]
        with pytest.raises(AssertionError) as exc:
            compare_outputs(outputs, input_path=self.inpath,
                            docopy=False, verbose=False)
            assert 'Headers contain differences' in str(exc)

    def test_difference_ascii(self):
        """
        Test ASCII with differences but suppress error to inspect
        returned report.
        """
        get_bigdata(*self.inpath, 'j6lq01010_asn_mod.txt', docopy=True)
        report = compare_outputs(
            [('j6lq01010_asn_mod.txt', 'j6lq01010_asn.txt')],
            input_path=self.inpath, docopy=False, verbose=False,
            raise_error=False)
        s = report.split(os.linesep)
        assert s[2:] == ['@@ -1,4 +1,4 @@',
                         ' # MEMNAME MEMTYPE MEMPRSNT',
                         '-J6LQ01NAQ EXP-CRJ 2',
                         '+J6LQ01NAQ EXP-CRJ 1',
                         ' J6LQ01NDQ EXP-CRJ 1',
                         '-J6LQ01013 PROD-RPT 1',
                         '+J6LQ01011 PROD-CRJ 1',
                         '']

    @pytest.mark.parametrize(
        'filename', ['j6lq01010_asn.fits', 'j6lq01010_asn.txt'])
    def test_all_okay(self, filename):
        """Same file has no difference."""
        get_bigdata(*self.inpath, filename, docopy=True)
        report = compare_outputs(
            [(filename, filename)], input_path=self.inpath,
            docopy=False, verbose=False)
        assert 'No differences found' in report

    @pytest.mark.parametrize('docopy', [False, True])
    def test_truth_missing(self, docopy):
        get_bigdata(*self.inpath, 'j6lq01010_asn.fits', docopy=True)
        with pytest.raises(AssertionError) as exc:
            compare_outputs(
                [('j6lq01010_asn.fits', 'doesnotexist.fits')],
                input_path=self.inpath, docopy=docopy, verbose=False)
            assert 'Cannot find doesnotexist.fits' in str(exc)

    @pytest.mark.parametrize(
        'outputs',
        [[('j6lq01010_asn.fits[ASN]', 'j6lq01010_asn_mod.fits', ['image'])],
         [('j6lq01010_asn.fits', 'j6lq01010_asn_mod.fits[ASN]', ['image'])]])
    def test_ambiguous_extlist(self, outputs):
        """Too many ways to do the same thing."""
        get_bigdata(*self.inpath, 'j6lq01010_asn.fits', docopy=True)
        with pytest.raises(AssertionError) as exc:
            compare_outputs(outputs, input_path=self.inpath, docopy=False,
                            verbose=False)
            assert 'Ambiguous extension requirements' in str(exc)

    def test_mixed_bunch(self):
        """
        Test different forms of acceptable ``outputs``.

        .. note:: Some other crazy combos are theoretically possible given
                  the logic but they are not officially supported, hence
                  not tested here. Add new combo as its support is added.

        """
        for filename in ('j6lq01010_asn.fits', 'j6lq01010_asn.txt'):
            get_bigdata(*self.inpath, filename, docopy=True)

        outputs = [('j6lq01010_asn.fits', 'j6lq01010_asn.fits'),
                   ('j6lq01010_asn.fits[asn]', 'j6lq01010_asn.fits[ASN]'),
                   {'files': ('j6lq01010_asn.fits[image]',
                              'j6lq01010_asn_mod.fits[IMAGE]'),
                    'pars': {'rtol': 1e-7, 'atol': 0.05}},
                   {'files': ('j6lq01010_asn.txt', 'j6lq01010_asn.txt')},
                   ('j6lq01010_asn.fits', 'j6lq01010_asn_mod.fits',
                    ['primary', 'IMAGE']),
                   ('j6lq01010_asn.txt', 'j6lq01010_asn.txt')]
        report = compare_outputs(outputs, input_path=self.inpath, docopy=False,
                                 verbose=False, raise_error=False)
        s = report.split(os.linesep)

        # TODO: Use regex?
        assert s[2] == ' a: j6lq01010_asn.fits'
        assert s[4:8] == [
            ' Maximum number of different data values to be reported: 10',
            ' Relative tolerance: 0.0, Absolute tolerance: 0.0',
            '',
            'No differences found.']
        assert s[9] == 'a: j6lq01010_asn.fits[asn]'
        assert s[11:14] == [' No differences found.',
                            '',
                            'a: j6lq01010_asn.fits[image]']
        assert s[15:18] == [' No differences found.',
                            '',
                            'a: j6lq01010_asn.txt']
        assert s[19:22] == ['No differences found.',
                            '',
                            'a: j6lq01010_asn.fits']
        assert s[27:31] == [
            ' Maximum number of different data values to be reported: 10',
            ' Relative tolerance: 0.0, Absolute tolerance: 0.0',
            '',
            'Extension HDU 1:']
        assert s[53:56] == [
            '     4 different pixels found (100.00% different).',
            '',
            'a: j6lq01010_asn.txt']
        assert s[57:] == ['No differences found.', '']


class TestGenerateUploadParams:
    def setup_class(self):
        self.old_envs = {}
        for key in ('BUILD_TAG', 'BUILD_MATRIX_SUFFIX'):
            self.old_envs[key] = os.environ.get(key)

        # Set up something reproducible
        os.environ['BUILD_TAG'] = 'tag0'
        os.environ['BUILD_MATRIX_SUFFIX'] = 'foo'

    def teardown_class(self):
        for key, val in self.old_envs.items():
            if val is None:
                del os.environ[key]
            else:
                os.environ[key] = val

    def test_gen(self, _jail):
        # Dummy file to move.
        datafile = 'actual.txt'
        with open(datafile, 'w') as f:
            f.write('\n')

        updated_outputs = [(datafile, '/path/to/desired.txt')]
        schema_pattern, tree, testname = generate_upload_params(
            'groot', updated_outputs, verbose=False)

        assert schema_pattern == ['*.log', 'desired.txt']
        assert isinstance(testname, str)  # Actual value non-deterministic

        # TODO: Use regex?
        split_tree = tree.split(os.sep)
        assert split_tree[0] == 'groot'
        assert split_tree[2].endswith('_tag0_foo')
        assert split_tree[3] == ''

        # Make sure file is moved properly.
        dirlist = os.listdir()
        assert dirlist == ['desired.txt']


def test_generate_upload_schema_multi(_jail):
    generate_upload_schema(
        ['*.log', 'desired.txt'], 'reponame/repopath', 'foo')
    # TODO: Better way to compare JSON?
    with open('foo_results.json') as f:
        j = json.load(f)
    assert json.dumps(j, indent=4, sort_keys=True).split(os.linesep) == [
        '{',
        '    "files": [',
        '        {',
        '            "excludePatterns": [],',
        '            "explode": "false",',
        '            "flat": "true",',
        '            "pattern": "*.log",',
        '            "props": null,',
        '            "recursive": "false",',
        '            "regexp": "false",',
        '            "target": "reponame/repopath"',
        '        },',
        '        {',
        '            "excludePatterns": [],',
        '            "explode": "false",',
        '            "flat": "true",',
        '            "pattern": "desired.txt",',
        '            "props": null,',
        '            "recursive": "false",',
        '            "regexp": "false",',
        '            "target": "reponame/repopath"',
        '        }',
        '    ]',
        '}']


def test_generate_upload_schema_one(_jail):
    generate_upload_schema(
        'desired.txt', 'reponame/repopath', 'foo', recursive=True)
    # TODO: Better way to compare JSON?
    with open('foo_results.json') as f:
        j = json.load(f)
    assert json.dumps(j, indent=4, sort_keys=True).split(os.linesep) == [
        '{',
        '    "files": [',
        '        {',
        '            "excludePatterns": [],',
        '            "explode": "false",',
        '            "flat": "true",',
        '            "pattern": "desired.txt",',
        '            "props": null,',
        '            "recursive": "true",',
        '            "regexp": "false",',
        '            "target": "reponame/repopath"',
        '        }',
        '    ]',
        '}']
