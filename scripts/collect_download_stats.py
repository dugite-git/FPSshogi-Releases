#!/usr/bin/env python3
"""Record complete GitHub release download observations using only the stdlib."""

import argparse
import csv
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import urlsplit
import urllib.request


ASSET_NAME = "FPSshogi-Windows.zip"
FETCH_LIVE = object()
JST = timezone(timedelta(hours=9))
SUMMARY_FIELDS = [
    "observed_at_utc", "observed_at_jst", "run_key", "active_downloads",
    "total_downloads", "new_downloads", "release_count", "asset_count",
    "archived_asset_count",
]
ASSET_FIELDS = [
    "observed_at_utc", "asset_id", "release_id", "tag", "name", "download_count", "active",
]


def _repository(value):
    if not isinstance(value, str) or not re.fullmatch(r"[\w.-]+/[\w.-]+", value, re.ASCII):
        raise ValueError("repository must be OWNER/REPO")
    return value


def _integer(value, label, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{label} must be an integer >= {minimum}")
    return value


def _text(value, label, allow_empty=False):
    if not isinstance(value, str) or (not value and not allow_empty):
        raise ValueError(f"{label} must be a string" + ("" if allow_empty else " and not empty"))
    if any(ord(char) < 32 for char in value):
        raise ValueError(f"{label} contains control characters")
    return value


def _timestamp(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("observed_at must be an ISO8601 timestamp with a timezone") from error
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("observed_at must include a timezone")
    return result.astimezone(timezone.utc)


def _utc(value):
    return value.isoformat().replace("+00:00", "Z")


def _current_assets(releases):
    if not isinstance(releases, list):
        raise ValueError("releases response must be an array")
    selected, release_ids, asset_ids = {}, set(), set()
    for release in releases:
        if not isinstance(release, dict):
            raise ValueError("each release must be an object")
        release_id = _integer(release.get("id"), "release id", 1)
        tag = _text(release.get("tag_name"), "tag_name")
        if type(release.get("draft")) is not bool or not isinstance(release.get("assets"), list):
            raise ValueError("each release must have a boolean draft and an assets array")
        if release_id in release_ids:
            raise ValueError(f"duplicate release id {release_id}; response may be incomplete")
        release_ids.add(release_id)
        for asset in release["assets"]:
            if not isinstance(asset, dict):
                raise ValueError("each asset must be an object")
            asset_id = _integer(asset.get("id"), "asset id", 1)
            name = _text(asset.get("name"), "asset name")
            count = _integer(asset.get("download_count"), "download_count")
            if asset_id in asset_ids:
                raise ValueError(f"duplicate asset id {asset_id}")
            asset_ids.add(asset_id)
            if not release["draft"] and name == ASSET_NAME:
                selected[str(asset_id)] = {
                    "release_id": release_id, "tag": tag, "name": name,
                    "download_count": count,
                }
    return selected


def fetch_releases(repository, token=None):
    """Fetch every page, or raise without returning a partial observation."""
    repository = _repository(repository)
    path = f"/repos/{repository}/releases"
    url = f"https://api.github.com{path}?per_page=100"
    headers = {"Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28",
               "User-Agent": "FPSshogi-download-history"}
    token = token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    releases, visited = [], set()
    while url:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.netloc != "api.github.com"
                or parsed.path.casefold() != path.casefold() or url in visited):
            raise ValueError("invalid or cyclic releases pagination URL")
        visited.add(url)
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            page = json.load(response)
            link = response.headers.get("Link", "")
        if not isinstance(page, list):
            raise ValueError("releases API page must be an array")
        releases.extend(page)
        next_urls = []
        for item in link.split(",") if link else []:
            match = re.fullmatch(r'\s*<([^<>]+)>\s*;\s*rel="([^"]+)"\s*', item)
            if not match:
                raise ValueError("malformed API pagination header")
            target, relation = match.groups()
            if "next" in relation.split():
                next_urls.append(target)
        if len(next_urls) > 1:
            raise ValueError("multiple next pages in API pagination header")
        url = next_urls[0] if next_urls else None
    _current_assets(releases)
    return releases


def _read_csv(path, fields):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, strict=True)
        if reader.fieldnames != fields:
            raise ValueError(f"unexpected columns in {path.name}")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError(f"incomplete row in {path.name}")
    return rows


