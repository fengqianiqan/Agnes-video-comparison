#!/usr/bin/env python3
"""Build a reusable paired-video comparison page from a private JSON spec.

The spec may contain absolute source paths. Generated HTML and manifests never
include those paths: media is staged below the ignored videos/ directory.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
from pathlib import Path
from string import Template


SITE_DIR = Path(__file__).resolve().parents[1]
TEMPLATE = SITE_DIR / "scripts/comparison-page.template.html"
SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*$")
ID_RE = re.compile(r"[A-Za-z0-9_-]+$")


def probe_video(path: Path) -> dict[str, int | float | str]:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
            "-show_entries", "format=duration", "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "frame_rate": stream["r_frame_rate"],
        "frames": int(stream["nb_frames"]) if stream.get("nb_frames", "N/A") != "N/A" else -1,
        "duration": round(float(data["format"]["duration"]), 6),
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def copy_if_changed(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and destination.stat().st_size == source.stat().st_size:
        if sha256(destination) == sha256(source):
            return
    shutil.copy2(source, destination)


def validate_pair(left: dict, right: dict, case_id: str) -> None:
    if left["frame_rate"] != right["frame_rate"]:
        raise SystemExit(f"Frame-rate mismatch for {case_id}: {left['frame_rate']} vs {right['frame_rate']}")
    if abs(float(left["duration"]) - float(right["duration"])) > 0.05:
        raise SystemExit(f"Duration mismatch for {case_id}: {left['duration']} vs {right['duration']}")
    if left["frames"] >= 0 and right["frames"] >= 0 and left["frames"] != right["frames"]:
        raise SystemExit(f"Frame-count mismatch for {case_id}: {left['frames']} vs {right['frames']}")
    left_ratio = int(left["width"]) / int(left["height"])
    right_ratio = int(right["width"]) / int(right["height"])
    ratio_delta = abs(left_ratio - right_ratio) / max(left_ratio, right_ratio)
    if ratio_delta > 0.03:
        raise SystemExit(f"Aspect-ratio mismatch over 3% for {case_id}")


def escaped(value: object) -> str:
    return html.escape(str(value), quote=True)


def render_links(links: list[dict]) -> str:
    return "\n".join(
        f'<a href="{escaped(item["url"])}" target="_blank" rel="noopener noreferrer">'
        f'{escaped(item["label"])} ↗</a>'
        for item in links
    )


def render_metrics(metrics: list[dict]) -> str:
    return "\n".join(
        "<div class=\"run-metric\">"
        f'<span class="run-metric-label">{escaped(item["label"])}</span>'
        f'<strong>{escaped(item["value"])}</strong>'
        f'<span>{escaped(item["detail"])}</span>'
        "</div>"
        for item in metrics
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True, help="private JSON build specification")
    parser.add_argument("--site-dir", type=Path, default=SITE_DIR)
    args = parser.parse_args()

    site_dir = args.site_dir.resolve()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    slug = spec["slug"]
    if not SLUG_RE.fullmatch(slug):
        raise SystemExit(f"Invalid slug: {slug}")
    cases_spec = spec.get("cases", [])
    if not cases_spec:
        raise SystemExit("The spec must contain at least one case")

    manifest_cases = []
    for item in cases_spec:
        case_id = item["id"]
        if not ID_RE.fullmatch(case_id):
            raise SystemExit(f"Invalid case id: {case_id}")
        left_source = Path(item["left"]).resolve()
        right_source = Path(item["right"]).resolve()
        if not left_source.is_file() or not right_source.is_file():
            raise SystemExit(f"Missing media for {case_id}")

        left_stage = site_dir / "videos" / slug / "left" / f"{case_id}.mp4"
        right_stage = site_dir / "videos" / slug / "right" / f"{case_id}.mp4"
        copy_if_changed(left_source, left_stage)
        copy_if_changed(right_source, right_stage)
        left_meta = probe_video(left_stage)
        right_meta = probe_video(right_stage)
        validate_pair(left_meta, right_meta, case_id)

        manifest_cases.append({
            "id": case_id,
            "type": item.get("type", "comparison"),
            "dimension": item.get("dimension", case_id),
            "kicker": item.get("kicker", case_id.upper()),
            "title": item.get("title", case_id),
            "width": left_meta["width"],
            "height": left_meta["height"],
            "duration": left_meta["duration"],
            "specText": (
                f'{spec["left_short"]} {left_meta["width"]} × {left_meta["height"]}'
                f' · {spec["right_short"]} {right_meta["width"]} × {right_meta["height"]}'
                f' · {left_meta["duration"]:.2f}s'
            ),
            "originalMeta": left_meta,
            "refinedMeta": right_meta,
            "original": f"videos/{slug}/left/{case_id}.mp4",
            "refined": f"videos/{slug}/right/{case_id}.mp4",
        })

    manifest_name = spec.get("manifest", slug.replace("-", "_") + ".json")
    manifest_path = site_dir / "data" / manifest_name
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps({"cases": manifest_cases}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    page = spec["page"]
    run = page["run_summary"]
    values = {
        "html_title": escaped(page["html_title"]),
        "meta_description": escaped(page["meta_description"]),
        "manifest_url": escaped(f"data/{manifest_name}"),
        "mismatch_message": escaped(page["mismatch_message"]),
        "left_resolution_label": escaped(page["left_resolution_label"]),
        "right_resolution_label": escaped(page["right_resolution_label"]),
        "brand_suffix": escaped(page["brand_suffix"]),
        "eyebrow": escaped(page["eyebrow"]),
        "heading_prefix": escaped(page["heading_prefix"]),
        "heading_accent": escaped(page["heading_accent"]),
        "intro": escaped(page["intro"]),
        "case_count": str(len(manifest_cases)),
        "method_eyebrow": escaped(page.get("method_eyebrow", "SOURCES & DISPLAY")),
        "method_title": escaped(page["method_title"]),
        "left_label": escaped(page["left_label"]),
        "left_description": escaped(page["left_description"]),
        "right_label": escaped(page["right_label"]),
        "right_description": escaped(page["right_description"]),
        "resolution_note": escaped(page["resolution_note"]),
        "links_html": render_links(page.get("links", [])),
        "run_title": escaped(run["title"]),
        "run_badge": escaped(run["badge"]),
        "metrics_html": render_metrics(run["metrics"]),
        "run_parameters": escaped(run["parameters"]),
        "run_footnote": escaped(run["footnote"]),
        "viewer_aria": escaped(page["viewer_aria"]),
        "case_kicker": escaped(manifest_cases[0]["kicker"]),
        "left_overlay": escaped(page["left_overlay"]),
        "right_overlay": escaped(page["right_overlay"]),
        "case_grid_label": escaped(page["case_grid_label"]),
        "footer": escaped(page["footer"]),
    }
    template = Template((site_dir / "scripts/comparison-page.template.html").read_text(encoding="utf-8"))
    html_path = site_dir / f"{slug}.html"
    html_path.write_text(template.substitute(values), encoding="utf-8")

    total_bytes = sum(
        (site_dir / item[field]).stat().st_size
        for item in manifest_cases
        for field in ("original", "refined")
    )
    print(f"Built {html_path.name} with {len(manifest_cases)} pair(s), {total_bytes / 1024**2:.1f} MiB staged")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
