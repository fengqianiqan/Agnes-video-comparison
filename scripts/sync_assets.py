#!/usr/bin/env python3
"""Validate matching Agnes clips, copy them into the static site, and write a manifest."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path


CASE_PATTERN = re.compile(r"^(case_\d{2})_(ref2va|fl2va)(?:_lms_r64_scale10)?\.mp4$")


def probe_video(path: Path) -> dict[str, int | float | str]:
    command = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate",
        "-show_entries", "format=duration", "-of", "json", str(path),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    metadata = json.loads(result.stdout)
    stream = metadata["streams"][0]
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "frame_rate": stream["r_frame_rate"],
        "duration": float(metadata["format"]["duration"]),
    }


def discover(directory: Path, refined: bool) -> dict[str, tuple[Path, str]]:
    found: dict[str, tuple[Path, str]] = {}
    for path in sorted(directory.glob("*.mp4")):
        match = CASE_PATTERN.match(path.name)
        if not match:
            continue
        case_id, case_type = match.groups()
        if refined != ("_lms_r64_scale10" in path.name):
            continue
        if case_id in found:
            raise ValueError(f"Duplicate {case_id} in {directory}")
        found[case_id] = (path, case_type)
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-dir", type=Path, required=True)
    parser.add_argument("--refined-dir", type=Path, required=True)
    parser.add_argument("--site-dir", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    originals = discover(args.original_dir, refined=False)
    refined = discover(args.refined_dir, refined=True)
    if not originals:
        raise SystemExit(f"No matching original videos found in {args.original_dir}")
    if originals.keys() != refined.keys():
        missing_refined = sorted(originals.keys() - refined.keys())
        missing_original = sorted(refined.keys() - originals.keys())
        raise SystemExit(f"Case mismatch; missing refined={missing_refined}, missing original={missing_original}")

    output_original = args.site_dir / "videos" / "original"
    output_refined = args.site_dir / "videos" / "refined"
    output_original.mkdir(parents=True, exist_ok=True)
    output_refined.mkdir(parents=True, exist_ok=True)
    cases = []
    for case_id in sorted(originals):
        original_path, case_type = originals[case_id]
        refined_path, refined_type = refined[case_id]
        if case_type != refined_type:
            raise SystemExit(f"Task type mismatch for {case_id}: {case_type} vs {refined_type}")
        original_meta = probe_video(original_path)
        refined_meta = probe_video(refined_path)
        for key in ("width", "height", "frame_rate"):
            if original_meta[key] != refined_meta[key]:
                raise SystemExit(f"{case_id}: {key} mismatch: {original_meta[key]} vs {refined_meta[key]}")
        if abs(float(original_meta["duration"]) - float(refined_meta["duration"])) > 0.05:
            raise SystemExit(f"{case_id}: duration mismatch: {original_meta['duration']} vs {refined_meta['duration']}")

        output_name = f"{case_id}.mp4"
        shutil.copy2(original_path, output_original / output_name)
        shutil.copy2(refined_path, output_refined / output_name)
        cases.append({
            "id": case_id,
            "type": case_type,
            "width": original_meta["width"],
            "height": original_meta["height"],
            "frameRate": original_meta["frame_rate"],
            "duration": round(float(original_meta["duration"]), 3),
            "original": f"videos/original/{output_name}",
            "refined": f"videos/refined/{output_name}",
        })

    manifest_path = args.site_dir / "data" / "cases.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"cases": cases}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total = sum((output_original / f"{case['id']}.mp4").stat().st_size + (output_refined / f"{case['id']}.mp4").stat().st_size for case in cases)
    print(f"Prepared {len(cases)} matched pairs ({total / 1024 / 1024:.1f} MiB).")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
