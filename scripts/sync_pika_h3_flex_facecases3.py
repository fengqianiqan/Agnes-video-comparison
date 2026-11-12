#!/usr/bin/env python3
"""Stage matched Pika H3 Flex and facecases3 videos for the comparison site."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from collections import Counter
from fractions import Fraction
from pathlib import Path
from statistics import mean, median


SITE_DIR = Path(__file__).resolve().parents[1]
STAGE_DIR = SITE_DIR / "videos/pika_h3_flex_facecases3"
ORIGINAL_STAGE = STAGE_DIR / "original"
PIKA_STAGE = STAGE_DIR / "pika_h3_flex"
MANIFEST_OUTPUT = SITE_DIR / "data/pika_h3_flex_facecases3.json"
OUTPUT_PATTERN = re.compile(r"case_\d+_(?P<source>facecases_\d+_.+)$")
CASE_PATTERN = re.compile(r"facecases_(?P<number>\d+)_(?P<label>.+)$")
TIMING_FIELDS = (
    "assets_seconds",
    "conditioning_seconds",
    "transformer_load_seconds",
    "sampling_seconds",
    "decode_encode_seconds",
)


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


def format_duration(seconds: float) -> str:
    whole_seconds = round(seconds)
    return f"{whole_seconds // 60}:{whole_seconds % 60:02d}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pika-dir", type=Path, required=True, help="Pika output directory")
    parser.add_argument("--original-dir", type=Path, required=True, help="facecases3 MP4 directory")
    parser.add_argument("--status-file", type=Path, required=True, help="Pika inference status JSON")
    args = parser.parse_args()

    originals: dict[str, Path] = {}
    for path in args.original_dir.glob("*.mp4"):
        if path.stem in originals:
            raise SystemExit(f"Duplicate source video for {path.stem}")
        originals[path.stem] = path

    status = json.loads(args.status_file.read_text(encoding="utf-8"))
    state_cases = status.get("cases", {})
    paired_outputs: dict[str, tuple[Path, Path]] = {}
    for output_dir in sorted(args.pika_dir.glob("case_*")):
        match = OUTPUT_PATTERN.fullmatch(output_dir.name)
        output = output_dir / "pika-h3-flex.mp4"
        metadata = output_dir / "pika-h3-flex.json"
        if not match or not output.is_file():
            continue
        source_stem = match.group("source")
        if source_stem not in originals:
            continue
        if source_stem in paired_outputs:
            raise SystemExit(f"Duplicate Pika output for {source_stem}")
        if not metadata.is_file():
            raise SystemExit(f"Missing Pika run metadata for {source_stem}")
        paired_outputs[source_stem] = (output, metadata)

    if not paired_outputs:
        raise SystemExit("No Pika videos matched the facecases3 source filenames")

    cases = []
    runtimes = []
    peaks = []
    tasks: Counter[str] = Counter()
    for source_stem in sorted(paired_outputs):
        case_match = CASE_PATTERN.fullmatch(source_stem)
        if not case_match:
            raise SystemExit(f"Unexpected facecases3 filename: {source_stem}")
        number = int(case_match.group("number"))
        label = case_match.group("label")
        case_id = f"case_{number:02d}"
        output_path, metadata_path = paired_outputs[source_stem]
        run_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        task = run_metadata.get("task")
        if task not in {"ref2va", "t2va"}:
            raise SystemExit(f"Unsupported Pika task for {case_id}: {task}")
        timings = run_metadata.get("timings", {})
        if any(not isinstance(timings.get(field), (int, float)) for field in TIMING_FIELDS):
            runtime_seconds = None
        else:
            runtime_seconds = round(sum(float(timings[field]) for field in TIMING_FIELDS), 3)

        process_state = state_cases.get(source_stem, {})
        peak_memory_mib = process_state.get("peak_process_memory_mib")
        if peak_memory_mib is not None:
            peak_memory_mib = int(peak_memory_mib)

        original_stage = ORIGINAL_STAGE / f"{case_id}.mp4"
        pika_stage = PIKA_STAGE / f"{case_id}.mp4"
        copy_unchanged(originals[source_stem], original_stage)
        copy_unchanged(output_path, pika_stage)
        original_meta = probe_video(original_stage)
        pika_meta = probe_video(pika_stage)
        frame_rate = float(Fraction(str(original_meta["frame_rate"])))

        cases.append({
            "id": case_id,
            "type": task,
            "dimension": f"{task.upper()} · {label}",
            "kicker": f"CASE {number:02d} / {task.upper()}",
            "title": f"Facecases3 · Case {number:02d} · {label}",
            "width": original_meta["width"],
            "height": original_meta["height"],
            "duration": original_meta["duration"],
            "specText": (
                f"原片 {original_meta['width']}×{original_meta['height']}"
                f" / H3 Flex {pika_meta['width']}×{pika_meta['height']}"
                f" · {original_meta['duration']:.2f}s / {pika_meta['duration']:.2f}s"
                f" · {frame_rate:g} fps"
            ),
            "originalMeta": original_meta,
            "refinedMeta": pika_meta,
            "runtimeSeconds": runtime_seconds,
            "peakProcessMemoryMiB": peak_memory_mib,
            "original": f"videos/pika_h3_flex_facecases3/original/{case_id}.mp4",
            "refined": f"videos/pika_h3_flex_facecases3/pika_h3_flex/{case_id}.mp4",
        })
        tasks[task] += 1
        if runtime_seconds is not None:
            runtimes.append(runtime_seconds)
        if peak_memory_mib is not None:
            peaks.append(peak_memory_mib)

    MANIFEST_OUTPUT.write_text(
        json.dumps({"cases": cases}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    total_bytes = sum(
        (ORIGINAL_STAGE / f"{case['id']}.mp4").stat().st_size
        + (PIKA_STAGE / f"{case['id']}.mp4").stat().st_size
        for case in cases
    )
    print(f"Prepared {len(cases)} matched pairs ({total_bytes / 1024**2:.1f} MiB), copied unchanged.")
    print(f"Tasks: {dict(tasks)}")
    if runtimes:
        print(
            "Per-video phase-time sum (mean / median / range): "
            f"{format_duration(mean(runtimes))} / {format_duration(median(runtimes))} / "
            f"{format_duration(min(runtimes))}–{format_duration(max(runtimes))}"
        )
    if peaks:
        print(f"Peak process memory: {max(peaks)} MiB ({max(peaks) / 1024:.2f} GiB)")
    print(f"Manifest: {MANIFEST_OUTPUT.name}")


if __name__ == "__main__":
    main()
