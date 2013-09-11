import os
from unittest import TestCase
from urlparse import urlparse

from mock import (
    patch,
    MagicMock,
)

from codetree.handlers import (
    log_failure,
    SourceHandler,
    BzrSourceHandler,
    LocalHandler,
)

BzrURLs = (
    "bzr://example.com/foo",
    "lp:debian/apt",
    "bzr+ssh://bazaar.launchpad.net/~foo/bar/trunk",
    "bzr+http://example.com/foo",
    "bzr+https://example.com/foo",
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


def called_with_cmd(mock, cmd):
    for call_args in mock.call_args_list:
        if call_args[0][0] == cmd:
            return True


class TestLogHandlers(TestCase):
    @patch("codetree.handlers.check_output")
    def test_log_failure_success(self, _call):
        cmd = ("echo", "hello world")
        log_failure(cmd, "Saying hello")
        assert(called_with_cmd(_call, cmd))

    def test_log_failure_failure(self):
        # Throws OSError
        cmd = ("/invalid/cmd", "hello world")
        log_failure(cmd, "Saying hello")

        # Throws CalledProcessError
        cmd = ("false",)
        log_failure(cmd, "Failing")


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
        bh.get(dest, options)
        _rmtree.assert_called_with(dest)

        # don't overwrite if not asked
        options = {"overwrite": False}
        bh.get(dest, options)
        _rmtree.assert_not_called()

        # don't overwrite if source = parent
        options = {"overwrite": True}
        bh.is_same_branch = MagicMock(return_value=True)
        bh.get(dest, options)
        _rmtree.assert_not_called()

    @patch("codetree.handlers.check_output")
    @patch("codetree.handlers.os.path.exists", return_value=False)
    def test_branches_new(self, _exists, _call):
        source = BzrURLs[0]
        dest = "foo"
        bh = BzrSourceHandler(source)
        bh.get(dest)
        assert(called_with_cmd(_call, ('bzr', 'branch', source, dest)))

    @patch("codetree.handlers.check_output")
    @patch("codetree.handlers.os.makedirs")
    def test_creates_new_dirs(self, _makedirs, _call):
        source = BzrURLs[0]
        dest = "foo/bar/baz"
        bh = BzrSourceHandler(source)
        bh.get(dest)
        _makedirs.assert_called_with(os.path.dirname(dest))

    @patch("codetree.handlers.check_output")
    @patch("codetree.handlers.os.path.exists", return_value=True)
    def test_updates_existing(self, _exists, _call):
        source = BzrURLs[0]
        dest = "foo"
        bh = BzrSourceHandler(source)
        bh.is_same_branch = MagicMock(return_value=True)
        bh.get(dest)
        assert(called_with_cmd(_call, ('bzr', 'pull', '-d', dest)))

    @patch("codetree.handlers.check_output")
    def test_gets_revno(self, _call):
        source = BzrURLs[0]
        dest = "foo"
        bh = BzrSourceHandler(source)
        bh.is_same_branch = MagicMock()

        revno = "1"
        options = {"revno": "1"}
        bh.get(dest, options)
        assert(called_with_cmd(_call, ('bzr', 'update', dest, '-r', revno)))


class TestLocalHandler(TestCase):
    def test_url_handling(self):
        for local_url in LocalURLs:
            assert(urlparse(local_url).scheme in LocalHandler.schemes)

    @patch("codetree.handlers.fileutils.mkdir")
    def creates_directory(self, _mkdir):
        lh = LocalHandler("@")
        lh.get("foo")
        _mkdir.assert_called_with('foo', overwrite=False)
