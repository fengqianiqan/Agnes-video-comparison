#!/usr/bin/env python3
"""Stage Facecases4 no-LMS and start-step-04 / scale-0.8 LMS pairs."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path


SITE_DIR = Path(__file__).resolve().parents[1]
MANIFEST_PATH = SITE_DIR / "data/facecases4_lms_step02.json"
ORIGINAL_STAGE = SITE_DIR / "videos/facecases4_lms_step04/no_lms_original"
LMS_STAGE = SITE_DIR / "videos/facecases4_lms_step04/lms_start_step_04_scale_0.8"
CASE_NUMBERS = (1, 2, 3, 4, 5, 6, 8, 9, 10, 11)
NO_LMS_TIMES = {
    1: (119.74, 130.17),
    2: (117.39, 119.26),
    3: (391.79, 403.71),
    4: (111.98, 128.14),
    5: (112.61, 128.98),
    6: (202.16, 224.83),
    8: (98.81, 114.90),
    9: (196.43, 198.27),
    10: (371.47, 392.91),
    11: (99.18, 101.30),
}
RUN_SUMMARY = {
    "model": "MiniMax H3 Ref2VA",
    "inferenceSteps": 10,
    "fps": 24,
    "guidanceScale": 1.0,
    "embeddedGuidanceScale": 6.0,
    "flowShift": 12.0,
    "lms": {"enabled": True, "startStep": 4, "scale": 0.8},
    "noLms": {
        "generationSeconds": {"mean": 182.16, "median": 118.56, "min": 98.81, "max": 391.79},
        "endToEndSeconds": {"mean": 194.25, "median": 129.57, "min": 101.30, "max": 403.71},
        "peakProcessMemoryMiBPerDevice": [27906, 27904],
    },
    "lmsRun": {
        "generationSeconds": None,
        "endToEndSeconds": None,
        "peakProcessMemoryMiBPerDevice": [36082, 36082],
    },
    "memoryCapture": "运行期间按进程采样 nvidia-smi used_memory",
    "weights": {
        "totalGb": 111.55,
        "totalGiB": 103.89,
        "breakdownGb": {
            "Qwen3-VL FP8": 66.71,
            "Ref2VA transformer": 33.19,
            "video and audio VAE": 11.02,
            "LMS LoRA": 0.62,
            "Real-ESRGAN": 0.005,
        },
    },
}


def copy_unchanged(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and destination.stat().st_size == source.stat().st_size:
        if sha256(destination) == sha256(source):
            return
    shutil.copy2(source, destination)
    if sha256(destination) != sha256(source):
        raise SystemExit(f"Copied media did not match its source: {destination.name}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe_video(path: Path) -> dict[str, int | float | str]:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,codec_name",
            "-show_entries", "format=duration", "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    metadata = json.loads(result.stdout)
    stream = metadata["streams"][0]
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "frame_rate": stream["r_frame_rate"],
        "duration": round(float(metadata["format"]["duration"]), 3),
        "codec": stream["codec_name"],
    }


def case_file(directory: Path, pattern: str) -> Path:
    matches = list(directory.glob(pattern))
    if len(matches) != 1:
        raise SystemExit(f"Expected one {pattern} in {directory}, found {len(matches)}")
    return matches[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-dir", type=Path, required=True, help="no-LMS baseline MP4 directory")
    parser.add_argument("--lms-dir", type=Path, required=True, help="start-step-04 / scale-0.8 LMS MP4 directory")
    args = parser.parse_args()

    if not MANIFEST_PATH.is_file():
        raise SystemExit(f"Expected the Facecases4 materials manifest: {MANIFEST_PATH}")
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    materials = {item["id"]: item for item in data.get("sourceMaterials", [])}
    expected_materials = {f"case{number:02d}" for number in (1, 2, 3, 4, 5, 6, 8, 9, 10, 11)}
    if set(materials) != expected_materials:
        raise SystemExit("The manifest must contain the 10 retained Facecases4 material entries")

    cases = []
    total_bytes = 0
    for number in CASE_NUMBERS:
        case_id = f"case_{number:02d}"
        filename = f"{case_id}.mp4"
        source_original = case_file(
            args.original_dir,
            f"case{number:02d}_ref2va_facecases4_no_lms.mp4",
        )
        source_lms = case_file(
            args.lms_dir,
            f"case_{number:02d}_ref2va_facecases4_s04_w08.mp4",
        )
        original = ORIGINAL_STAGE / filename
        lms = LMS_STAGE / filename
        copy_unchanged(source_original, original)
        copy_unchanged(source_lms, lms)
        original_meta = probe_video(original)
        lms_meta = probe_video(lms)

        if original_meta["frame_rate"] != lms_meta["frame_rate"]:
            raise SystemExit(f"Frame-rate mismatch for {case_id}")
        if abs(float(original_meta["duration"]) - float(lms_meta["duration"])) > 0.05:
            raise SystemExit(f"Duration mismatch for {case_id}")
        frame_rate = float(Fraction(str(original_meta["frame_rate"])))
        duration = original_meta["duration"]
        original_dims = f"{original_meta['width']} × {original_meta['height']}"
        lms_dims = f"{lms_meta['width']} × {lms_meta['height']}"

        cases.append({
            "id": case_id,
            "type": "ref2va",
            "dimension": "no-LMS × LMS LoRA 0.8",
            "kicker": f"CASE {number:02d} / REF2VA",
            "title": f"Facecases4 · Case {number:02d}",
            "width": original_meta["width"],
            "height": original_meta["height"],
            "duration": duration,
            "specText": f"原视频 {original_dims} · LMS {lms_dims} · {duration:.2f}s · {frame_rate:g} fps",
            "originalMeta": original_meta,
            "refinedMeta": lms_meta,
            "noLmsModelSeconds": NO_LMS_TIMES[number][0],
            "noLmsEndToEndSeconds": NO_LMS_TIMES[number][1],
            "lmsModelSeconds": None,
            "lmsEndToEndSeconds": None,
            "original": f"videos/facecases4_lms_step04/no_lms_original/{filename}",
            "refined": f"videos/facecases4_lms_step04/lms_start_step_04_scale_0.8/{filename}",
        })
        total_bytes += original.stat().st_size + lms.stat().st_size

        material = materials[f"case{number:02d}"]
        material["comparisonCaseId"] = case_id
        material["status"] = "paired"
        material["notRunReasonZh"] = None

    data["cases"] = cases
    data["runSummary"] = RUN_SUMMARY
    MANIFEST_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Prepared {len(cases)} matched pairs ({total_bytes / 1024**2:.1f} MiB); all MP4s copied unchanged.")
    print(f"Manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
