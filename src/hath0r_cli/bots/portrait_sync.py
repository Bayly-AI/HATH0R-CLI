"""Government-first, identity-bound portrait discovery and verified-only publication."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import subprocess
import threading
import time
import warnings
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

import yaml

MAX_BYTES = 20 * 1024 * 1024
USER_AGENT = "Hath0rPortraitSync/1.0 (https://github.com/Bayly-AI/HATH0R-CLI; biography image verification)"


def allowed_url(url: str) -> bool:
    if any(ord(c) < 32 for c in url):
        return False
    p = urlparse(url)
    host = (p.hostname or "").lower()
    return (
        p.scheme == "https"
        and not p.username
        and not p.password
        and p.port in (None, 443)
        and (
            host.endswith(".gov")
            or host
            in ("en.wikipedia.org", "upload.wikimedia.org", "commons.wikimedia.org", "raw.githubusercontent.com")
        )
    )


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed_url(newurl):
            raise ValueError("Redirect outside allowed public sources")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class SourceError(Exception):
    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


def retry_after_seconds(value, default):
    """Parse a Retry-After header (delta-seconds only); bounded to avoid stalling a run."""
    try:
        return min(max(float(value), 1.0), 300.0)
    except (TypeError, ValueError):
        return default


class Fetcher:
    """Per-host paced fetcher.

    Rate limits (429/503) are retried with Retry-After / exponential backoff and slow the
    whole host down. Each success decays the host's throttle score by one; the host circuit
    only opens when that score reaches ``max_throttles``, or immediately on 403 (access denied).
    """

    def __init__(self, interval=0.1, retries=4, backoff=5.0, max_throttles=12, sleep=time.sleep, opener=None):
        self.interval = interval
        self.retries = retries
        self.backoff = backoff
        self.max_throttles = max_throttles
        self.sleep = sleep
        self.opener = opener or (lambda: build_opener(SafeRedirect()))
        self.lock = threading.Lock()
        self.next_request = {}
        self.throttles = Counter()
        self.blocked = {}

    def _pace(self, host):
        with self.lock:
            if host in self.blocked:
                raise SourceError(self.blocked[host], "Host circuit open after access denial or rate limit")
            now = time.monotonic()
            start = max(now, self.next_request.get(host, now))
            base = max(
                self.interval, 1.0 if host == "en.wikipedia.org" else 0.3 if host == "upload.wikimedia.org" else 0
            )
            self.next_request[host] = start + base * (1 + min(self.throttles[host], 8))
        self.sleep(max(0, start - time.monotonic()))

    def get(self, url):
        if not allowed_url(url):
            raise SourceError("unsafe_url", "Source host is not allowed")
        host = urlparse(url).hostname
        for attempt in range(self.retries + 1):
            self._pace(host)
            try:
                with self.opener().open(Request(url, headers={"User-Agent": USER_AGENT}), timeout=15) as r:
                    data = r.read(MAX_BYTES + 1)
                    if len(data) > MAX_BYTES:
                        raise SourceError("oversize", "Response exceeds size bound")
                    with self.lock:
                        self.throttles[host] = max(0, self.throttles[host] - 1)
                    return data, r.geturl(), r.headers.get("Content-Type", "")
            except HTTPError as exc:
                if exc.code == 403:
                    with self.lock:
                        self.blocked[host] = "http_403"
                    raise SourceError("http_403", "HTTP 403") from exc
                if exc.code in (429, 503):
                    wait = retry_after_seconds(
                        exc.headers.get("Retry-After") if exc.headers else None, self.backoff * (2**attempt)
                    )
                    with self.lock:
                        self.throttles[host] += 1
                        if self.throttles[host] >= self.max_throttles:
                            self.blocked[host] = f"http_{exc.code}"
                        # Push every worker on this host back, not only this thread.
                        self.next_request[host] = max(self.next_request.get(host, 0), time.monotonic() + wait)
                    if attempt < self.retries and host not in self.blocked:
                        continue
                raise SourceError(f"http_{exc.code}", f"HTTP {exc.code}") from exc
            except (OSError, TimeoutError, ValueError) as exc:
                if attempt < min(self.retries, 1):
                    self.sleep(self.backoff)
                    continue
                raise SourceError("network_error", type(exc).__name__) from exc
        raise SourceError("network_error", "Retries exhausted")


def verify_image(data):
    from PIL import Image

    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(data)) as im:
            if im.format not in ("JPEG", "PNG", "WEBP", "GIF"):
                raise ValueError("Unsupported image format")
            width, height = im.size
            if min(width, height) < 80 or width * height > 40_000_000:
                raise ValueError("Image dimensions outside portrait limits")
            im.verify()
        with Image.open(io.BytesIO(data)) as im:
            im.load()
    return {"width": width, "height": height, "sha256": hashlib.sha256(data).hexdigest()}


class BiographyImages(HTMLParser):
    def __init__(self, image_alt):
        super().__init__()
        self.image_alt = " ".join(image_alt.lower().split())
        self.images = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "img" and self.image_alt and self.image_alt in " ".join(a.get("alt", "").lower().split()):
            if a.get("src"):
                self.images.append((0 if a.get("fetchpriority") == "high" else 1, a["src"]))


def load_crosswalk(fetcher, urls):
    result = {}
    for url in urls:
        data, _, _ = fetcher.get(url)
        for person in yaml.load(data, Loader=yaml.CSafeLoader):
            ids = person.get("id", {})
            if ids.get("bioguide"):
                result[ids["bioguide"]] = {
                    "wikipedia": ids.get("wikipedia"),
                    "birthday": str(person.get("bio", {}).get("birthday", "")),
                }
    return result


class PortraitSyncBot:
    def __init__(self, cwd=None):
        self.cwd = Path(cwd or Path.cwd())

    @staticmethod
    def psql(config, sql):
        cmd = [
            "docker",
            "exec",
            "-i",
            config["container"],
            "psql",
            "-X",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            config["user"],
            "-d",
            config["database"],
        ]
        return subprocess.run(cmd, input=sql, text=True, capture_output=True, check=True).stdout

    def read_profiles(self, config):
        out = self.psql(
            config,
            """BEGIN READ ONLY;