def _csv_integer(value, label, minimum=0):
    if not re.fullmatch(r"0|[1-9][0-9]*", value):
        raise ValueError(f"invalid {label} in saved CSV")
    return _integer(int(value), label, minimum)


def _metrics(assets):
    active = [asset for asset in assets.values() if asset["active"]]
    return {
        "active_downloads": sum(asset["download_count"] for asset in active),
        "total_downloads": sum(asset["download_count"] for asset in assets.values()),
        "release_count": len({asset["release_id"] for asset in active}),
        "asset_count": len(active), "archived_asset_count": len(assets) - len(active),
    }


def _load_existing(data_dir, repository):
    """Rebuild state from the CSVs to detect edits, omissions, and partial saves."""
    paths = [data_dir / name for name in ("history.csv", "assets.csv", "state.json")]
    present = [path.exists() for path in paths]
    if not any(present):
        return [], [], {}
    if not all(present):
        raise ValueError("existing history.csv, assets.csv, and state.json must all be present")
    history = _read_csv(paths[0], SUMMARY_FIELDS)
    details = _read_csv(paths[1], ASSET_FIELDS)
    state = json.loads(paths[2].read_text(encoding="utf-8"))
    if (not isinstance(state, dict) or type(state.get("schema_version")) is not int
            or state["schema_version"] != 1 or not isinstance(state.get("assets"), dict)):
        raise ValueError("invalid saved state schema")
    if _repository(state.get("repository")).casefold() != repository.casefold():
        raise ValueError("saved state belongs to a different repository")
    if not history:
        raise ValueError("existing history has no baseline")
    groups, run_keys, last_time = {}, set(), None
    for row in history:
        moment = _timestamp(row["observed_at_utc"])
        if (_utc(moment) != row["observed_at_utc"] or (last_time and moment <= last_time)
                or row["observed_at_jst"] != moment.astimezone(JST).isoformat()):
            raise ValueError("inconsistent or non-increasing saved observation times")
        run_key = _text(row["run_key"], "run_key", allow_empty=True)
        if run_key and run_key in run_keys:
            raise ValueError("duplicate run_key in saved history")
        run_keys.add(run_key)
        groups[row["observed_at_utc"]] = {}
        last_time = moment
    for row in details:
        group = groups.get(row["observed_at_utc"])
        asset_id = str(_csv_integer(row["asset_id"], "asset_id", 1))
        if group is None or asset_id in group:
            raise ValueError("unknown observation or duplicate asset in assets.csv")
        if row["active"] not in ("true", "false") or row["name"] != ASSET_NAME:
            raise ValueError("invalid active flag or asset name in assets.csv")
        group[asset_id] = {
            "release_id": _csv_integer(row["release_id"], "release_id", 1),
            "tag": _text(row["tag"], "tag"), "name": row["name"],
            "download_count": _csv_integer(row["download_count"], "download_count"),
            "active": row["active"] == "true",
        }
    rebuilt, previous_total = {}, None
    for row in history:
        moment = row["observed_at_utc"]
        group = groups[moment]
        if not group or not rebuilt.keys() <= group.keys():
            raise ValueError("missing assets in saved observation")
        for asset_id, asset in group.items():
            old = rebuilt.get(asset_id)
            if old and (asset["download_count"] < old["download_count"]
                        or asset["release_id"] != old["release_id"]):
                raise ValueError("decreased counter or changed release id in saved history")
            if not asset["active"] and (not old or any(
                    asset[key] != old[key] for key in ("release_id", "tag", "name", "download_count"))):
                raise ValueError("archived asset changed in saved history")
            rebuilt[asset_id] = {
                **asset, "first_seen_at": old["first_seen_at"] if old else moment,
                "last_seen_at": moment if asset["active"] else old["last_seen_at"],
            }
        metrics = _metrics(rebuilt)
        expected = {key: str(value) for key, value in metrics.items()}
        expected["new_downloads"] = ("" if previous_total is None else
                                     str(metrics["total_downloads"] - previous_total))
        if any(row[key] != value for key, value in expected.items()):
            raise ValueError("history summary does not match saved asset observations")
        previous_total = metrics["total_downloads"]
    for asset in state["assets"].values():
        if (not isinstance(asset, dict) or type(asset.get("active")) is not bool
                or type(asset.get("release_id")) is not int
                or type(asset.get("download_count")) is not int):
            raise ValueError("invalid saved asset state")
    if state["assets"] != rebuilt:
        raise ValueError("saved state does not match asset history")
    return history, details, rebuilt


