import io
import unittest
from unittest.mock import Mock, patch

from PIL import Image

from hath0r_cli.bots.portrait_sync import PortraitSyncBot, SourceError, allowed_url, verify_image


def picture():
    f = io.BytesIO()
    Image.new("RGB", (100, 150), "blue").save(f, format="JPEG")
    return f.getvalue()


class PortraitTests(unittest.TestCase):
    def setUp(self):
        self.row = {
            "id": "id1",
            "bioguide_id": "B000444",
            "display_name": "Joe Biden",
            "birthday": "1942-11-20",
            "wikipedia_id": "Joe Biden",
            "photo_url": "bad",
            "branch": "executive",
        }
        self.bot = PortraitSyncBot()

    def test_reject_html_and_small_images(self):
        with self.assertRaises(OSError):
            verify_image(b"<html>not a picture</html>")
        f = io.BytesIO()
        Image.new("RGB", (1, 1)).save(f, format="PNG")
        with self.assertRaises(ValueError):
            verify_image(f.getvalue())

    def test_image_is_decoded(self):
        self.assertEqual(verify_image(picture())["height"], 150)

    def test_government_precedes_wikipedia(self):
        f = Mock()
        f.get.return_value = (picture(), "https://bioguide.congress.gov/a.jpg", "image/jpeg")
        r = self.bot.resolve(self.row, {}, {}, f)
        self.assertEqual(r["source"], "government")
        self.assertEqual(f.get.call_count, 1)

    def test_missing_government_falls_back(self):
        f = Mock()
        f.get.side_effect = [
            SourceError("http_404", "missing"),
            (
                b'{"query":{"pages":{"1":{"original":{"source":"https://upload.wikimedia.org/a.jpg"}}}}}',
                "https://en.wikipedia.org/w/api.php",
                "application/json",
            ),
            (picture(), "https://upload.wikimedia.org/a.jpg", "image/jpeg"),
        ]
        self.assertEqual(self.bot.resolve(self.row, {}, {}, f)["source"], "wikipedia")

    def test_denied_is_not_missing(self):
        f = Mock()
        f.get.side_effect = SourceError("http_403", "denied")
        self.assertEqual(self.bot.resolve(self.row, {}, {}, f)["status"], "unverified")

    def test_crosswalk_conflict_is_not_published(self):
        f = Mock()
        r = self.bot.resolve(self.row, {}, {"B000444": {"birthday": "1900-01-01"}}, f)
        self.assertEqual(r["status"], "identity_conflict")
        f.get.assert_not_called()

    def test_source_boundary(self):
        for u in [
            "http://senate.gov/a",
            "https://senate.gov.attacker.com/a",
            "https://127.0.0.1/a",
            "https://user@senate.gov/a",
        ]:
            self.assertFalse(allowed_url(u))
        self.assertTrue(allowed_url("https://www.whitehouse.gov/a.jpg"))

    def test_apply_only_verified_and_optimistic(self):
        r = {
            "id": "01234567-0123-0123-0123-012345678901",
            "status": "verified",
            "old_photo_url": "old",
            "photo_url": "https://senate.gov/new",
            "checked_at": "2026-10-10T10:00:00Z",
        }
        with patch.object(self.bot, "psql", return_value="applied 1") as db:
            self.bot.apply({}, [r, {"status": "not_found"}])
            sql = db.call_args.args[1]
        self.assertIn("COALESCE(f.photo_url,'')=u.old_url", sql)
        self.assertIn("photo_provenance=u.provenance", sql)

    def test_no_verified_no_write(self):
        with patch.object(self.bot, "psql") as db:
            self.bot.apply({}, [{"status": "unverified"}])
            db.assert_not_called()


class _Resp:
    def __init__(self, data):
        self.data = data
        self.headers = {"Content-Type": "image/jpeg"}

    def read(self, n):
        return self.data

    def geturl(self):
        return "https://en.wikipedia.org/x"

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _opener(outcomes):
    from urllib.error import HTTPError

    seq = iter(outcomes)

    class _FakeOpener:
        def open(self, req, timeout=None):
            o = next(seq)
            if isinstance(o, int):
                raise HTTPError(req.full_url, o, "err", {"Retry-After": "2"}, None)
            return _Resp(o)

    return lambda: _FakeOpener()


class FetcherTests(unittest.TestCase):
    def test_rate_limit_is_retried_not_circuit_broken(self):
        from hath0r_cli.bots.portrait_sync import Fetcher

        sleeps = []
        f = Fetcher(sleep=sleeps.append, opener=_opener([429, 429, b"ok"]))
        self.assertEqual(f.get("https://en.wikipedia.org/x")[0], b"ok")
        self.assertEqual(f.blocked, {})

    def test_persistent_rate_limit_opens_circuit(self):
        from hath0r_cli.bots.portrait_sync import Fetcher

        f = Fetcher(sleep=lambda s: None, retries=10, max_throttles=3, opener=_opener([429] * 10))
        with self.assertRaises(SourceError) as c:
            f.get("https://en.wikipedia.org/x")
        self.assertEqual(c.exception.status, "http_429")
        self.assertIn("en.wikipedia.org", f.blocked)

    def test_access_denied_blocks_immediately(self):
        from hath0r_cli.bots.portrait_sync import Fetcher

        f = Fetcher(sleep=lambda s: None, opener=_opener([403]))
        with self.assertRaises(SourceError):
            f.get("https://www.senate.gov/x")
        self.assertEqual(f.blocked, {"www.senate.gov": "http_403"})


if __name__ == "__main__":
    unittest.main()
