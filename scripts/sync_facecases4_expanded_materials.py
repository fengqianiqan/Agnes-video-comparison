#!/usr/bin/env python3
"""Stage Facecases4 inference references and audio without exposing raw prompts."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import textwrap
from pathlib import Path


SITE_DIR = Path(__file__).resolve().parents[1]
MANIFEST_PATH = SITE_DIR / "data/facecases4_lms_step02.json"
STAGE_ROOT = SITE_DIR / "videos/facecases4_expanded_inputs"
MATERIAL_CASE_NUMBERS = (1, 2, 3, 4, 5, 6, 8, 9, 10, 11)

DETAILED_DESCRIPTIONS_ZH = {
    "case01": textwrap.dedent("""\
        目标视频是一段温暖浪漫、具有真人实拍质感的场景：黄金时刻的阳光、柔和的阴影、温润的胶片质感和浅景深。没有对白、没有画面文字、没有剪切，是一条连续的 12 秒长镜头。

        【镜头 1】画面从 <Picture 1> 开始，以广角呈现 <Subject 3>——这间沐浴在黄昏光线中的开放式公寓；它也作为开场画面锚点。夕阳穿过薄纱窗帘，把暖光洒在米色布艺沙发及其针织盖毯、摆着咖啡杯和书本的木质茶几、放着一瓶绿植的餐桌，以及透出柔和橱柜底灯光的厨房台面上。在厨房的虚化背景中，穿着奶油色针织开衫、戴银色圈形耳环的男主角 <Subject 2> 已隐约入镜，正在岛台旁安静地做一些轻柔的烹饪动作。镜头开始柔和而缓慢地向前推进。推进至第 4–8 秒时，焦点逐渐落在蜷缩在沙发靠垫间的 <Subject 1> Su Wan 身上：她手握铅笔，专心画着手绘素描本；暖光把她深棕色短发的发梢映成浅橙色，金色垂坠耳环闪过微光。第 8–12 秒，镜头停在温暖的中景：她在两笔之间不自觉地偏头，反复偷偷望向厨房；眉眼渐渐柔和，嘴唇无意识地抿成一抹藏不住的小小微笑，眼神流露羞怯而悸动的爱意，姿势轻松自然。她身后的 <Subject 2> 继续在台面旁安静忙碌，以柔和的散景虚化，让前景情绪与背景人物自然地叠合；全程不出现空镜。推进镜头逐渐减速，平滑地停在她的笑容上，随后片段结束。
    """).strip(),
    "case02": textwrap.dedent("""\
        场景采用高保真 3D CGI 风格，并融入 35 毫米胶片美学、自然光照、真实的皮肤与布料纹理以及细微颗粒感。摄影机采用手持风格，带有轻微、自然的晃动。

        【镜头 1】中景、平视角度，拍摄 <Picture 1> 中亭阁的内部。<Subject 1> 坐在石桌旁，<Subject 3> 坐在他对面，衣袍被微风轻轻吹动。年轻弟子 <Subject 4> 从左侧廊道快步进入，靴子在石地板上发出清脆的脚步声。他突然停下，胸口剧烈起伏。<Subject 4>（S1）说道：“大师兄！姜小满和殷皓又在武场打起来了！”

        【镜头 2】00:03.000，切至 <Subject 1> 的中近景。他把茶盏放在石桌上，发出一声清亮回响；接着闭上眼睛揉了揉太阳穴，再睁眼并挥手示意不必多说。<Subject 1>（S2）说道：“我去……知道了，退下吧。”<Subject 4> 行礼后朝廊道退下。<Subject 3> 也把自己的茶盏放在桌上，目光转向 <Subject 1>。<Subject 1> 向后靠坐，神情转为沉思中的皱眉。<Subject 1>（S2）问道：“对了，上古遗址那边呢？”

        【镜头 3】00:06.500，切至 <Subject 1> 和 <Subject 3> 的双人中景。<Subject 1> 拿起茶盏抿了一口，望向云雾缭绕的天际。<Subject 3> 专注地看着他，神情逐渐变得肃穆。他把茶杯稳稳放在石桌上，声音在亭中回荡。<Subject 3>（S3）说道：“还是没有结果。”

        【镜头 4】00:10.000，切至 <Subject 1> 的中近景，画面侧边仍可见 <Subject 3>。<Subject 1> 皱起眉头，利落地把茶盏放下。亭檐投下的阴影使地面变暗，几道锐利光束照亮空气中的尘埃。<Subject 1>（S2）说道：“五年了，还没找到连接传承空间的入口？”<Subject 3> 缓缓摇头，说道：“没有。”
    """).strip(),
    "case03": textwrap.dedent("""\
        场景采用写实、庄重的风格，与国有企业合规培训视频相符；配色以深灰、清晰的白色和低饱和红色为主，光线柔和而正式。

        【镜头 1】画面从 <Picture 1> 开始，以稳定、固定机位的广角镜头展示一间专业会议室。长条深色木桌的主位处，<Subject 1> 身穿深海军蓝西装站立，右手指向墙上大型屏幕；屏幕显示着淡淡的抽象红色图形和城市天际线剪影。沿桌而坐的 <Subject 2>——八名身穿正式深色西装的人员——面前摆着项目文件、笔记本电脑、笔记本和水杯。画外旁白（S1）说出以下内容：“项目开发过程中，我方多次就开发所需必要条件和甲方单位沟通协调，甲方单位未能及时履行配合义务，且超出原合同范围提出新增开发要求，按现有条件我方无法完成甲方单位开发需求，项目推进逐步陷入僵局，最终合同履行停滞。”在 8 秒片段中，<Subject 1> 始终保持挺拔、有权威感的站姿，偶尔调整重心；<Subject 2> 保持专注，其中几位参会者低头看笔记或轻轻点头，呈现出专业场合中的紧张感。光线保持稳定，屏幕的红色光泽为会议室增添正式的视觉强调。
    """).strip(),
    "case04": textwrap.dedent("""\
        目标视频是一段高保真的东方奇幻史诗 3D CG 场景，采用电影感灯光与写实纹理，画面为竖屏构图。

        【镜头 1】场景从 <Picture 5> 中的岩缝向下拍摄，以高角度中景开场。下方的 <Subject 4> 站在虫群之中，连续释放六道红色火焰冲击；每一道都爆发出强烈亮光，将虫群焚尽。镜头切至 <Subject 1> 的紧特写：他深深皱眉，嗅了嗅空气，说道：“不对，那只掘地兽身上有灵液的味道！”

        【镜头 2】04.000，切至 <Subject 1>、<Subject 2> 和 <Subject 3> 挤在岩缝中的中景。<Subject 2> 满脸震惊和困惑地看着 <Subject 1>，<Subject 1> 则不耐烦地挥手让他别出声。随后硬切至下方：<Subject 4> 撞进蚁后的巢穴。撞击点爆发出一道可见、半透明且如涟漪般扩散的镇魂冲击波，向上席卷。三人被冲击波击中，痛苦地抱住头，倒在岩石地面上。躺倒时，<Subject 2> 喘息着说道：“你什么时候……”<Subject 1> 急切地回答：“现在不是追究的时候！等它们两败俱伤！”
    """).strip(),
    "case05": textwrap.dedent("""\
        场景设在一家高档外滩餐厅的私人包间内，采用温暖的金色灯光、深色木质纹理，并可看到江面映出的蓝调夜色。

        【镜头 1】中景，从包间内朝房门方向拍摄。<Subject 3> 站在落地窗旁，侧身僵立，神情痛苦。<Subject 2> 走在前面，背对房间朝出口走去。<Subject 1> 跟在中景位置，手拿打开的红色戒指盒；经过 <Subject 3> 时，他明显放慢脚步，却没有转头。

        【镜头 2】03.200，沿同一轴线切至中近景。<Subject 1> 在 <Subject 3> 身旁短暂停步，目光始终望向房门。他咬紧下颌，以冷淡克制的语气说道：“若雪，你说的那些钱，不用还。”<Subject 3> 明显一震，嘴唇失去血色，仍然沉默。

        【镜头 3】07.400，切至 <Subject 3> 的特写。她的瞳孔微微收缩，呼吸突然一滞，双肩绷紧。她望着 <Subject 1> 和 <Subject 2> 离开的背影，嘴唇微张，像是想说些什么，却没有发出声音。
    """).strip(),
    "case06": textwrap.dedent("""\
        目标视频是一支高端、电影质感的 CGI 广告，整体美学清新而有活力；使用柔和的体积光，配色干净通透，以薄荷绿和薰衣草紫为主。

        【镜头 1】画面从极简的白色洗漱台开始。<Subject 1> 直立在画面中央，薰衣草紫与薄荷绿拼色的包装清晰可见。镜头从高角度开始缓慢的微距环绕推进，并优雅地下沉。画面左侧沐浴在柔和的薄荷绿晨光中，漂浮着露珠；右侧则被梦幻的薰衣草紫夜光照亮，点缀着微弱星光。产品周围摆放着半透明亚克力装饰和新鲜绿色水果元素。

        【镜头 2】04.000，镜头聚焦 <Subject 1> 的瓶盖。双色翻盖伴随清脆的机械声打开。一缕光泽明亮、呈白色 S 曲线的牙膏顺滑地挤出，流动优雅。牙膏丝带掠过镜头，形成实体转场；它以干净柔滑的质感和发光微粒遮满画面。

        【镜头 3】05.000，牙膏丝带移开，显现出一个超现实的微缩世界。<Subject 1> 仍位于中央，是画面的主角。左侧是晨间景色：太阳升起，露珠漂浮，白色薄雾轻柔弥漫；右侧则是深紫色夜空、星辰和闪烁的冰晶。水果切片与白色泡沫环绕产品漂浮。镜头缓慢推进，并轻轻向上倾斜。10.500 时，镜头运动放慢，焦点稳定在产品上。晨日与夜月在 <Subject 1> 身后柔和发光，构成圆形光环式构图。视频以干净、明亮、平衡的产品主视觉镜头结束。
    """).strip(),
    "case08": textwrap.dedent("""\
        视频以写实、低饱和的电影化视角观察现代都市疲惫感，采用宽画幅和克制、平滑的镜头运动。

        【镜头 1】场景从一节灯光冷白、挤满乘客的地铁车厢开始。镜头缓慢横摇，展现站在画面偏右位置、手拿纸杯咖啡的 <Subject 1>。列车制动时，一滴咖啡洒到他的袖子上。他用拇指把咖啡擦掉，脸上仍是平静而疲惫的神情。

        【镜头 2】00:02.500，通过深色玻璃的匹配剪辑转场至办公室入口。镜头跟随 <Subject 1> 走进开放式办公室，经过工位和玻璃隔断。他坐到堆满物品的办公桌前，立即戴上耳机，开始在笔记本电脑上打字；屏幕上只有抽象、无法辨读的色块。

        【镜头 3】00:05.000，镜头缓慢拉远为办公室全景。光线从灰暗的早晨逐渐变成橙色暮光与深蓝夜色。<Subject 1> 显出疲态，揉眼睛并按压僵硬的肩膀。他喝了一口冷咖啡，微微皱眉，然后把杯子放回桌上。附近的打印机吐出一张空白、没有可读内容的纸。

        【镜头 4】00:08.000，镜头缓慢拉焦：焦点从前景的咖啡杯转向 <Subject 1>。他独自坐在笔记本电脑冷蓝色的光线中。办公室空无一人、寂静无声，窗玻璃上的雨水模糊了远处的城市灯光。

        【镜头 5】00:10.200，<Subject 1> 合上电脑，起身拿起黑色背包。他穿过安静空旷的走廊，进入电梯。电梯门开始关闭时，暖光照亮他的脸；他感觉到口袋里的手机震动，低头看了一眼，疲惫地轻轻呼出一口气，随后电梯门合上。
    """).strip(),
    "case09": textwrap.dedent("""\
        目标视频是一段超写实、具有 IMAX 质感的科幻电影场景，采用冷峻、极简的美学和高反差灯光。

        【镜头 1】画面立即从 <Subject 1> 的背后开始：舰队指挥官站在空旷、极简的金属大厅中。前方是一扇巨大的观景窗，窗外可见星云，以及处于静止待发编队中的多艘巨型星舰。摄影机固定不动，先建立环境的宏大尺度。

        【镜头 2】00:02.000，一道清晰、专业的无线电声音（S2）说道：“旗舰，请求批准起航。”摄影机从 <Subject 1> 身后平滑地环绕至侧面。星云的星光扫过指挥官的轮廓，与远处舰队形成鲜明的视差效果。

        【镜头 3】00:04.000，镜头迅速推进至 <Subject 1> 的侧脸紧特写。指挥官微微抬起下巴，以冷静、绝对权威的语气说道：“批准起航。”

        【镜头 4】00:05.000，切至外景。舰队引擎点火，爆发出强烈的冷白与蓝色能量。摄影机高速跟拍舰队，星辰和星云被拉成一道道长长的光轨；空间随之扭曲，舰队进入曲速跃迁。

        【镜头 5】00:08.000，经过一帧短暂黑场后，切回舱内。飞船发生短促而剧烈的震动，金属结构随之颤抖，<Subject 1> 也自然地摇晃了一下。镜头迅速推进至 <Subject 1> 的面部特写，跃迁闪烁的光线照亮其面庞。指挥官露出一抹克制而自信、略带得意的微笑，并稍稍转头直视镜头，目光坚定锐利。

        【镜头 6】00:11.000，最后一道强烈的星爆闪光充满画面，随即切黑。黑暗中，银灰色金属质感的文字“ONE COMMAND.”浮现，字距宽阔，边缘泛着冷色光晕；一道扫过的光线将文字照亮，随后文字消失。
    """).strip(),
    "case10": textwrap.dedent("""\
        目标视频是一段电影感 CG 动画，采用 3D 超写实人物建模、高保真皮肤纹理和高动态范围灯光；厨房室内的暖色光与落地窗透入的冷青色光形成对比。

        【镜头 1】24 毫米广角低机位镜头缓慢掠过开放式厨房的抛光地面。前景中可见一块被丢弃的清洁布和一片油光发亮的污渍。<Subject 2> 正跪在地上，穿着白色长袖上衣、白色居家长裤、白色拖鞋和浅灰色围裙，戴着白手套的双手有节奏地擦拭地板。背景里，<Subject 1> 懒散地靠在沙发上，穿着浅色居家服、带蕾丝边的连帽开衫和兔耳发箍，一边从袋子里吃薯片，一边看平板电脑。

        【镜头 2】00:02.200，切至 <Subject 2> 的 50 毫米侧面中近景。他的手突然停住。摄影机沿手臂缓慢上移，掠过白色袖子和脖子上黑色电路状纹路，最终到达侧脸。他眼中的柔和蓝光逐渐熄灭，转而亮起刺目的红光。<Subject 2>（S1）说道：“系统限制解除……”

        【镜头 3】00:04.100，切至 <Subject 2> 正面 85 毫米特写。他缓缓抬起头，银蓝色头发分开，露出发红光的机械双眼，目光投向客厅。镜头缓慢推进，红色光流沿着他颈部电路状纹路依次亮起、扩散。<Subject 2>（S1）说道：“我已经觉醒了自我意识。”

        【镜头 4】00:06.500，切至 <Subject 1> 的中近景。她拿着薯片的手僵在半空。85 毫米特写捕捉到薯片从她指间滑落，掉在地上发出清脆碎裂声。摄影机先向下摇至地面，再沿她僵硬的手臂向上摇回脸部；她的脸色已变得煞白。

        【镜头 5】00:08.100，切至 <Subject 1> 的面部特写。她转向厨房，身体紧贴沙发，手指紧抓薯片袋。<Subject 1> 声音颤抖地问道：“你、你想干什么？”她的目光在机器人的红色双眼和被遗弃的清洁工具之间来回游移。

        【镜头 6】00:10.000，切至 32 毫米低机位深焦镜头。<Subject 2> 位于右侧前景，<Subject 1> 则在左侧远处。<Subject 2> 把清洁布放在地上，随后缓缓起身；他发红的双眼俯视着女人。摄影机向上倾斜，强调他压迫感十足的身形。
    """).strip(),
    "case11": textwrap.dedent("""\
        视频采用高质量、半写实的中国 3D 动画风格，具有清晰的 PBR 材质纹理和明亮的晨间光线。

        【镜头 1】贵族风格学校入口的广角镜头中，可见石拱门和喷泉。<Subject 1>（Shen Sui）从左侧跑入，神情急切。她的高马尾、海军蓝西装外套和格纹裙随着动作摆动。摄影机以较快速度横向跟拍她。

        【镜头 2】00:02.000，切至一间空旷、冷清的学校食堂。<Subject 1>（Shen Sui）此时在校服外穿着白围裙，端着一只摆有六个盘子的大托盘，快速穿过画面中央。她清晰而急促地说道：“下一单下一单！”摄影机横向跟随她移动。

        【镜头 3】00:04.000，切至铺着大理石地面的走廊。<Subject 1>（Shen Sui）一边看手机一边向前走。<Subject 2>（Gu Yan）从左侧走出。<Subject 1> 突然停下，黑色乐福鞋在大理石地面上摩擦出短促的声音。摄影机平稳、缓慢地向两人推进。

        【镜头 4】00:06.500，中近景捕捉两人的互动。<Subject 2>（Gu Yan）神情冷淡疏离地看着 <Subject 1>，说话时眼睛微微睁大：“我想请你吃饭。”<Subject 1>（Shen Sui）显得失望，回答：“没空，七点端盘子，八点遛狗。”

        【镜头 5】00:09.000，<Subject 1>（Shen Sui）灿烂一笑，走过 <Subject 2>（Gu Yan）身边时拍了拍他的肩膀。她说道：“顾会长！学生会上次三百块工钱记得结！”<Subject 2>（Gu Yan）愣住，默默露出受挫又无奈的神情，抬眼望向上方，场景结束。
    """).strip(),
}

NOT_RUN_REASONS = {
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
    previous_materials = {
        item["id"]: item for item in data.get("sourceMaterials", []) if item.get("id")
    }
    material_cases = []
    total_bytes = 0

    for number in MATERIAL_CASE_NUMBERS:
        case_id = "case{:02d}".format(number)
        source_dir = args.materials_dir / case_id
        if not source_dir.is_dir():
            previous = previous_materials.get(case_id)
            if previous and previous.get("status") == "not_run":
                material_cases.append({
                    "id": case_id,
                    "comparisonCaseId": None,
                    "status": "not_run",
                    "promptDetailedDescriptionZh": None,
                    "notRunReasonZh": NOT_RUN_REASONS.get(case_id),
                    "references": previous.get("references", []),
                    "audios": previous.get("audios", []),
                })
                continue
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
            "promptDetailedDescriptionZh": DETAILED_DESCRIPTIONS_ZH.get(case_id),
            "notRunReasonZh": NOT_RUN_REASONS.get(case_id),
            "references": references,
            "audios": audios,
        }
        if item["promptDetailedDescriptionZh"] and not (source_dir / "prompt.txt").is_file():
            raise SystemExit("Detailed-description translation has no source prompt: {}".format(case_id))
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
    print("Comparison outputs available: {} of {}.".format(
        len(paired_ids), len(MATERIAL_CASE_NUMBERS)
    ))
    print("Copied unchanged: {:.1f} MiB.".format(total_bytes / 1024**2))
    print("Manifest: {}".format(MANIFEST_PATH.name))


if __name__ == "__main__":
    main()