def _csv_text(fields, rows):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _save(data_dir, history, details, repository, assets):
    contents = {
        "history.csv": _csv_text(SUMMARY_FIELDS, history),
        "assets.csv": _csv_text(ASSET_FIELDS, details),
        "state.json": json.dumps({"schema_version": 1, "repository": repository,
                                  "assets": assets}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    }
    data_dir.mkdir(parents=True, exist_ok=True)
    staged = []
    try:
        # Stage every complete file before replacing any existing one.
        for name, content in contents.items():
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="",
                                             dir=data_dir, prefix=".collector-", delete=False) as handle:
                staged.append((Path(handle.name), data_dir / name))
                handle.write(content)
        for temporary, destination in staged:
            os.replace(temporary, destination)
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)


def collect(repository, data_dir, releases=FETCH_LIVE, observed_at=None, run_key=""):
    """Append one validated observation; return False for an already recorded run."""
    repository = _repository(repository)
    run_key = _text(run_key, "run_key", allow_empty=True)
    data_dir = Path(data_dir)
    history, details, previous = _load_existing(data_dir, repository)
    if run_key and any(row["run_key"] == run_key for row in history):
        return False
    if releases is FETCH_LIVE:
        releases = fetch_releases(repository)
    current = _current_assets(releases)
    if not history and not current:
        raise ValueError("initial baseline requires at least one matching public release asset")
    moment = _timestamp(observed_at) if observed_at is not None else datetime.now(timezone.utc)
    if history and moment <= _timestamp(history[-1]["observed_at_utc"]):
        raise ValueError("observation timestamp must be strictly later than the previous observation")
    timestamp = _utc(moment)
    assets = {asset_id: {**asset, "active": False} for asset_id, asset in previous.items()}
    for asset_id, asset in current.items():
        old = previous.get(asset_id)
        if old and asset["download_count"] < old["download_count"]:
            raise ValueError(f"download_count decreased for asset {asset_id}")
        if old and asset["release_id"] != old["release_id"]:
            raise ValueError(f"release id changed for asset {asset_id}")
        assets[asset_id] = {
            **asset, "active": True, "first_seen_at": old["first_seen_at"] if old else timestamp,
            "last_seen_at": timestamp,
        }
    metrics = _metrics(assets)
    history.append({
        "observed_at_utc": timestamp, "observed_at_jst": moment.astimezone(JST).isoformat(),
        "run_key": run_key, **{key: str(value) for key, value in metrics.items()},
        "new_downloads": (str(metrics["total_downloads"] - _metrics(previous)["total_downloads"])
                          if previous else ""),
    })
    for asset_id in sorted(assets, key=int):
        asset = assets[asset_id]
        details.append({
            "observed_at_utc": timestamp, "asset_id": asset_id,
            **{key: asset[key] for key in ("release_id", "tag", "name", "download_count")},
            "active": str(asset["active"]).lower(),
        })
    _save(data_dir, history, details, repository, assets)
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--input-json", type=Path)
    parser.add_argument("--observed-at")
    parser.add_argument("--run-key", default=os.environ.get("GITHUB_RUN_ID", ""))
    args = parser.parse_args(argv)
    try:
        releases = (json.loads(args.input_json.read_text(encoding="utf-8"))
                    if args.input_json else FETCH_LIVE)
        changed = collect(args.repository, args.data_dir, releases,
                          args.observed_at, args.run_key)
    except (ValueError, OSError, csv.Error) as error:
        print(f"download stats: {error}", file=sys.stderr)
        return 1
    print("Recorded download observation." if changed else "Run already recorded; no files changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
