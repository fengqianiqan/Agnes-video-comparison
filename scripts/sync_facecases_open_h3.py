#!/usr/bin/env python3
"""Stage and index the facecases originals and Open-H3-Regenerate-2K outputs."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


SITE_DIR = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = Path(
    "/keyan/Video_group/fq/workspace/Sol-Refiner/metadata/facecases_case_manifest.json"
)
ORIGINAL_DIR = Path("/keyan/Video_group/fq/workspace/AgnesProdution/outputs/facecases")
REFINED_DIR = Path(
    "/keyan/Video_group/fq/workspace/Sol-Refiner/outputs/agnes_facecases_open_h3_regenerate_2k"
)
ORIGINAL_STAGE = SITE_DIR / "videos/facecases_open_h3/original"
REFINED_STAGE = SITE_DIR / "videos/facecases_open_h3/open_h3_regenerate_2k"
MANIFEST_OUTPUT = SITE_DIR / "data/facecases_open_h3_regenerate_2k.json"


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


def copy_if_changed(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file():
        source_stat = source.stat()
        destination_stat = destination.stat()
        if (source_stat.st_size, source_stat.st_mtime_ns) == (
            destination_stat.st_size, destination_stat.st_mtime_ns
        ):
            return
    shutil.copy2(source, destination)


def main() -> None:
    source_data = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    cases = source_data["cases"]
    if len(cases) != 42:
        raise SystemExit(f"Expected 42 source cases, found {len(cases)}")

    index = []
    missing = []
    for case in cases:
        number = int(case["case_number"])
        case_id = f"case_{number:02d}"
        variant = case["variant"]
        original = ORIGINAL_DIR / f"{number:02d}_{variant}.mp4"
        refined = REFINED_DIR / f"{number:02d}_{variant}_open_h3_2k.mp4"
        if not original.is_file():
            missing.append(str(original))
        if not refined.is_file():
            missing.append(str(refined))
        if missing:
            continue

        filename = f"{case_id}.mp4"
        staged_original = ORIGINAL_STAGE / filename
        staged_refined = REFINED_STAGE / filename
        copy_if_changed(original, staged_original)
        copy_if_changed(refined, staged_refined)

        original_meta = probe_video(staged_original)
        refined_meta = probe_video(staged_refined)
        original_ratio = original_meta["width"] / original_meta["height"]
        refined_ratio = refined_meta["width"] / refined_meta["height"]
        ratio_difference = abs(original_ratio - refined_ratio) / max(original_ratio, refined_ratio)
        if ratio_difference > 0.03:
            raise SystemExit(
                f"Aspect ratio mismatch for {case_id}: "
                f"{original_meta['width']}x{original_meta['height']} vs "
                f"{refined_meta['width']}x{refined_meta['height']}"
            )
        if abs(original_meta["duration"] - refined_meta["duration"]) > 0.05:
            raise SystemExit(f"Duration mismatch for {case_id}")
        if original_meta["frame_rate"] != refined_meta["frame_rate"]:
            raise SystemExit(f"Frame rate mismatch for {case_id}")

        index.append({
            "id": case_id,
            "type": variant,
            "dimension": case["dimension"],
            "kicker": f"CASE {number:02d} / {variant.upper()}",
            "title": f"Case {number:02d} · {case['dimension']}",
            "width": original_meta["width"],
            "height": original_meta["height"],
            "duration": original_meta["duration"],
            "specText": (
                f"原视频 {original_meta['width']} × {original_meta['height']}"
                f" · Open-H3 {refined_meta['width']} × {refined_meta['height']}"
                f" · {original_meta['duration']:.2f}s"
            ),
            "originalMeta": original_meta,
            "refinedMeta": refined_meta,
            "original": f"videos/facecases_open_h3/original/{filename}",
            "refined": f"videos/facecases_open_h3/open_h3_regenerate_2k/{filename}",
        })

    if missing:
        raise SystemExit("Missing source videos:\n" + "\n".join(missing))
    if len(index) != 42:
        raise SystemExit(f"Prepared {len(index)} pairs; expected 42")

    MANIFEST_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUTPUT.write_text(
        json.dumps({"cases": index}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    total_bytes = sum(
        (ORIGINAL_STAGE / f"{item['id']}.mp4").stat().st_size
        + (REFINED_STAGE / f"{item['id']}.mp4").stat().st_size
        for item in index
    )
    print(f"Prepared {len(index)} matched pairs ({total_bytes / 1024**3:.2f} GiB).")
    print(f"Manifest: {MANIFEST_OUTPUT}")


if __name__ == "__main__":
    main()
