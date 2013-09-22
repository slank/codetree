import os
from unittest import TestCase
from urlparse import urlparse
from tempfile import mkdtemp
from urllib2 import URLError
import subprocess
import shutil
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

from mock import (
    patch,
    MagicMock,
    mock_open,
)

from codetree.handlers import (
    strip_trailing_slash,
    log_failure,
    CommandFailure,
    SourceHandler,
    BzrSourceHandler,
    LocalHandler,
    HttpFileHandler,
)

BzrURLs = (
    "bzr://example.com/foo/",
    "lp:debian/apt/",
    "bzr+ssh://bazaar.launchpad.net/~foo/bar/trunk/",
    "bzr+http://example.com/foo/",
    "bzr+https://example.com/foo/",
    "lp:debian/apt",
)

HttpURLs = (
    "http://example.com/foo.txt",
    "https://example.com/foo.txt",
)

LocalURLs = (
    "file:///etc/hosts",
    "/etc/hosts",
    "etc/hosts",
    "../etc/hosts",
    "hosts"
    "/etc"
)


def was_called_with_cmd(mock, cmd):
    for call_args in mock.call_args_list:
        if call_args[0][0] == cmd:
            return True
    return False


def shellcmd(cmd):
    try:
        subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print "------- output --------"
        print e.output
        print "-----------------------"
        raise


class TestLogHandlers(TestCase):
    @patch("codetree.handlers.check_output")
    def test_log_failure_success(self, _call):
        cmd = ("echo", "hello world")
        log_failure(cmd, "Saying hello")
        assert(was_called_with_cmd(_call, cmd))

    def test_log_failure_failure(self):
        # Throws OSError
        cmd = ("/invalid/cmd", "hello world")
        self.assertFalse(log_failure(cmd, "Saying hello"))
        with self.assertRaises(CommandFailure):
            log_failure(cmd, "Failing", fatal=True)

        cmd = ("false",)
        self.assertFalse(log_failure(cmd, "Failing"))
        with self.assertRaises(CommandFailure):
            log_failure(cmd, "Failing", fatal=True)

    def test_strip_trailing_slash(self):
        value = "abc"
        self.assertEqual(value, strip_trailing_slash(value))
        self.assertEqual(value, strip_trailing_slash(value + "/"))


class TestSourceHandler(TestCase):
    def setUp(self):
        super(TestSourceHandler, self).setUp()
        self.source = "foo"
        self.sh = SourceHandler("foo")

    def test_stores_source(self):
        self.assertEqual(self.sh.source, self.source)

    def test_handles_nothing(self):
        self.assertEqual(SourceHandler.schemes, tuple())


class BzrSourceHandlerTest(TestCase):
    def test_url_handling(self):
        for url in BzrURLs:
            assert(urlparse(url).scheme in BzrSourceHandler.schemes)

    def test_stores_source(self):
        url = BzrURLs[0]
        bh = BzrSourceHandler(url)
        self.assertEqual(bh.source, url)

    def test_nonstandard_schemes(self):
        http_url = "bzr+http://example.com/repo"
        bh = BzrSourceHandler(http_url)
        self.assertTrue(bh.source.startswith("http"))

        https_url = "bzr+https://example.com/repo"
        bh = BzrSourceHandler(https_url)
        self.assertTrue(bh.source.startswith("https"))

    @patch("codetree.handlers.check_output")
    @patch("codetree.handlers.logging")
    @patch("codetree.handlers.os.path.exists", return_value=True)
    @patch("codetree.handlers.shutil.rmtree")
    def test_overwite(self, _rmtree, _exists, _log, _call):
        source = BzrURLs[0]
        dest = "foo"
        bh = BzrSourceHandler(source)
        bh.is_same_branch = MagicMock(return_value=False)

        # overwrite (delete) existing when asked
        options = {"overwrite": True}
        self.assertTrue(bh.get(dest, options))
        _rmtree.assert_called_with(dest)

        # don't overwrite if not asked
        options = {"overwrite": False}
        self.assertFalse(bh.get(dest, options))
        _rmtree.assert_not_called()

        # don't overwrite if source = parent
        options = {"overwrite": True}
        bh.is_same_branch = MagicMock(return_value=True)
        self.assertTrue(bh.get(dest, options))
        _rmtree.assert_not_called()

    @patch("codetree.handlers.check_output")
    @patch("codetree.handlers.os.path.exists", return_value=False)
    def test_branches_new(self, _exists, _call):
        source = BzrURLs[0]
        dest = "foo"
        bh = BzrSourceHandler(source)
        self.assertTrue(bh.get(dest))
        self.assertTrue(was_called_with_cmd(_call, ('bzr', 'branch', source, dest)))

    @patch("codetree.handlers.check_output")
    @patch("codetree.handlers.os.makedirs")
    def test_creates_new_dirs(self, _makedirs, _call):
        source = BzrURLs[0]
        dest = "foo/bar/baz"
        bh = BzrSourceHandler(source)
        self.assertTrue(bh.get(dest))
        _makedirs.assert_called_with(os.path.dirname(dest))

    @patch("codetree.handlers.check_output")
    @patch("codetree.handlers.os.path.exists", return_value=True)
    def test_updates_existing(self, _exists, _call):
        source = BzrURLs[0]
        dest = "foo"
        bh = BzrSourceHandler(source)
        bh.is_same_branch = MagicMock(return_value=True)
        self.assertTrue(bh.get(dest))
        assert(was_called_with_cmd(_call, ('bzr', 'pull', '-d', dest)))

    @patch("codetree.handlers.check_output")
    def test_gets_revno(self, _call):
        source = BzrURLs[0]
        dest = "foo"
        bh = BzrSourceHandler(source)
        bh.is_same_branch = MagicMock()

        revno = "1"
        options = {"revno": "1"}
        self.assertTrue(bh.get(dest, options))
        assert(was_called_with_cmd(_call, ('bzr', 'update', dest, '-r', revno)))

    def test_same_branch(self):
        parent = mkdtemp()
        self.addCleanup(shutil.rmtree, parent)
        shellcmd("bzr init {}".format(parent))
        bh = BzrSourceHandler(parent)

        child_tmp = mkdtemp()
        self.addCleanup(shutil.rmtree, child_tmp)

        # is same
        child = os.path.join(child_tmp, "child") + "/"
        shellcmd("bzr branch {} {}".format(parent, child))
        self.assertTrue(bh.is_same_branch(child))

        # is not the same
        nonchild = os.path.join(child_tmp, "nonchild")
        shellcmd("bzr branch {} {}".format(child, nonchild))
        self.assertFalse(bh.is_same_branch(nonchild), "test: is not same")

        # is standalone
        stdalone = os.path.join(child_tmp, "stdalone")
        shellcmd("bzr init {}".format(stdalone))
        self.assertFalse(bh.is_same_branch(stdalone), "test: is standalone")


