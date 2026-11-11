#!/usr/bin/env python3
"""Stage facecases4 no-LMS baselines and LMS start-step-02 outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path


SITE_DIR = Path(__file__).resolve().parents[1]
ORIGINAL_STAGE = SITE_DIR / "videos/facecases4_lms_step02/no_lms_baseline"
LMS_STAGE = SITE_DIR / "videos/facecases4_lms_step02/lms_start_step_02_scale_1.0"
MANIFEST_OUTPUT = SITE_DIR / "data/facecases4_lms_step02.json"
ORIGINAL_PATTERN = re.compile(r"case(?P<number>\d+)_ref2va_facecases4_no_lms\.mp4$")
LMS_PATTERN = re.compile(r"case_(?P<number>\d+)_ref2va_facecases4_s02_w10\.mp4$")
EXPECTED_CASES = [1, 2, 3, 4, 5, 6, 8, 9, 11]


def files_by_case(directory: Path, pattern: re.Pattern[str]) -> dict[int, Path]:
    matches: dict[int, Path] = {}
    for path in directory.glob("*.mp4"):
        match = pattern.fullmatch(path.name)
        if match:
            number = int(match.group("number"))
            if number in matches:
                raise SystemExit(f"Duplicate video for case {number:02d}")
            matches[number] = path
    return matches


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def copy_unchanged(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and destination.stat().st_size == source.stat().st_size:
        if sha256(destination) == sha256(source):
            return
    shutil.copy2(source, destination)
    if destination.stat().st_size != source.stat().st_size or sha256(destination) != sha256(source):
        raise SystemExit(f"Copied media did not match its source: {destination.name}")


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
        "duration": round(float(metadata["format"]["duration"]), 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-dir", type=Path, required=True, help="no-LMS baseline MP4 directory")
    parser.add_argument("--lms-dir", type=Path, required=True, help="LMS start-step-02 MP4 directory")
    args = parser.parse_args()

    originals = files_by_case(args.original_dir, ORIGINAL_PATTERN)
    lms_outputs = files_by_case(args.lms_dir, LMS_PATTERN)
    expected = set(EXPECTED_CASES)
    if set(originals) != expected or set(lms_outputs) != expected:
        raise SystemExit(
            f"Expected cases {EXPECTED_CASES}; found no-LMS={sorted(originals)}, "
            f"LMS={sorted(lms_outputs)}"
        )

    cases = []
    for number in EXPECTED_CASES:
        case_id = f"case_{number:02d}"
        filename = f"{case_id}.mp4"
        original = ORIGINAL_STAGE / filename
        refined = LMS_STAGE / filename
        copy_unchanged(originals[number], original)
        copy_unchanged(lms_outputs[number], refined)
        original_meta = probe_video(original)
        refined_meta = probe_video(refined)

        if original_meta["frame_rate"] != refined_meta["frame_rate"]:
            raise SystemExit(f"Frame-rate mismatch for {case_id}")
        if abs(float(original_meta["duration"]) - float(refined_meta["duration"])) > 0.05:
            raise SystemExit(f"Duration mismatch for {case_id}")
        frame_rate = float(Fraction(str(original_meta["frame_rate"])))

        cases.append({
            "id": case_id,
            "type": "ref2va",
            "dimension": "no-LMS × LMS 1.0",
            "kicker": f"CASE {number:02d} / REF2VA",
            "title": f"Facecases4 · Case {number:02d}",
            "width": original_meta["width"],
            "height": original_meta["height"],
            "duration": original_meta["duration"],
            "specText": (
                f"no-LMS {original_meta['width']} × {original_meta['height']}"
                f" · LMS {refined_meta['width']} × {refined_meta['height']}"
                f" · {original_meta['duration']:.2f}s · {frame_rate:g} fps"
            ),
            "originalMeta": original_meta,
            "refinedMeta": refined_meta,
            "original": f"videos/facecases4_lms_step02/no_lms_baseline/{filename}",
            "refined": f"videos/facecases4_lms_step02/lms_start_step_02_scale_1.0/{filename}",
        })

    MANIFEST_OUTPUT.write_text(
        json.dumps({"cases": cases}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    total_bytes = sum(
        (ORIGINAL_STAGE / f"case_{number:02d}.mp4").stat().st_size
        + (LMS_STAGE / f"case_{number:02d}.mp4").stat().st_size
        for number in EXPECTED_CASES
    )
    print(f"Prepared {len(cases)} matched pairs ({total_bytes / 1024**2:.1f} MiB), copied unchanged.")
    print(f"Manifest: {MANIFEST_OUTPUT}")


if __name__ == "__main__":
    main()
