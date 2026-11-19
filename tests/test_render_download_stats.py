import csv
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.render_download_stats import daily_rows, render


def observation(utc, jst, total, increment):
    return {
        "observed_at_utc": utc,
        "observed_at_jst": jst,
        "run_key": utc,
        "active_downloads": str(total),
        "total_downloads": str(total),
        "new_downloads": increment,
        "release_count": "2",
        "asset_count": "2",
        "archived_asset_count": "0",
    }


class DailyHistoryTests(unittest.TestCase):
    def test_initial_total_is_not_presented_as_new_downloads(self):
        history = [observation("2026-11-19T14:50:00Z", "2026-11-19T23:50:00+09:00", 121, "")]
        self.assertEqual(daily_rows(history), [{
            "date_jst": "2026-11-19", "new_downloads": None,
            "observations": 1, "baseline_only": True,
        }])

    def test_deltas_are_grouped_by_japan_observation_date(self):
        history = [
            observation("2026-11-19T14:50:00Z", "2026-11-19T23:50:00+09:00", 121, ""),
            observation("2026-11-19T15:20:00Z", "2026-11-20T00:20:00+09:00", 123, "2"),
            observation("2026-11-19T23:17:00Z", "2026-11-20T08:17:00+09:00", 128, "5"),
        ]
        self.assertEqual(daily_rows(history)[1], {
            "date_jst": "2026-11-20", "new_downloads": 7,
            "observations": 2, "baseline_only": False,
        })

    def test_missing_observation_day_remains_unknown(self):
        history = [
            observation("2026-11-18T23:17:00Z", "2026-11-19T08:17:00+09:00", 121, ""),
            observation("2026-11-20T23:17:00Z", "2026-11-21T08:17:00+09:00", 130, "9"),
        ]
        self.assertEqual(daily_rows(history)[1], {
            "date_jst": "2026-11-20", "new_downloads": None,
            "observations": 0, "baseline_only": False,
        })

    def test_report_outputs_csv_and_valid_svg_from_single_baseline(self):
        history = [observation("2026-11-19T08:03:00Z", "2026-11-19T17:03:00+09:00", 121, "")]
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            with (data / "history.csv").open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=list(history[0]))
                writer.writeheader()
                writer.writerows(history)
            (data / "state.json").write_text(json.dumps({
                "schema_version": 1, "repository": "dugite-git/FPSshogi-Releases",
                "assets": {"42": {"release_id": 7, "tag": "v1<&|>",
                    "name": "FPSshogi-Windows.zip", "download_count": 121,
                    "active": True, "first_seen_at": "2026-11-19T08:03:00Z",
                    "last_seen_at": "2026-11-19T08:03:00Z"}},
            }), encoding="utf-8")
            render(data)
            for name in ("cumulative.svg", "daily.svg"):
                self.assertTrue(ET.parse(data / name).getroot().tag.endswith("svg"))
            with (data / "daily.csv").open(encoding="utf-8", newline="") as file:
                self.assertEqual(next(csv.DictReader(file))["new_downloads"], "")
            report = (data / "trends.md").read_text(encoding="utf-8")
            self.assertIn("121", report)
            self.assertIn("v1&lt;&amp;\\|&gt;", report)
            self.assertNotIn("[v1<&|>]", report)


if __name__ == "__main__":
    unittest.main()