COPY (SELECT f.id, f.bioguide_id, f.display_name, f.birthday, f.wikipedia_id,
 f.photo_url, f.is_current, COALESCE((SELECT lower(t.chamber) FROM federal_official_terms t
 WHERE t.legislator_id=f.id ORDER BY t.end_date DESC,t.start_date DESC,t.id LIMIT 1),'unclassified') AS branch
 FROM federal_legislators f ORDER BY f.is_current DESC,f.bioguide_id) TO STDOUT WITH CSV HEADER;
ROLLBACK;
""",
        )
        lines = out.splitlines()
        return list(
            csv.DictReader(
                io.StringIO(
                    "\n".join(lines[lines.index(next(ln for ln in lines if ln.startswith("id,bioguide_id,"))) : -1])
                )
            )
        )

    def resolve(self, row, config, crosswalk, fetcher, government_only=False):
        result = {
            "id": row["id"],
            "bioguide_id": row["bioguide_id"],
            "name": row["display_name"],
            "branch": row["branch"],
            "old_photo_url": row["photo_url"],
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "attempts": [],
        }
        key = row["bioguide_id"]
        explicit = config.get("executives", {}).get(key, {})
        link = crosswalk.get(key, {})
        # Reject mismatched crosswalk identities instead of attaching a namesake portrait.
        if row["birthday"] and link.get("birthday") and row["birthday"] != link["birthday"]:
            result.update(status="identity_conflict")
            return result

        def candidate(url, page, source):
            try:
                data, final, mime = fetcher.get(url)
                info = verify_image(data)
                if not mime.lower().startswith("image/"):
                    raise ValueError("Non-image Content-Type")
                result.update(
                    status="verified", photo_url=final, source_page=page, source=source, content_type=mime, **info
                )
                return True
            except SourceError as exc:
                result["attempts"].append({"url": url, "status": exc.status})
            except (ValueError, OSError, SyntaxError) as exc:
                result["attempts"].append({"url": url, "status": "invalid_image", "reason": str(exc)[:160]})
            return False

        if explicit.get("government_page"):
            page = explicit["government_page"]
            try:
                content, final, _ = fetcher.get(page)
                parser = BiographyImages(explicit["image_alt"])
                parser.feed(content.decode("utf-8", errors="replace"))
                for _, url in sorted(parser.images):
                    if candidate(urljoin(final, url), page, "government"):
                        return result
                if not parser.images:
                    result["attempts"].append({"url": page, "status": "no_matched_portrait"})
            except SourceError as exc:
                result["attempts"].append({"url": page, "status": exc.status})
        if re.fullmatch(r"[A-Z][0-9]{6}", key):
            if candidate(
                f"https://bioguide.congress.gov/bioguide/photo/{key[0]}/{key}.jpg",
                f"https://bioguide.congress.gov/search/bio/{key}",
                "government",
            ):
                return result
        if government_only:
            result["status"] = "pending_wikipedia"
            return result
        title = explicit.get("wikipedia") or row.get("wikipedia_id") or link.get("wikipedia")
        if title:
            page = "https://en.wikipedia.org/wiki/" + quote(title.replace(" ", "_"), safe="()_")
            api = "https://en.wikipedia.org/w/api.php?" + urlencode(
                {
                    "action": "query",
                    "format": "json",
                    "prop": "pageimages",
                    "piprop": "original",
                    "redirects": 1,
                    "titles": title,
                }
            )
            try:
                data, _, _ = fetcher.get(api)
                document = json.loads(data)
                pages = document.get("query", {}).get("pages", {}).values()
                images = [p["original"]["source"] for p in pages if p.get("original", {}).get("source")]
                for url in images:
                    if candidate(url, page, "wikipedia"):
                        return result
                result["attempts"].append({"url": page, "status": "no_portrait"})
            except SourceError as exc:
                result["attempts"].append({"url": page, "status": exc.status})
            except (ValueError, KeyError, TypeError):
                result["attempts"].append({"url": page, "status": "invalid_metadata"})
        else:
            result["attempts"].append({"status": "no_identity_crosswalk"})
        blocked = any(
            a["status"] not in ("http_404", "http_410", "no_portrait", "no_matched_portrait")
            for a in result["attempts"]
        )
        result["status"] = "unverified" if blocked else "not_found"
        return result

    def wikipedia_batch(self, rows, results, config, crosswalk, fetcher, report):
        """Query up to 50 identity-linked biographies per request after government mining."""
        pending = []
        for row in rows:
            result = results[row["id"]]
            if result["status"] in ("verified", "identity_conflict"):
                continue
            title = (
                config.get("executives", {}).get(row["bioguide_id"], {}).get("wikipedia")
                or row.get("wikipedia_id")
                or crosswalk.get(row["bioguide_id"], {}).get("wikipedia")
            )
            if not title:
                result["status"] = "unverified"
                result["attempts"].append({"status": "no_identity_crosswalk"})
                report.write(json.dumps(result) + "\n")
                report.flush()
            else:
                pending.append((row, title, result))

        def image_result(item, metadata):
            row, title, result = item
            page_url = "https://en.wikipedia.org/wiki/" + quote(title.replace(" ", "_"), safe="()_")
            image = metadata.get("thumbnail", {}).get("source")
            filename = metadata.get("pageimage", "").lower()
            unsuitable = any(
                token in filename
                for token in (
                    "signature",
                    "coat_of_arms",
                    "flag_of",
                    "map_of",
                    "seal_of",
                    "tomb",
                    "grave",
                    "cemetery",
                    "logo",
                )
            )
            if not image or unsuitable:
                status = "no_portrait" if not image else "non_portrait_asset"
            else:
                try:
                    data, final, mime = fetcher.get(image)
                    info = verify_image(data)
                    if not mime.lower().startswith("image/"):
                        raise ValueError("Non-image Content-Type")
                    result.update(
                        status="verified",
                        source="wikipedia",
                        source_page=page_url,
                        photo_url=final,
                        content_type=mime,
                        **info,
                    )
                    return result
                except SourceError as exc:
                    status = exc.status
                except (ValueError, OSError, SyntaxError):
                    status = "invalid_image"
            result["attempts"].append({"url": page_url, "status": status})
            # A valid biography with no image is conclusive only if government checks were conclusive too.
            result["status"] = (
                "not_found"
                if status == "no_portrait"
                and all(
                    a["status"] in ("http_404", "http_410", "no_portrait", "no_matched_portrait")
                    for a in result["attempts"]
                )
                else "unverified"
            )
            return result

        for offset in range(0, len(pending), 50):
            batch = pending[offset : offset + 50]
            titles = list(dict.fromkeys(title for _, title, _ in batch))
            url = "https://en.wikipedia.org/w/api.php?" + urlencode(
                {
                    "action": "query",
                    "format": "json",
                    "prop": "pageimages",
                    "piprop": "thumbnail|name",
                    "pithumbsize": 600,
                    "redirects": 1,
                    "titles": "|".join(titles),
                }
            )
            try:
                data, _, _ = fetcher.get(url)
                document = json.loads(data)
                if "query" not in document:
                    raise SourceError("invalid_metadata", "No query results")
                query = document["query"]
                names = {x["from"]: x["to"] for x in query.get("normalized", []) + query.get("redirects", [])}
                pages = {x["title"]: x for x in query.get("pages", {}).values()}
                metadata = {}
                for title in titles:
                    canonical = title
                    for _ in range(8):
                        if canonical not in names:
                            break
                        canonical = names[canonical]
                    metadata[title] = pages.get(canonical, {})
                with ThreadPoolExecutor(max_workers=4) as pool:
                    jobs = [pool.submit(image_result, item, metadata[item[1]]) for item in batch]
                    completed = [job.result() for job in jobs]
            except (SourceError, ValueError, KeyError, TypeError) as exc:
                status = exc.status if isinstance(exc, SourceError) else "invalid_metadata"
                completed = []
                for _, title, result in batch:
                    result.update(status="unverified")
                    result["attempts"].append(
                        {"url": "https://en.wikipedia.org/wiki/" + quote(title), "status": status}
                    )
                    completed.append(result)
            for result in completed:
                results[result["id"]] = result
                report.write(json.dumps(result) + "\n")
            report.flush()
            print(
                json.dumps({"wikipedia_processed": min(offset + 50, len(pending)), "wikipedia_total": len(pending)}),
                flush=True,
            )
        return list(results.values())

    def apply(self, config, results):
        verified = [r for r in results if r["status"] == "verified"]
        if not verified:
            return {"verified_candidates": 0, "output": "No verified changes"}
        stream = io.StringIO()
        writer = csv.writer(stream, lineterminator="\n")
        for r in verified:
            writer.writerow([r["id"], r["old_photo_url"], r["photo_url"], json.dumps(r)])
        # CSV payload is passed through stdin, never interpolated into SQL values or a shell.
        sql = (
            """BEGIN;
