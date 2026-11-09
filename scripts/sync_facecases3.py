#!/usr/bin/env python3
"""Copy and index the facecases3 originals and selected LMS comparison outputs."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


DEFAULT_MANIFEST = Path("/keyan/Video_group/fq/workspace/facecases3/case_manifest.json")
DEFAULT_ORIGINAL_DIR = Path("/keyan/Video_group/fq/workspace/AgnesProdution/outputs/facecases3")
DEFAULT_REFINED_DIR = Path(
    "/keyan/Video_group/fq/workspace/AgnesProductionLms/outputs/facecases3_lms_matrix/start_step_03_scale_0.8"
)


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

    source_manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    cases = source_manifest["cases"]
    pairs = []
    missing = []
    for case in cases:
        case_id = f"case_{int(case['case_number']):02d}"
        original = args.original_dir / f"{case['case_dir']}.mp4"
        refined_name = f"{case_id}_{case['variant']}_lms_facecases3_s03_w0p8.mp4"
        refined = args.refined_dir / refined_name
        if not original.is_file():
            missing.append(str(original))
        if not refined.is_file():
            missing.append(str(refined))
        pairs.append((case, case_id, original, refined))
    if missing:
        raise SystemExit("Missing source videos:\n" + "\n".join(missing))

    output_original = args.site_dir / "videos" / "facecases3" / "original"
    output_refined = args.site_dir / "videos" / "facecases3" / "lms_step_03_scale_0.8"
    output_original.mkdir(parents=True, exist_ok=True)
    output_refined.mkdir(parents=True, exist_ok=True)
    index = []
    for case, case_id, original, refined in pairs:
        output_name = f"{case_id}.mp4"
        copied_original = output_original / output_name
        copied_refined = output_refined / output_name
        shutil.copy2(original, copied_original)
        shutil.copy2(refined, copied_refined)
        original_meta = probe_video(copied_original)
        refined_meta = probe_video(copied_refined)
        dimension = case.get("dimension", case["variant"])
        case_number = int(case["case_number"])
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
                f"原片 {original_meta['width']} × {original_meta['height']} · {original_meta['duration']:.2f}s"
                f" → LMS {refined_meta['width']} × {refined_meta['height']} · {refined_meta['duration']:.2f}s"
            ),
            "originalMeta": original_meta,
            "refinedMeta": refined_meta,
            "original": f"videos/facecases3/original/{output_name}",
            "refined": f"videos/facecases3/lms_step_03_scale_0.8/{output_name}",
        })

    manifest_path = args.site_dir / "data" / "facecases3_lms08.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps({"cases": index}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    total = sum(
        (output_original / f"{item['id']}.mp4").stat().st_size
        + (output_refined / f"{item['id']}.mp4").stat().st_size
        for item in index
    )
    print(f"Prepared {len(index)} matched pairs ({total / 1024 / 1024:.1f} MiB).")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
