#!/usr/bin/env python3
"""Stage the valid Facecases R2VA pairs and their exact reference assets."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any


SITE_DIR = Path(__file__).resolve().parents[1]
BASELINE_DIR = Path("/keyan/Video_group/fq/workspace/AgnesProdution/outputs/facecases")
HYBRID_DIR = Path(
    "/keyan/Video_group/fq/workspace/Hybrid/outputs/facecases_lms_matrix/"
    "start_step_04_scale_0.8"
)
INPUT_DIR = Path("/keyan/Video_group/fq/workspace/facecases")
INPUT_MANIFEST = Path(
    "/keyan/Video_group/fq/workspace/Hybrid/inputs/facecases_lms_matrix/case_manifest.json"
)
BASELINE_STATE = Path(
    "/keyan/Video_group/fq/workspace/AgnesProdution/runtime/facecases_state.json"
)
HYBRID_STATE_DIR = Path(
    "/keyan/Video_group/fq/workspace/Hybrid/state/facecases_lms_matrix/"
    "start_step_04_scale_0.8"
)
HYBRID_CONTROLLER = HYBRID_STATE_DIR / "controller_state.json"
HYBRID_INFERENCE = HYBRID_STATE_DIR / "inference_state.json"

SLUG = "facecases_hybrid_lms_s04_w0p8"
MANIFEST_PATH = SITE_DIR / "data" / f"{SLUG}.json"
PROMPT_TRANSLATIONS_PATH = SITE_DIR / "data" / f"{SLUG}_prompt_zh.json"
VIDEO_STAGE = SITE_DIR / "videos" / SLUG
MATERIAL_STAGE = SITE_DIR / "videos" / f"{SLUG}_inputs"

ORIGINAL_PATTERN = re.compile(r"^case_(?P<number>\d+)_ref2va\.mp4$", re.IGNORECASE)
HYBRID_PATTERN = re.compile(
    r"^case_(?P<number>\d+)_(?P<kind>t2va|fl2va|ref2va)_"
    r"lms_facecases_s04_w0p8(?:-(?P<suffix>good|bad))?\.mp4$",
    re.IGNORECASE,
)

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def copy_unchanged(source: Path, destination: Path) -> None:
    if not source.is_file() or source.stat().st_size == 0:
        raise FileNotFoundError(f"Missing or empty source asset: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    if source.stat().st_size != destination.stat().st_size or sha256(source) != sha256(destination):
        raise RuntimeError(f"Copy verification failed: {source.name}")


def probe_video(path: Path) -> dict[str, int | float | str | bool]:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    video = next(stream for stream in payload["streams"] if stream.get("codec_type") == "video")
    audio_present = any(stream.get("codec_type") == "audio" for stream in payload["streams"])
    return {
        "width": int(video["width"]),
        "height": int(video["height"]),
        "frame_rate": str(video.get("r_frame_rate", "0/1")),
        "duration": round(float(payload["format"]["duration"]), 3),
        "codec": str(video.get("codec_name", "unknown")),
        "hasAudio": audio_present,
    }


def probe_audio_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return round(float(result.stdout.strip()), 3)


def format_rate(rate: str) -> str:
    try:
        return f"{float(Fraction(rate)):.2f} fps"
    except (ValueError, ZeroDivisionError):
        return "帧率未记录"


def safe_input_path(relative_path: str) -> Path:
    root = INPUT_DIR.resolve()
    candidate = (root / relative_path).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError(f"Input reference escapes its source directory: {relative_path}")
    if not candidate.is_file():
        raise FileNotFoundError(f"Missing input material: {relative_path}")
    return candidate


def file_bytes(path: Path) -> int:
    resolved = path.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Model component not found: {path}")
    if resolved.is_file():
        return resolved.stat().st_size

    seen: set[tuple[int, int]] = set()
    total = 0
    for directory, _, filenames in os.walk(resolved):
        for filename in filenames:
            item = Path(directory) / filename
            if item.suffix.lower() not in {".safetensors", ".bin", ".pt", ".pth", ".ckpt"}:
                continue
            try:
                stat = item.stat()
            except OSError:
                continue
            inode = (stat.st_dev, stat.st_ino)
            if inode not in seen:
                seen.add(inode)
                total += stat.st_size
    return total


def summarize(values: list[float]) -> dict[str, float]:
    return {
        "mean": round(statistics.mean(values), 2),
        "median": round(statistics.median(values), 2),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
    }


def selected_r2va_peaks() -> list[int]:
    peaks_by_device: dict[str, int] = defaultdict(int)
    for path in HYBRID_STATE_DIR.glob("gpu_peak_ref2va_attempt_*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for record in payload.get("peak_process_memory", []):
            device = str(record["gpu_uuid"])
            peaks_by_device[device] = max(
                peaks_by_device[device], int(record["used_memory_mib"])
            )
    if not peaks_by_device:
        raise RuntimeError("No R2VA process-level GPU memory samples were recorded")
    return sorted(peaks_by_device.values(), reverse=True)[:2]


def model_weight_summary() -> dict[str, Any]:
    model_root = Path("/keyan/Video_group/model/MiniMax-H3/Ref2VA")
    components = {
        "agnesTransformerBytes": file_bytes(
            Path("/keyan/Video_group/production/Agnes-video-2.5-1015/model/REF2VA")
        ),
        "hybridTransformerBytes": file_bytes(
            Path("/keyan/zq/Models/MinimaxH3/fused_models/Hybrid-FP8-nosubtitle-FP8")
        ),
        "textEncoderBytes": file_bytes(model_root / "text_encoder"),
        "videoVaeBytes": file_bytes(model_root / "video_vae"),
        "audioVaeBytes": file_bytes(model_root / "audio_vae"),
        "loraBytes": file_bytes(
            Path(
                "/keyan/Video_group/fq/workspace/AgnesProductionLms/model_links/"
                "minimax_h3_lms_v1.0_r64_sglang.safetensors"
            )
        ),
    }
    agnes_total = sum(
        components[key]
        for key in (
            "agnesTransformerBytes", "textEncoderBytes", "videoVaeBytes", "audioVaeBytes"
        )
    )
    hybrid_total = sum(
        components[key]
        for key in (
            "hybridTransformerBytes", "textEncoderBytes", "videoVaeBytes",
            "audioVaeBytes", "loraBytes",
        )
    )
    return {
        "componentsBytes": components,
        "agnesTotalBytes": agnes_total,
        "hybridTotalBytes": hybrid_total,
        "unit": "decimal bytes on disk; total includes transformer, text encoder, video/audio VAE, and LMS LoRA where loaded",
    }


def main() -> None:
    prompt_translations = json.loads(PROMPT_TRANSLATIONS_PATH.read_text(encoding="utf-8"))
    original_files: dict[int, Path] = {}
    for path in BASELINE_DIR.glob("*.mp4"):
        match = ORIGINAL_PATTERN.fullmatch(path.name)
        if match:
            number = int(match.group("number"))
            if number in original_files:
                raise RuntimeError(f"Duplicate original for case {number:02d}")
            original_files[number] = path

    candidates: dict[int, list[dict[str, Any]]] = defaultdict(list)
    output_counts: Counter[str] = Counter()
    suffix_counts: Counter[str] = Counter()
    for path in HYBRID_DIR.glob("*.mp4"):
        match = HYBRID_PATTERN.fullmatch(path.name)
        if not match:
            continue
        kind = match.group("kind").lower()
        suffix = (match.group("suffix") or "standard").lower()
        number = int(match.group("number"))
        output_counts[kind] += 1
        suffix_counts[suffix] += 1
        candidates[number].append({"path": path, "kind": kind, "suffix": suffix})

    inputs = json.loads(INPUT_MANIFEST.read_text(encoding="utf-8"))
    input_cases = {int(case["case_number"]): case for case in inputs["cases"]}
    baseline_state = json.loads(BASELINE_STATE.read_text(encoding="utf-8"))["cases"]
    hybrid_state = json.loads(HYBRID_INFERENCE.read_text(encoding="utf-8"))["cases"]
    controller = json.loads(HYBRID_CONTROLLER.read_text(encoding="utf-8"))
    if controller.get("status") != "complete" or controller.get("lora_start_step") != 4:
        raise RuntimeError("The requested Hybrid LMS run is not complete or has unexpected settings")
    if abs(float(controller.get("lora_scale", -1)) - 0.8) > 1e-9:
        raise RuntimeError("The requested Hybrid LMS scale does not match 0.8")

    selected: list[tuple[int, Path, dict[str, Any]]] = []
    for number, versions in candidates.items():
        eligible = [item for item in versions if item["suffix"] != "bad"]
        if number not in original_files or not eligible:
            continue
        eligible.sort(key=lambda item: (item["suffix"] != "good", item["path"].name))
        chosen = eligible[0]
        if chosen["kind"] != "ref2va":
            continue
        selected.append((number, original_files[number], chosen))

    # Put the preferred eligible variant first, then keep case-number order.
    selected.sort(key=lambda item: (item[2]["suffix"] != "good", item[0]))
    if not selected:
        raise RuntimeError("No valid same-case video pairs were found")

    shutil.rmtree(VIDEO_STAGE, ignore_errors=True)
    shutil.rmtree(MATERIAL_STAGE, ignore_errors=True)
    cases: list[dict[str, Any]] = []
    source_materials: list[dict[str, Any]] = []
    baseline_generation: list[float] = []
    baseline_end_to_end: list[float] = []
    hybrid_generation: list[float] = []
    material_image_count = 0
    material_audio_count = 0

    for number, original_source, chosen in selected:
        case_id = f"case_{number:02d}"
        case = input_cases.get(number)
        if case is None:
            raise RuntimeError(f"Input manifest is missing case {number:02d}")
        request = case.get("request", {})
        if request.get("videos"):
            raise RuntimeError(f"Case {number:02d} includes an unhandled source-video input")
        request_kind = chosen["kind"].lower()
        if case.get("variant", "").lower() != request_kind:
            raise RuntimeError(f"Request type mismatch for case {number:02d}")

        prompt_path = safe_input_path(str(case["prompt_path"]))
        if not prompt_path.read_text(encoding="utf-8").strip():
            raise RuntimeError(f"Prompt file is empty for case {number:02d}")

        original_stage = VIDEO_STAGE / "agnes_original" / f"{case_id}.mp4"
        hybrid_stage = VIDEO_STAGE / "hybrid_lms" / f"{case_id}.mp4"
        copy_unchanged(original_source, original_stage)
        copy_unchanged(chosen["path"], hybrid_stage)
        original_meta = probe_video(original_stage)
        hybrid_meta = probe_video(hybrid_stage)
        spec_text = (
            f"Agnes {original_meta['width']} × {original_meta['height']} · "
            f"Hybrid {hybrid_meta['width']} × {hybrid_meta['height']} · "
            f"{original_meta['duration']:.2f}s / {hybrid_meta['duration']:.2f}s · "
            f"{format_rate(str(original_meta['frame_rate']))}"
        )

        baseline = baseline_state.get(str(number), {})
        hybrid = hybrid_state.get(str(number), {})
        if baseline.get("status") != "success" or hybrid.get("status") != "success":
            raise RuntimeError(f"Run state is incomplete for case {number:02d}")
        if int(baseline.get("bytes", -1)) != original_source.stat().st_size:
            raise RuntimeError(f"Agnes run-state file size does not match case {number:02d}")
        if int(hybrid.get("bytes", -1)) != chosen["path"].stat().st_size:
            raise RuntimeError(f"Hybrid run-state file size does not match case {number:02d}")

        baseline_seconds = float(baseline["elapsed_seconds"])
        baseline_total = float(baseline.get("total_elapsed_seconds", baseline_seconds))
        hybrid_seconds = float(hybrid["elapsed_seconds"])
        baseline_generation.append(baseline_seconds)
        baseline_end_to_end.append(baseline_total)
        hybrid_generation.append(hybrid_seconds)

        dimension = str(case.get("dimension") or "Facecases 视频质量案例")
        cases.append({
            "id": case_id,
            "type": request_kind,
            "dimension": "R2VA",
            "kicker": f"CASE {number:02d} / R2VA",
            "title": f"Facecases · Case {number:02d}",
            "width": original_meta["width"],
            "height": original_meta["height"],
            "duration": original_meta["duration"],
            "specText": spec_text,
            "originalMeta": original_meta,
            "refinedMeta": hybrid_meta,
            "category": dimension,
            "agnesGenerationSeconds": round(baseline_seconds, 2),
            "agnesEndToEndSeconds": round(baseline_total, 2),
            "hybridGenerationSeconds": round(hybrid_seconds, 2),
            "original": f"videos/{SLUG}/agnes_original/{case_id}.mp4",
            "refined": f"videos/{SLUG}/hybrid_lms/{case_id}.mp4",
        })

        material_id = f"case{number:02d}"
        material_dir = MATERIAL_STAGE / case_id
        references = []
        for index, relative_path in enumerate(request.get("images", []), start=1):
            source = safe_input_path(str(relative_path))
            suffix = source.suffix.lower()
            filename = f"reference_{index:02d}{suffix}"
            staged = material_dir / filename
            copy_unchanged(source, staged)
            references.append({
                "label": f"参考图 {index:02d}",
                "src": f"videos/{SLUG}_inputs/{case_id}/{filename}",
            })
            material_image_count += 1

        audios = []
        for index, relative_path in enumerate(request.get("audios", []), start=1):
            source = safe_input_path(str(relative_path))
            suffix = source.suffix.lower()
            filename = f"audio_{index:02d}{suffix}"
            staged = material_dir / filename
            copy_unchanged(source, staged)
            audios.append({
                "label": f"音频参考 {index:02d}",
                "duration": probe_audio_duration(staged),
                "src": f"videos/{SLUG}_inputs/{case_id}/{filename}",
            })
            material_audio_count += 1

        source_materials.append({
            "id": material_id,
            "comparisonCaseId": case_id,
            "status": "paired",
            "requestType": "R2VA" if request_kind == "ref2va" else request_kind.upper(),
            "category": dimension,
            "sceneScale": case.get("scene_scale"),
            "references": references,
            "audios": audios,
        })

    missing_translations = [
        item["id"] for item in source_materials if item["id"] not in prompt_translations
    ]
    if missing_translations:
        raise RuntimeError(
            "Full Chinese prompt translations are missing for: "
            + ", ".join(missing_translations)
        )

    weight_sizes = model_weight_summary()
    gpu_peaks = selected_r2va_peaks()
    output_number_types = Counter(
        str(item["kind"]).upper() for values in candidates.values() for item in values
    )
    bad_pairable = sum(
        1
        for number, versions in candidates.items()
        if number in original_files and all(item["suffix"] == "bad" for item in versions)
    )
    unpaired_types = Counter(
        str(item["kind"]).upper()
        for number, versions in candidates.items()
        if number not in original_files
        for item in versions
    )

    manifest = {
        "cases": cases,
        "sourceMaterials": source_materials,
        "runSummary": {
            "pairedCaseCount": len(cases),
            "excludedBadPairCount": bad_pairable,
            "availableOutputTypeCounts": {
                key: output_number_types.get(key, 0) for key in ("T2VA", "FL2VA", "REF2VA")
            },
            "unpairedOutputTypeCounts": dict(unpaired_types),
            "requestTypeCounts": dict(Counter(
                "R2VA" if item["type"].upper() == "REF2VA" else item["type"].upper()
                for item in cases
            )),
            "inputImageCount": material_image_count,
            "inputAudioCount": material_audio_count,
            "agnes": {
                "model": "Agnes Production · MiniMax H3 Ref2VA",
                "generationSeconds": summarize(baseline_generation),
                "endToEndSeconds": summarize(baseline_end_to_end),
                "peakProcessMemoryMiBPerDevice": None,
                "peakMemoryLabel": "未记录",
                "weightBytes": weight_sizes["agnesTotalBytes"],
            },
            "hybrid": {
                "model": "Hybrid FP8 · MiniMax H3 Ref2VA",
                "lora": {"startStep": 4, "scale": 0.8},
                "generationSeconds": summarize(hybrid_generation),
                "endToEndSeconds": None,
                "peakProcessMemoryMiBPerDevice": gpu_peaks,
                "peakMemorySampling": "nvidia-smi 按进程 PID 查询 used_memory，每 2 秒采样",
                "weightBytes": weight_sizes["hybridTotalBytes"],
            },
            "settings": {
                "inferenceSteps": 10,
                "seed": 42,
                "fps": 24,
                "guidanceScale": 1.0,
                "embeddedGuidanceScale": 6.0,
                "flowShift": 12.0,
                "gpuCount": 2,
                "parallelism": "tensor parallel",
            },
            "weightBreakdownBytes": weight_sizes["componentsBytes"],
            "weightSizeBasis": weight_sizes["unit"],
        },
    }

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    video_bytes = sum(
        path.stat().st_size
        for directory in (VIDEO_STAGE / "agnes_original", VIDEO_STAGE / "hybrid_lms")
        for path in directory.glob("*.mp4")
    )
    input_bytes = sum(path.stat().st_size for path in MATERIAL_STAGE.rglob("*") if path.is_file())
    print(
        f"Prepared {len(cases)} R2VA pairs ({material_image_count} reference images, "
        f"{material_audio_count} audio references)."
    )
    print("Preferred eligible variants prioritized within each case.")
    print(f"Staged media: {video_bytes / 1024**2:.1f} MiB video, {input_bytes / 1024**2:.1f} MiB inputs.")
    print(f"Manifest: {MANIFEST_PATH.name}")


if __name__ == "__main__":
    main()