class TestLocalHandler(TestCase):
    def test_url_handling(self):
        for local_url in LocalURLs:
            assert(urlparse(local_url).scheme in LocalHandler.schemes)

    @patch("codetree.handlers.fileutils.mkdir")
    def creates_directory(self, _mkdir):
        lh = LocalHandler("@")
        self.assertTrue(lh.get("foo"))
        _mkdir.assert_called_with('foo', overwrite=False)


class TestHttpFileHandler(TestCase):
    def test_url_handling(self):
        for http_url in HttpURLs:
            assert(urlparse(http_url).scheme in HttpFileHandler.schemes)

    @patch('codetree.handlers.os.unlink')
    @patch('codetree.handlers.os.path.exists')
    @patch('codetree.handlers.urllib2.urlopen')
    def test_gets_file(self, _urlopen, _exists, _unlink):
        destfile = "foo"

        _urlopen.return_value = StringIO("words words")
        hh = HttpFileHandler(HttpURLs[0])

        # New file
        _open = mock_open()
        _exists.return_value = False
        with patch('codetree.handlers.open', _open, create=True):
            self.assertTrue(hh.get(destfile))
        self.assertFalse(_unlink.called)
        _open.assert_called_with(destfile, "w")
        _urlopen.assert_called_with(HttpURLs[0])

    @patch('codetree.handlers.os.unlink')
    @patch('codetree.handlers.os.path.exists')
    @patch('codetree.handlers.urllib2.urlopen')
    def test_gets_file_no_overwrite(self, _urlopen, _exists, _unlink):
        destfile = "foo"

        _urlopen.return_value = StringIO("words words")
        hh = HttpFileHandler(HttpURLs[0])

        # Existing file
        _open = mock_open()
        _exists.return_value = True
        with patch('codetree.handlers.open', _open, create=True):
            self.assertFalse(hh.get(destfile))
        self.assertFalse(_unlink.called)
        self.assertFalse(_open.called)
        self.assertFalse(_urlopen.called)

    @patch('codetree.handlers.os.unlink')
    @patch('codetree.handlers.os.path.exists')
    @patch('codetree.handlers.urllib2.urlopen')
    def test_gets_file_with_overwite(self, _urlopen, _exists, _unlink):
        destfile = "foo"

        _urlopen.return_value = StringIO("words words")
        hh = HttpFileHandler(HttpURLs[0])

        # Overwrite existing file
        _open = mock_open()
        _exists.return_value = True
        with patch('codetree.handlers.open', _open, create=True):
            self.assertTrue(hh.get(destfile, options={"overwrite": True}))
        _unlink.assert_called_with(destfile)
        _open.assert_called_with(destfile, "w")
        _urlopen.assert_called_with(HttpURLs[0])

    @patch('codetree.handlers.os.unlink')
    @patch('codetree.handlers.os.path.exists')
    @patch('codetree.handlers.urllib2.urlopen')
    def test_gets_file_bad_url(self, _urlopen, _exists, _unlink):
        destfile = "foo"

        _urlopen.return_value = StringIO("words words")
        hh = HttpFileHandler(HttpURLs[0])

        # Broken source
        _open = mock_open()
        _exists.return_value = False
        _urlopen.side_effect = URLError('failed')
        with patch('codetree.handlers.open', _open, create=True):
            self.assertFalse(hh.get(destfile))
