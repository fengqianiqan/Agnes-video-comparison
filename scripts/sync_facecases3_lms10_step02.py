#!/usr/bin/env python3
"""Prepare the facecases3 original vs LMS LoRA 1.0 start-step-02 page."""

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
    "/keyan/Video_group/fq/workspace/AgnesProductionLms/outputs/facecases3_lms_matrix/start_step_02_scale_1.0"
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

    original_assets = args.site_dir / "videos" / "facecases3" / "original"
    refined_assets = args.site_dir / "videos" / "facecases3_lms10" / "start_step_02_scale_1.0"
    pairs = []
    missing = []
    changed_originals = []
    for case in cases:
        number = int(case["case_number"])
        case_id = f"case_{number:02d}"
        original = args.original_dir / f"{case['case_dir']}.mp4"
        shared_original = original_assets / f"{case_id}.mp4"
        refined = args.refined_dir / f"{case_id}_{case['variant']}_lms_facecases3_s02_w1p0.mp4"
        for path in (original, shared_original, refined):
            if not path.is_file():
                missing.append(str(path))
        if original.is_file() and shared_original.is_file() and sha256(original) != sha256(shared_original):
            changed_originals.append(case_id)
        pairs.append((case, case_id, shared_original, refined))

    if missing:
        raise SystemExit("Missing comparison files:\n" + "\n".join(missing))
    if changed_originals:
        raise SystemExit(
            "The site's original clips no longer match the requested source for: "
            + ", ".join(changed_originals)
        )

    refined_assets.mkdir(parents=True, exist_ok=True)
    index = []
    for case, case_id, original, refined in pairs:
        copied_refined = refined_assets / f"{case_id}.mp4"
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
                f"原视频 {original_meta['width']} × {original_meta['height']} · {original_meta['duration']:.2f}s"
                f" → LMS 1.0 {refined_meta['width']} × {refined_meta['height']} · {refined_meta['duration']:.2f}s"
            ),
            "originalMeta": original_meta,
            "refinedMeta": refined_meta,
            "original": f"videos/facecases3/original/{case_id}.mp4",
            "refined": f"videos/facecases3_lms10/start_step_02_scale_1.0/{case_id}.mp4",
        })

    manifest_path = args.site_dir / "data" / "facecases3_lms10_step02.json"
    manifest_path.write_text(
        json.dumps({"cases": index}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    total = sum((refined_assets / f"{item['id']}.mp4").stat().st_size for item in index)
    print(f"Prepared {len(index)} matched pairs; copied {total / 1024 / 1024:.1f} MiB of LMS videos.")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
