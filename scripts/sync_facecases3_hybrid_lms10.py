#!/usr/bin/env python3
"""Prepare the public Base vs Hybrid+lms1.0 facecases3 comparison page."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


DEFAULT_MANIFEST = Path("/keyan/Video_group/fq/workspace/facecases3/case_manifest.json")
DEFAULT_ORIGINAL_DIR = Path("/keyan/Video_group/fq/workspace/AgnesProdution/outputs/facecases3")
DEFAULT_REFINED_DIR = Path(
    "/keyan/Video_group/fq/workspace/Hybrid/outputs/justminimaxh3_hybrid_fp8_lms/start_step_03_scale_1.0"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--original-dir", type=Path, default=DEFAULT_ORIGINAL_DIR)
    parser.add_argument("--refined-dir", type=Path, default=DEFAULT_REFINED_DIR)
    parser.add_argument("--site-dir", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    cases = json.loads(args.manifest.read_text(encoding="utf-8"))["cases"]
    if len(cases) != 29 or [int(case["case_number"]) for case in cases] != list(range(1, 30)):
        raise SystemExit("Expected facecases3 manifest case numbers 1 through 29 in order")

    shared_original_dir = args.site_dir / "videos" / "facecases3" / "original"
    output_refined_dir = args.site_dir / "videos" / "facecases3_hybrid" / "lms_step_03_scale_1.0"
    pairs = []
    missing = []
    changed_base = []
    for case in cases:
        number = int(case["case_number"])
        case_id = f"case_{number:02d}"
        original = args.original_dir / f"{case['case_dir']}.mp4"
        shared_original = shared_original_dir / f"{case_id}.mp4"
        refined = args.refined_dir / f"{case_id}_{case['variant']}_lms_facecases3_s03_w1p0.mp4"
        if not original.is_file():
            missing.append(str(original))
        if not refined.is_file():
            missing.append(str(refined))
        if not shared_original.is_file():
            missing.append(str(shared_original))
        if original.is_file() and shared_original.is_file() and sha256(original) != sha256(shared_original):
            changed_base.append(case_id)
        pairs.append((case, case_id, original, shared_original, refined))

    if missing:
        raise SystemExit("Missing comparison files:\n" + "\n".join(missing))
    if changed_base:
        raise SystemExit(
            "The published Base assets no longer match the requested source for: "
            + ", ".join(changed_base)
            + ". Refresh the existing facecases3 Base assets before preparing this page."
        )

    output_refined_dir.mkdir(parents=True, exist_ok=True)
    index = []
    for case, case_id, original, shared_original, refined in pairs:
        copied_refined = output_refined_dir / f"{case_id}.mp4"
        shutil.copy2(refined, copied_refined)
        original_meta = probe_video(original)
        refined_meta = probe_video(copied_refined)
        case_number = int(case["case_number"])
        dimension = case.get("dimension", case["variant"])
        index.append({
            "id": case_id,
            "type": case["variant"],
            "dimension": dimension,
            "kicker": f"CASE {case_number:02d} / {case['variant'].upper()}",
            "title": f"Case {case_number:02d} · {dimension}",
            "width": original_meta["width"],
            "height": original_meta["height"],
            "duration": original_meta["duration"],
            "specText": (
                f"Base {original_meta['width']} × {original_meta['height']} · {original_meta['duration']:.2f}s"
                f" → Hybrid LMS {refined_meta['width']} × {refined_meta['height']} · {refined_meta['duration']:.2f}s"
            ),
            "originalMeta": original_meta,
            "refinedMeta": refined_meta,
            "original": f"videos/facecases3/original/{case_id}.mp4",
            "refined": f"videos/facecases3_hybrid/lms_step_03_scale_1.0/{case_id}.mp4",
        })

    manifest_path = args.site_dir / "data" / "facecases3_hybrid_lms10.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps({"cases": index}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    total = sum((args.site_dir / item["refined"]).stat().st_size for item in index)
    print(f"Prepared {len(index)} matched pairs; reused Base assets and copied {total / 1024 / 1024:.1f} MiB of Hybrid videos.")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
