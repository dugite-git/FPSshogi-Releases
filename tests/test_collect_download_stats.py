"""Behavioral checks for complete, append-only release observations."""

import csv
from contextlib import redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/collect_download_stats.py"
REPOSITORY = "dugite-git/FPSshogi-Releases"
FIRST = "2026-11-19T00:17:00Z"
SECOND = "2026-11-19T08:17:00Z"


def asset(asset_id, count, name="FPSshogi-Windows.zip"):
    return {"id": asset_id, "name": name, "download_count": count}


def release(release_id, assets, *, draft=False, tag=None):
    return {"id": release_id, "tag_name": tag or f"v{release_id}",
            "draft": draft, "assets": assets}


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "downloads"

    def invoke(self, releases, *, observed_at=FIRST, run_key="run-1",
               repository=REPOSITORY):
        fixture = self.root / "releases.json"
        fixture.write_text(json.dumps(releases), encoding="utf-8")
        return subprocess.run([
            sys.executable, str(SCRIPT), "--repository", repository,
            "--data-dir", str(self.data), "--input-json", str(fixture),
            "--observed-at", observed_at, "--run-key", run_key,
        ], capture_output=True, text=True)

    def record(self, releases, **kwargs):
        result = self.invoke(releases, **kwargs)
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.rows("history.csv")

    def rows(self, name):
        with (self.data / name).open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def snapshot(self):
        return {path.name: path.read_bytes() for path in self.data.glob("*")}

    def baseline(self):
        return self.record([release(1, [asset(11, 10)]),
                            release(2, [asset(21, 20)])])

    def module(self):
        self.assertTrue(SCRIPT.is_file(), "collector is not implemented")
        spec = importlib.util.spec_from_file_location("collector_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_baseline_is_unknown_delta_and_excludes_drafts_and_other_files(self):
        rows = self.record([
            release(1, [asset(11, 10), asset(12, 300, "source.zip")]),
            release(2, [asset(21, 20)]),
            release(3, [asset(31, 900)], draft=True),
        ])
        self.assertEqual(rows, [{
            "observed_at_utc": FIRST, "observed_at_jst": "2026-11-19T09:17:00+09:00",
            "run_key": "run-1", "active_downloads": "30", "total_downloads": "30",
            "new_downloads": "", "release_count": "2", "asset_count": "2",
            "archived_asset_count": "0",
        }])
        state = json.loads((self.data / "state.json").read_text())
        self.assertEqual(state["schema_version"], 1)
        self.assertEqual(state["repository"], REPOSITORY)
        self.assertEqual(set(state["assets"]), {"11", "21"})
        self.assertEqual(state["assets"]["11"], {
            "release_id": 1, "tag": "v1", "name": "FPSshogi-Windows.zip",
            "download_count": 10, "active": True,
            "first_seen_at": FIRST, "last_seen_at": FIRST,
        })
        self.assertEqual(self.rows("assets.csv")[0], {
            "observed_at_utc": FIRST, "asset_id": "11", "release_id": "1",
            "tag": "v1", "name": "FPSshogi-Windows.zip", "download_count": "10",
            "active": "true",
        })

    def test_later_observation_records_only_the_increment(self):
        self.baseline()
        rows = self.record([release(1, [asset(11, 13)]), release(2, [asset(21, 22)])],
                           observed_at=SECOND, run_key="run-2")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]["total_downloads"], "35")
        self.assertEqual(rows[1]["new_downloads"], "5")
        self.assertEqual(len(self.rows("assets.csv")), 4)

    def test_replacement_keeps_old_id_and_adds_new_id(self):
        self.baseline()
        rows = self.record([release(1, [asset(12, 3)]), release(2, [asset(21, 25)])],
                           observed_at=SECOND, run_key="run-2")
        self.assertEqual(rows[-1]["active_downloads"], "28")
        self.assertEqual(rows[-1]["total_downloads"], "38")
        self.assertEqual(rows[-1]["new_downloads"], "8")
        self.assertEqual(rows[-1]["asset_count"], "2")
        self.assertEqual(rows[-1]["archived_asset_count"], "1")
        state = json.loads((self.data / "state.json").read_text())
        self.assertFalse(state["assets"]["11"]["active"])
        self.assertEqual(state["assets"]["11"]["last_seen_at"], FIRST)
        self.assertEqual(state["assets"]["12"]["first_seen_at"], SECOND)
        self.assertEqual(self.rows("assets.csv")[-3]["active"], "false")

    def test_complete_empty_response_archives_all_without_erasing_totals(self):
        self.baseline()
        row = self.record([], observed_at=SECOND, run_key="run-2")[-1]
        self.assertEqual((row["active_downloads"], row["total_downloads"],
                          row["new_downloads"], row["asset_count"],
                          row["archived_asset_count"], row["release_count"]),
                         ("0", "30", "0", "0", "2", "0"))

    def test_empty_initial_baseline_is_rejected(self):
        for payload in ([], [release(1, [asset(11, 20, "other.zip")])]):
            with self.subTest(payload=payload):
                result = self.invoke(payload)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("initial baseline", result.stderr)
                self.assertEqual(self.snapshot(), {})

    def test_json_null_is_invalid_and_does_not_fall_back_to_a_live_fetch(self):
        collector = self.module()
        self.baseline()
        before = self.snapshot()
        fixture = self.root / "null.json"
        fixture.write_text("null", encoding="utf-8")
        with patch("urllib.request.urlopen", return_value=Response([])), redirect_stderr(io.StringIO()):
            result = collector.main([
                "--repository", REPOSITORY, "--data-dir", str(self.data),
                "--input-json", str(fixture), "--observed-at", SECOND, "--run-key", "run-2",
            ])
        self.assertNotEqual(result, 0)
        self.assertEqual(self.snapshot(), before)

    def test_malformed_api_data_never_changes_persisted_files(self):
        self.baseline()
        before = self.snapshot()
        payloads = [
            {"message": "rate limited"}, [None], [{}],
            [release(1, None)], [release(1, [asset(11, -1)])],
            [release(1, [asset(11, True)])], [release(1, [asset(11, "20")])],
            [release(1, [{"id": 11, "name": "FPSshogi-Windows.zip"}])],
            [release(1, [asset(11, 10), asset(11, 12)])],
            [release(1, [asset(11, 10)]), release(1, [asset(12, 20)])],
            [release(1, [asset(11, 10)], draft="false")],
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                result = self.invoke(payload, observed_at=SECOND, run_key="run-2")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.snapshot(), before)

    def test_counter_decrease_fails_even_for_an_archived_id(self):
        self.baseline()
        self.record([], observed_at=SECOND, run_key="run-2")
        before = self.snapshot()
        result = self.invoke([release(1, [asset(11, 9)])],
                             observed_at="2026-11-19T16:17:00Z", run_key="run-3")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("decreas", result.stderr.lower())
        self.assertEqual(self.snapshot(), before)

    def test_duplicate_run_key_is_a_noop_even_after_another_run(self):
        self.baseline()
        self.record([release(1, [asset(11, 15)])], observed_at=SECOND, run_key="run-2")
        before = self.snapshot()
        result = self.invoke([release(1, [asset(11, 999)])], run_key="run-1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_distinct_run_requires_strictly_increasing_aware_timestamp(self):
        self.baseline()
        before = self.snapshot()
        for timestamp in (FIRST, "2026-11-18T00:00:00Z", "2026-11-20T00:00:00", ""):
            with self.subTest(timestamp=timestamp):
                result = self.invoke([release(1, [asset(11, 20)])],
                                     observed_at=timestamp, run_key="run-2")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.snapshot(), before)

    def test_repository_change_is_rejected(self):
        self.baseline()
        before = self.snapshot()
        result = self.invoke([release(1, [asset(11, 20)])],
                             observed_at=SECOND, run_key="run-2", repository="other/repo")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.snapshot(), before)

    def test_inconsistent_existing_summary_or_detail_is_rejected(self):
        self.baseline()
        pristine = self.snapshot()
        for filename, old, new in (
                ("history.csv", ",30,30,", ",30,31,"),
                ("assets.csv", ",10,true", ",999,true")):
            with self.subTest(filename=filename):
                for name, content in pristine.items():
                    (self.data / name).write_bytes(content)
                path = self.data / filename
                path.write_text(path.read_text().replace(old, new), encoding="utf-8")
                before = self.snapshot()
                result = self.invoke([release(1, [asset(11, 20)])],
                                     observed_at=SECOND, run_key="run-2")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.snapshot(), before)

    def test_incomplete_existing_file_set_is_rejected(self):
        self.baseline()
        (self.data / "assets.csv").unlink()
        before = self.snapshot()
        result = self.invoke([release(1, [asset(11, 20)])],
                             observed_at=SECOND, run_key="run-2")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.snapshot(), before)

    def test_paginated_fetch_records_assets_from_every_page(self):
        collector = self.module()
        first_url = f"https://api.github.com/repos/{REPOSITORY}/releases?per_page=100"
        next_url = first_url + "&page=2"

        def respond(request, timeout):
            self.assertEqual(request.get_header("Authorization"), "Bearer fixture-token")
            if request.full_url == first_url:
                return Response([release(1, [asset(11, 10)])],
                                {"Link": f'<{next_url}>; rel="next", <{next_url}>; rel="last"'})
            if request.full_url == next_url:
                return Response([release(2, [asset(21, 20)])])
            self.fail(f"Unexpected request URL: {request.full_url}")

        with patch("urllib.request.urlopen", side_effect=respond):
            payload = collector.fetch_releases(REPOSITORY, token="fixture-token")
        self.assertEqual(self.record(payload)[0]["total_downloads"], "30")

    def test_failed_later_page_cannot_append_partial_observation(self):
        collector = self.module()
        self.baseline()
        before = self.snapshot()
        next_url = f"https://api.github.com/repos/{REPOSITORY}/releases?per_page=100&page=2"
        responses = [Response([release(1, [asset(11, 15)])],
                              {"Link": f'<{next_url}>; rel="next"'}),
                     HTTPError(next_url, 502, "bad gateway", {}, None)]
        with patch("urllib.request.urlopen", side_effect=responses), redirect_stderr(io.StringIO()):
            result = collector.main(["--repository", REPOSITORY,
                                     "--data-dir", str(self.data),
                                     "--observed-at", SECOND, "--run-key", "run-2"])
        self.assertNotEqual(result, 0)
        self.assertEqual(self.snapshot(), before)

    def test_malformed_or_untrusted_pagination_fails(self):
        collector = self.module()
        for payload, headers in (
                ({"message": "failed"}, {}),
                ([], {"Link": '<https://api.github.com/ignored>; rel="prev", broken; rel="next"'}),
                ([], {"Link": '<https://example.com/steal>; rel="next"'})):
            with self.subTest(payload=payload, headers=headers):
                with patch("urllib.request.urlopen", return_value=Response(payload, headers)):
                    with self.assertRaises(ValueError):
                        collector.fetch_releases(REPOSITORY, token="fixture-token")


class Response(io.BytesIO):
    def __init__(self, payload, headers=None):
        super().__init__(json.dumps(payload).encode())
        self.headers = headers or {}


if __name__ == "__main__":
    unittest.main()
