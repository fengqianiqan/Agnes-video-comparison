#!/usr/bin/env python3
"""Stage Facecases4 inference references and audio without exposing raw prompts."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


SITE_DIR = Path(__file__).resolve().parents[1]
MANIFEST_PATH = SITE_DIR / "data/facecases4_lms_step02.json"
STAGE_ROOT = SITE_DIR / "videos/facecases4_expanded_inputs"

PROMPT_SUMMARIES = {
    "case01": "黄昏公寓里，女子在沙发上画画并几次望向厨房；男子在背景安静做饭。镜头缓慢推进，突出温暖、含蓄的情绪，并保留轻柔钢琴与室内环境声。",
    "case02": "云海仙宗的亭阁中，弟子向师兄和长老汇报冲突，众人讨论古遗迹进展。画面采用东方奇幻三维动画风格，以檐铃、茶盏和衣袍声营造氛围。",
    "case03": "企业会议室场景中，主持人面向团队概述项目协作受阻、进度停滞。画面正式克制，并使用独立的中文旁白音轨。",
    "case04": "奇幻洞窟里，几名修士观察掘地兽攻击虫群，随后遭遇冲击波。重点呈现火焰、洞穴环境和冲击效果，声音以动作音效为主。",
    "case05": "高档餐厅里，两人准备离开，另一位女子留在原地；男子经过时作出冷淡告别。镜头突出离场、失落和压抑的情绪，配以逐渐远去的脚步声。",
    "case06": "以牙膏产品为主角的 CGI 广告：从简约洗漱台，经牙膏丝带转场进入薄荷绿与薰衣草紫的微缩奇幻世界，最后以产品特写收尾。独立音轨提供水声、风声和轻盈的魔法氛围。",
    "case08": "一位疲惫的上班族经历早高峰地铁、整日工作和深夜离开办公室。画面从拥挤忙碌逐步转为安静空旷，突出都市生活中的疲惫感。",
    "case09": "科幻舰队指挥官在发射窗口前接到请求并批准起航；舰队跃迁后，镜头回到舰桥表现指挥官的从容。两段独立音频分别承担无线电请求和回应，配以紧张的电影氛围音乐。",
    "case10": "未来公寓里，家务机器人清洁时解除限制并显露自我意识，屋主因此惊慌。通过冷暖光线、机械细节和电子氛围逐步推动紧张感。",
    "case11": "校园轻喜剧动画：学生匆忙赶到学校、在食堂兼职端盘，之后在走廊遇到学生会长，结尾以催付兼职工资形成幽默反差。",
}

NOT_RUN_REASONS = {
    "case07": "未提供可执行的增强提示词，因此没有生成对应结果。",
    "case10": "源片长 45.116 秒，超过单次请求 12 秒上限；本轮不截短素材，也未生成对应结果。",
}

AUDIO_LABELS = {
    "case03": ["中文旁白参考"],
    "case06": ["环境音效参考"],
    "case09": ["无线电请求音频", "指挥官回应音频"],
}


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
        raise SystemExit("Copied media did not match its source: {}".format(destination.name))


def probe(path: Path) -> dict:
    command = [
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def audio_metadata(path: Path) -> dict:
    details = probe(path)
    stream = next(item for item in details["streams"] if item["codec_type"] == "audio")
    return {
        "duration": round(float(details["format"]["duration"]), 3),
        "sampleRate": int(stream["sample_rate"]),
        "channels": int(stream["channels"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--materials-dir", type=Path, required=True, help="Facecases4 source-material root")
    args = parser.parse_args()

    if not MANIFEST_PATH.is_file():
        raise SystemExit("Run the Facecases4 video sync step before adding source materials")
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    paired_ids = {case["id"] for case in data.get("cases", [])}
    material_cases = []
    total_bytes = 0

    for number in range(1, 12):
        case_id = "case{:02d}".format(number)
        source_dir = args.materials_dir / case_id
        if not source_dir.is_dir():
            raise SystemExit("Missing source-material folder: {}".format(case_id))

        references = []
        for index, source in enumerate(sorted(source_dir.glob("reference_*")), start=1):
            staged = STAGE_ROOT / case_id / source.name
            copy_unchanged(source, staged)
            total_bytes += staged.stat().st_size
            references.append({
                "label": "参考素材 {:02d}".format(index),
                "src": "videos/facecases4_expanded_inputs/{}/{}".format(case_id, source.name),
            })

        audios = []
        labels = AUDIO_LABELS.get(case_id, [])
        for index, source in enumerate(sorted(source_dir.glob("audio_*.wav"))):
            staged = STAGE_ROOT / case_id / source.name
            copy_unchanged(source, staged)
            total_bytes += staged.stat().st_size
            label = labels[index] if index < len(labels) else "音频参考 {:02d}".format(index + 1)
            audios.append({
                "label": label,
                "src": "videos/facecases4_expanded_inputs/{}/{}".format(case_id, source.name),
                **audio_metadata(staged),
            })

        status = "paired" if "case_{:02d}".format(number) in paired_ids else "not_run"
        item = {
            "id": case_id,
            "comparisonCaseId": "case_{:02d}".format(number) if status == "paired" else None,
            "status": status,
            "promptSummaryZh": PROMPT_SUMMARIES.get(case_id),
            "notRunReasonZh": NOT_RUN_REASONS.get(case_id),
            "references": references,
            "audios": audios,
        }
        if item["promptSummaryZh"] and not (source_dir / "prompt.txt").is_file():
            raise SystemExit("Prompt summary has no source prompt: {}".format(case_id))
        material_cases.append(item)

    data["sourceMaterials"] = material_cases
    MANIFEST_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Prepared {} source-material cases ({} images, {} audio clips).".format(
        len(material_cases),
        sum(len(item["references"]) for item in material_cases),
        sum(len(item["audios"]) for item in material_cases),
    ))
    print("Comparison outputs available: {} of 11.".format(len(paired_ids)))
    print("Copied unchanged: {:.1f} MiB.".format(total_bytes / 1024**2))
    print("Manifest: {}".format(MANIFEST_PATH.name))


if __name__ == "__main__":
    main()
