#!/usr/bin/env python3
"""Render the recorded observations without inventing unobserved history."""

import argparse
import csv
from datetime import date, datetime, timedelta
from html import escape
import json
import math
from pathlib import Path
from urllib.parse import quote


def daily_rows(history):
    """Assign each measured interval's delta to its ending observation's JST date."""
    days = {}
    for row in history:
        day = row["observed_at_jst"][:10]
        entry = days.setdefault(day, {
            "date_jst": day, "new_downloads": None,
            "observations": 0, "baseline_only": True,
        })
        entry["observations"] += 1
        if row["new_downloads"] != "":
            entry["new_downloads"] = (entry["new_downloads"] or 0) + int(row["new_downloads"])
            entry["baseline_only"] = False
    if not days:
        return []
    current, last = date.fromisoformat(min(days)), date.fromisoformat(max(days))
    result = []
    while current <= last:
        key = current.isoformat()
        result.append(days.get(key, {
            "date_jst": key, "new_downloads": None,
            "observations": 0, "baseline_only": False,
        }))
        current += timedelta(days=1)
    return result


def chart_svg(title, subtitle, labels, values, *, bars=False, times=None):
    width, height = 960, 340
    left, top, right, bottom = 76, 82, 922, 265
    known = [value for value in values if value is not None]
    ymax = max(5, math.ceil(max(known, default=0) * 1.15 / 5) * 5)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(title)}</title>',
        f'<desc id="desc">{escape(subtitle)}。単位：ダウンロード回数。</desc>',
        '<rect width="960" height="340" rx="12" fill="#f8fafc"/>',
        '<g font-family="Noto Sans CJK JP, Noto Sans JP, sans-serif" fill="#172554">',
        f'<text x="28" y="34" font-size="20" font-weight="700">{escape(title)}</text>',
        f'<text x="28" y="59" font-size="12" fill="#475569">{escape(subtitle)}</text>',
    ]
    for tick in range(6):
        value = ymax * tick / 5
        y = bottom - (bottom - top) * tick / 5
        parts.extend([
            f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" stroke="#dbe4ee"/>',
            f'<text x="{left - 12}" y="{y + 4:.2f}" text-anchor="end" font-size="12">{value:,.0f}</text>',
        ])
    parts.append(f'<text x="{left - 12}" y="{top - 12}" text-anchor="end" font-size="12">回</text>')
    count = len(labels)
    if not count:
        parts.append('<text x="480" y="176" text-anchor="middle" font-size="16">記録がありません</text>')
    else:
        if bars:
            step = (right - left) / count
            xs = [left + step * (index + 0.5) for index in range(count)]
        elif times and count > 1 and times[-1] > times[0]:
            xs = [left + (right - left) * (time - times[0]) / (times[-1] - times[0]) for time in times]
        else:
            xs = [(left + right) / 2] if count == 1 else [left + (right - left) * index / (count - 1) for index in range(count)]
        points = []
        for index, value in enumerate(values):
            x = xs[index]
            if value is None:
                if bars:
                    parts.append(f'<text x="{x:.2f}" y="{bottom - 5}" text-anchor="middle" font-size="12" fill="#64748b">—</text>')
                continue
            y = bottom - (bottom - top) * value / ymax
            if bars:
                bar_width = max(1, min(50, step * 0.72))
                parts.append(f'<rect x="{x - bar_width / 2:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{max(1, bottom - y):.2f}" rx="2" fill="#0f766e"><title>{escape(labels[index])}: {value:,}回</title></rect>')
                if count <= 16:
                    parts.append(f'<text x="{x:.2f}" y="{y - 8:.2f}" text-anchor="middle" font-size="12">{value:,}</text>')
            else:
                points.append((x, y, value, labels[index]))
        if not bars and points:
            if len(points) > 1:
                coordinates = " ".join(f"{x:.2f},{y:.2f}" for x, y, _, _ in points)
                parts.append(f'<polyline points="{coordinates}" fill="none" stroke="#2563eb" stroke-width="2.5"/>')
            for x, y, value, label in points:
                parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{4 if count < 50 else 2}" fill="#2563eb"><title>{escape(label)}: {value:,}回</title></circle>')
            x, y, value, _ = points[-1]
            anchor = "end" if x > 870 else "middle"
            parts.append(f'<text x="{x:.2f}" y="{y - 12:.2f}" text-anchor="{anchor}" font-size="14" font-weight="700">{value:,}</text>')
        tick_indices = sorted({round(index * (count - 1) / min(count - 1, 5)) for index in range(min(count, 6))}) if count > 1 else [0]
        for index in tick_indices:
            anchor = "start" if xs[index] <= left + 20 else "end" if xs[index] >= right - 20 else "middle"
            parts.append(f'<text x="{xs[index]:.2f}" y="{bottom + 24}" text-anchor="{anchor}" font-size="11">{escape(labels[index])}</text>')
    footer = "確認日（日本時間）／ —：未計測" if bars else "観測日時（日本時間）"
    parts.append(f'<text x="28" y="322" font-size="12" fill="#475569">{escape(footer)}</text>')
    parts.append("</g></svg>\n")
    return "\n".join(parts)


