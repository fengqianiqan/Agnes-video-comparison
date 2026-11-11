#!/usr/bin/env python3
"""Stage facecases3 originals and Open-H3 IC outputs for comparison."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


SITE_DIR = Path(__file__).resolve().parents[1]
ORIGINAL_DIR = Path("/keyan/Video_group/fq/workspace/AgnesProdution/outputs/facecases3")
REFINED_DIR = Path("/keyan/Video_group/fq/workspace/Sol-Refiner/outputs/open_h3_ic_facecases3")
ORIGINAL_STAGE = SITE_DIR / "videos/facecases3_open_h3_ic/original"
REFINED_STAGE = SITE_DIR / "videos/facecases3_open_h3_ic/open_h3_ic_2k"
MANIFEST_OUTPUT = SITE_DIR / "data/facecases3_open_h3_ic.json"
OUTPUT_PATTERN = re.compile(r"(?P<order>\d+)_(?P<source>.+)_open_h3_ic_2k\.mp4$")
SOURCE_PATTERN = re.compile(r"(?P<group>facecases2?)_(?P<number>\d+)_(?P<dimension>.+)$")
EXPECTED_PAIRS = 29


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


def collect_outputs() -> list[tuple[int, Path, str]]:
    outputs = []
    for path in REFINED_DIR.glob("*.mp4"):
        match = OUTPUT_PATTERN.fullmatch(path.name)
        if not match:
            raise SystemExit(f"Unexpected Open-H3 IC output name: {path.name}")
        outputs.append((int(match.group("order")), path, match.group("source")))
    outputs.sort(key=lambda item: item[0])
    if len(outputs) != EXPECTED_PAIRS:
        raise SystemExit(f"Expected {EXPECTED_PAIRS} Open-H3 IC videos, found {len(outputs)}")
    return outputs


def validate_pair(original: dict, refined: dict, case_id: str) -> None:
    original_ratio = original["width"] / original["height"]
    refined_ratio = refined["width"] / refined["height"]
    ratio_difference = abs(original_ratio - refined_ratio) / max(original_ratio, refined_ratio)
    if ratio_difference > 0.03:
        raise SystemExit(
            f"Aspect ratio mismatch for {case_id}: "
            f"{original['width']}x{original['height']} vs "
            f"{refined['width']}x{refined['height']}"
        )
    if abs(original["duration"] - refined["duration"]) > 0.05:
        raise SystemExit(f"Duration mismatch for {case_id}")
    if original["frame_rate"] != refined["frame_rate"]:
        raise SystemExit(f"Frame-rate mismatch for {case_id}")


def main() -> None:
    index = []
    used_originals = set()
    for order, refined, source_stem in collect_outputs():
        source_match = SOURCE_PATTERN.fullmatch(source_stem)
        if not source_match:
            raise SystemExit(f"Cannot identify source case in output name: {refined.name}")

        original = ORIGINAL_DIR / f"{source_stem}.mp4"
        if not original.is_file():
            raise SystemExit(f"Missing source video for {refined.name}: {original.name}")
        used_originals.add(original.name)

        case_id = f"case_{order:02d}"
        filename = f"{case_id}.mp4"
        staged_original = ORIGINAL_STAGE / filename
        staged_refined = REFINED_STAGE / filename
        copy_if_changed(original, staged_original)
        copy_if_changed(refined, staged_refined)

        original_meta = probe_video(staged_original)
        refined_meta = probe_video(staged_refined)
        validate_pair(original_meta, refined_meta, case_id)

        group = source_match.group("group")
        source_number = source_match.group("number")
        dimension = source_match.group("dimension")
        group_label = "FACECases2" if group == "facecases2" else "FACECases"
        index.append({
            "id": case_id,
            "type": group,
            "dimension": dimension,
            "kicker": f"SOURCE {group_label} {source_number}",
            "title": f"{group_label} {source_number} · {dimension}",
            "width": original_meta["width"],
            "height": original_meta["height"],
            "duration": original_meta["duration"],
            "specText": (
                f"原视频 {original_meta['width']} × {original_meta['height']}"
                f" · Open-H3 IC {refined_meta['width']} × {refined_meta['height']}"
                f" · {original_meta['duration']:.2f}s"
            ),
            "originalMeta": original_meta,
            "refinedMeta": refined_meta,
            "original": f"videos/facecases3_open_h3_ic/original/{filename}",
            "refined": f"videos/facecases3_open_h3_ic/open_h3_ic_2k/{filename}",
        })

    original_videos = {path.name for path in ORIGINAL_DIR.glob("*.mp4")}
    if used_originals != original_videos:
        missing = sorted(original_videos - used_originals)
        unexpected = sorted(used_originals - original_videos)
        raise SystemExit(f"Original pairing mismatch; unused={missing}, unexpected={unexpected}")

    MANIFEST_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUTPUT.write_text(
        json.dumps({"cases": index}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    total_bytes = sum(
        (ORIGINAL_STAGE / f"case_{order:02d}.mp4").stat().st_size
        + (REFINED_STAGE / f"case_{order:02d}.mp4").stat().st_size
        for order in range(1, len(index) + 1)
    )
    print(f"Prepared {len(index)} matched pairs ({total_bytes / 1024**3:.2f} GiB).")
    print(f"Manifest: {MANIFEST_OUTPUT}")


if __name__ == "__main__":
    main()