CREATE TEMP TABLE portrait_updates (id uuid,old_url text,new_url text,provenance jsonb) ON COMMIT DROP;
COPY portrait_updates FROM STDIN WITH (FORMAT csv);
"""
            + stream.getvalue()
            + "\\.\n"
            + """
WITH changed AS (
 UPDATE federal_legislators f SET photo_url=u.new_url, photo_provenance=u.provenance,
 photo_verified_at=(u.provenance->>'checked_at')::timestamptz, updated_at=NOW()
 FROM portrait_updates u WHERE f.id=u.id AND COALESCE(f.photo_url,'')=u.old_url
 RETURNING f.id
) SELECT count(*) AS applied FROM changed;
COMMIT;
"""
        )
        return {"verified_candidates": len(verified), "output": self.psql(config, sql)}

    def sync(self, config="cfg/portraits.yaml", apply=False, resume=False, limit=None, dry_run=False):
        config_path = (self.cwd / config).resolve()
        if not config_path.is_relative_to(self.cwd.resolve()):
            raise ValueError("Config must be inside the working repository")
        cfg = yaml.safe_load(config_path.read_text())
        output = (self.cwd / cfg["output_dir"]).resolve()
        if not output.is_relative_to(self.cwd.resolve()):
            raise ValueError("Output must be inside the working repository")
        if dry_run:
            return {"status": "success", "dry_run": True, "config": str(config_path), "apply": False}
        rows = self.read_profiles(cfg)
        if cfg.get("bioguide_ids"):
            rows = [r for r in rows if r["bioguide_id"] in cfg["bioguide_ids"]]
        if limit:
            rows = rows[:limit]
        output.mkdir(parents=True, exist_ok=True)
        root = output
        if resume:
            pointer = root / "latest-run.txt"
            output = root / pointer.read_text().strip() if pointer.exists() else root
            if not output.resolve().is_relative_to(root):
                raise ValueError("Invalid resume directory")
            if not (output / "portraits.jsonl").exists():
                raise ValueError("No prior checkpoint to resume")
        else:
            output = root / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            output.mkdir()
            (root / "latest-run.txt").write_text(output.name)
        checkpoint = output / "portraits.jsonl"
        previous = (
            list({r["id"]: r for r in (json.loads(line) for line in checkpoint.read_text().splitlines())}.values())
            if checkpoint.exists()
            else []
        )
        known = {r["id"] for r in previous}
        fetcher = Fetcher(float(cfg.get("request_interval", 0.1)))
        crosswalk = load_crosswalk(fetcher, cfg["crosswalk_urls"])
        counts = Counter(r["status"] for r in previous)
        with (
            checkpoint.open("a") as report,
            ThreadPoolExecutor(max_workers=min(8, max(1, int(cfg.get("workers", 4))))) as pool,
        ):
            jobs = [
                pool.submit(self.resolve, row, cfg, crosswalk, fetcher, True) for row in rows if row["id"] not in known
            ]
            for job in as_completed(jobs):
                r = job.result()
                report.write(json.dumps(r) + "\n")
                report.flush()
                previous.append(r)
                counts[r["status"]] += 1
                if len(previous) % 100 == 0:
                    print(
                        json.dumps({"processed": len(previous), "total": len(rows), "counts": dict(counts)}), flush=True
                    )
        with checkpoint.open("a") as report:
            previous = self.wikipedia_batch(rows, {r["id"]: r for r in previous}, cfg, crosswalk, fetcher, report)
        counts = Counter(r["status"] for r in previous)
        summary = {
            "status": "success",
            "profiles": len(rows),
            "counts": dict(counts),
            "blocked_hosts": fetcher.blocked,
            "report": str(checkpoint),
        }
        if apply:
            summary["publication"] = self.apply(cfg, previous)
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        return summary