def md(value):
    return escape(str(value)).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def render(data_dir):
    data_dir = Path(data_dir)
    with (data_dir / "history.csv").open(encoding="utf-8", newline="") as file:
        history = list(csv.DictReader(file))
    if not history:
        raise ValueError("history.csv has no observations")
    state = json.loads((data_dir / "state.json").read_text(encoding="utf-8"))
    daily = daily_rows(history)
    with (data_dir / "daily.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["date_jst", "new_downloads", "observations", "baseline_only"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(daily)

    last = history[-1]
    labels = [datetime.fromisoformat(row["observed_at_jst"]).strftime("%m/%d %H:%M") for row in history]
    times = [datetime.fromisoformat(row["observed_at_utc"].replace("Z", "+00:00")).timestamp() for row in history]
    cumulative = chart_svg(
        "累計ダウンロード数", f"Windows版・記録済み累計／観測 {len(history):,}回",
        labels, [int(row["total_downloads"]) for row in history], times=times,
    )
    recent_days = daily[-90:]
    daily_chart = chart_svg(
        "確認日別の増加数", "直近90日・確認日基準",
        [row["date_jst"][5:].replace("-", "/") for row in recent_days],
        [row["new_downloads"] for row in recent_days], bars=True,
    )
    (data_dir / "cumulative.svg").write_text(cumulative, encoding="utf-8")
    (data_dir / "daily.svg").write_text(daily_chart, encoding="utf-8")
    delta = f"{int(last['new_downloads']):,}回" if last["new_downloads"] != "" else "—"
    repo_url = "https://github.com/" + state["repository"]
    updated = datetime.fromisoformat(last["observed_at_jst"]).strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# FPS将棋 ダウンロード統計", "",
        f"最終更新：{updated}（日本時間）", "",
        "| 指標 | 数値 |", "| --- | ---: |",
        f"| 記録済み累計 | **{int(last['total_downloads']):,}回** |",
        f"| 公開中ファイルの累計 | {int(last['active_downloads']):,}回 |",
        f"| 前回からの増加 | {delta} |",
        f"| 対象リリース数 | {last['release_count']}件 |", "",
        "## グラフ", "",
        "![累計ダウンロード数](cumulative.svg)", "", "![確認日別の増加数](daily.svg)", "",
        "## 最近の推移", "", "| 日時（日本時間） | 累計 | 増加 |", "| --- | ---: | ---: |",
    ]
    for row in reversed(history[-15:]):
        stamp = datetime.fromisoformat(row["observed_at_jst"]).strftime("%Y-%m-%d %H:%M:%S")
        increment = f"{int(row['new_downloads']):,}" if row["new_downloads"] != "" else "—"
        lines.append(f"| {stamp} | {int(row['total_downloads']):,} | {increment} |")
    lines.extend(["", "## バージョン別", "", "| バージョン | ダウンロード数 | 状態 |", "| --- | ---: | --- |"])
    for asset in sorted(state["assets"].values(), key=lambda item: (int(item["release_id"]), item["tag"]), reverse=True):
        link = repo_url + "/releases/tag/" + quote(asset["tag"], safe="")
        status = "公開中" if asset["active"] else "非公開"
        lines.append(f"| [{md(asset['tag'])}]({link}) | {int(asset['download_count']):,} | {status} |")
    lines.append("")
    (data_dir / "trends.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("stats/downloads"))
    args = parser.parse_args()
    render(args.data_dir)


if __name__ == "__main__":
    main()
