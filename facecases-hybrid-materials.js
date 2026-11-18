const materialsPicker = document.querySelector("#material-picker");
const materialsDetail = document.querySelector("#material-detail");
const originalTrack = document.querySelector("#video-original");
const hybridTrack = document.querySelector("#video-refined");
let sourceMaterials = [];

for (const option of document.querySelectorAll('input[name="pair-audio"]')) {
  option.addEventListener("change", () => {
    if (!option.checked) return;
    originalTrack.muted = option.value !== "original";
    hybridTrack.muted = option.value !== "lms";
  });
}

function makeElement(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function selectMaterial(item, selectComparison) {
  for (const button of materialsPicker.querySelectorAll(".material-case")) {
    button.setAttribute("aria-pressed", String(button.dataset.materialId === item.id));
  }
  renderMaterial(item);

  if (selectComparison && item.comparisonCaseId) {
    const button = document.querySelector(
      '.case-button[data-case-id="' + item.comparisonCaseId + '"]'
    );
    if (button) button.click();
    else if (window.selectComparisonCase) window.selectComparisonCase(item.comparisonCaseId);
  }
}

function formatSeconds(value) {
  if (!Number.isFinite(Number(value))) return "未记录";
  return `${Number(value).toFixed(2)} 秒`;
}

function renderPromptText(text) {
  const content = makeElement("div", "prompt-translation");
  for (const paragraphText of String(text || "").split(/\n+/).filter(Boolean)) {
    content.append(makeElement("p", "prompt-paragraph", paragraphText));
  }
  return content;
}

function renderDetailedDescription(text) {
  const content = makeElement("div", "prompt-translation");
  const paragraphs = String(text || "")
    .replace(/\n(?=\[Shot\s+\d+\]|【镜头\s*\d+】)/g, "\n\n")
    .split(/\n\s*\n/)
    .filter(Boolean);
  for (const paragraphText of paragraphs) {
    const paragraph = makeElement("p", "prompt-paragraph");
    const shot = paragraphText.match(/^(?:\[Shot\s*(\d+)\]|【镜头\s*(\d+)】)\s*([\s\S]*)$/);
    if (shot) {
      paragraph.append(makeElement("span", "shot-label", `镜头 ${shot[1] || shot[2]}`));
      paragraph.append(document.createTextNode(shot[3]));
    } else {
      paragraph.textContent = paragraphText;
    }
    content.append(paragraph);
  }
  return content;
}

function renderFullPrompt(prompt) {
  const labels = {
    subject_definitions: "主体与参考素材定义",
    summary: "提示摘要",
    retention_analysis: "素材保留分析",
    detailed_description: "详细场景描述",
    integrated_multimodal_description: "综合多模态场景描述",
    overall_soundscape: "整体声音设计",
    non_diegetic_music: "非画内配乐",
    reference_alignment: "参考图片与时间点对应关系",
    full_prompt: "完整提示词",
    主体与参考素材定义: "主体与参考素材定义",
    主体定义: "主体定义",
    参考素材定义: "参考素材定义",
    提示摘要: "提示摘要",
    概要: "提示摘要",
    素材保留分析: "素材保留分析",
    保留要求: "保留要求",
    详细场景描述: "详细场景描述",
    完整场景描述: "详细场景描述",
    综合多模态场景描述: "综合多模态场景描述",
    完整多模态描述: "综合多模态场景描述",
    参考图片与视频时间点对应关系: "参考图片与时间点对应关系",
    参考图与时间对应: "参考图与时间对应",
    参考绑定: "参考绑定",
    参考图与角色设定: "参考图与角色设定",
    参考图: "参考图",
    剧情: "剧情与镜头安排",
    视觉风格: "视觉风格",
    整体画面风格: "整体画面风格",
    本段视觉风格: "本段视觉风格",
    生成要求: "生成要求",
    整体声音设计: "整体声音设计",
    整体声音: "整体声音设计",
    整体音频: "整体音频要求",
    全局声音: "整体声音设计",
    非画内配乐: "非画内配乐",
    非画内音乐: "非画内音乐",
  };
  const preferredOrder = [
    "subject_definitions", "主体与参考素材定义", "主体定义", "参考素材定义", "参考绑定",
    "reference_alignment", "参考图片与视频时间点对应关系", "参考图与时间对应",
    "参考图与角色设定", "参考图", "summary", "提示摘要", "概要", "剧情",
    "retention_analysis", "素材保留分析", "保留要求", "detailed_description", "详细场景描述",
    "完整场景描述", "integrated_multimodal_description", "综合多模态场景描述",
    "完整多模态描述", "生成要求", "视觉风格", "整体画面风格", "本段视觉风格",
    "overall_soundscape", "整体声音设计", "整体声音", "整体音频", "全局声音",
    "non_diegetic_music", "非画内配乐", "非画内音乐", "full_prompt",
  ];
  const detailedFields = new Set([
    "detailed_description", "integrated_multimodal_description", "详细场景描述",
    "完整场景描述", "综合多模态场景描述", "完整多模态描述", "剧情",
  ]);
  const fields = Object.entries(prompt || {}).filter(([, value]) => typeof value === "string" && value.trim());
  fields.sort(([left], [right]) => {
    const leftIndex = preferredOrder.indexOf(left);
    const rightIndex = preferredOrder.indexOf(right);
    return (leftIndex < 0 ? preferredOrder.length : leftIndex) -
      (rightIndex < 0 ? preferredOrder.length : rightIndex);
  });

  const content = makeElement("div", "full-prompt-translation");
  for (const [key, text] of fields) {
    const section = makeElement("section", "prompt-section");
    section.append(makeElement("h5", "prompt-section-title", labels[key] || key));
    section.append(detailedFields.has(key)
      ? renderDetailedDescription(text)
      : renderPromptText(text));
    content.append(section);
  }
  return content;
}

function renderMaterial(item) {
  materialsDetail.replaceChildren();

  const heading = makeElement("div", "material-detail-heading");
  heading.append(makeElement("h3", "", `Case ${item.id.slice(-2)} · ${item.requestType}`));
  heading.append(makeElement("span", "material-status", "已配对"));
  materialsDetail.append(heading);

  const summaryCard = makeElement("div", "material-copy-card");
  summaryCard.append(makeElement("h4", "", `全部 Prompt 完整中文翻译 · ${item.category}`));
  if (item.promptFullZh && Object.keys(item.promptFullZh).length) {
    summaryCard.append(renderFullPrompt(item.promptFullZh));
  } else {
    summaryCard.append(makeElement("p", "pending-copy", "此案例的完整中文翻译尚未载入。"));
  }
  if (item.sceneScale) {
    summaryCard.append(makeElement("p", "material-scene-scale", `场景范围：${item.sceneScale}`));
  }
  materialsDetail.append(summaryCard);

  const timingCard = makeElement("div", "case-timing-card");
  timingCard.append(makeElement("h4", "", "当前案例生成耗时"));
  const timingValues = makeElement("div", "case-timing-values");
  timingValues.append(makeElement("span", "", `Agnes 模型生成 ${formatSeconds(item.agnesGenerationSeconds)}`));
  timingValues.append(makeElement("span", "", `Agnes 端到端 ${formatSeconds(item.agnesEndToEndSeconds)}`));
  timingValues.append(makeElement("span", "", `Hybrid 模型生成 ${formatSeconds(item.hybridGenerationSeconds)}`));
  timingValues.append(makeElement("span", "", "Hybrid 端到端 未记录"));
  timingCard.append(timingValues);
  materialsDetail.append(timingCard);

  if (item.references.length) {
    materialsDetail.append(makeElement("h4", "material-assets-heading", "参考图片 · 点击查看原图"));
    const referenceGrid = makeElement("div", "reference-grid");
    for (const reference of item.references) {
      const link = makeElement("a", "reference-tile");
      link.href = reference.src;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      const image = makeElement("img");
      image.src = reference.src;
      image.alt = `Case ${item.id.slice(-2)} ${reference.label}`;
      image.loading = "lazy";
      link.append(image, makeElement("span", "", reference.label));
      referenceGrid.append(link);
    }
    materialsDetail.append(referenceGrid);
  } else {
    materialsDetail.append(makeElement("p", "pending-copy", "此请求没有独立参考图片。"));
  }

  if (item.audios.length) {
    materialsDetail.append(makeElement("h4", "material-assets-heading", "独立音频参考"));
    const audioGrid = makeElement("div", "audio-reference-grid");
    for (const source of item.audios) {
      const audioCard = makeElement("div", "audio-reference");
      audioCard.append(makeElement("span", "", `${source.label} · ${Number(source.duration).toFixed(2)} 秒`));
      const audio = makeElement("audio");
      audio.controls = true;
      audio.preload = "none";
      audio.src = source.src;
      audioCard.append(audio);
      audioGrid.append(audioCard);
    }
    materialsDetail.append(audioGrid);
  }
}

const fetchJson = (url) => fetch(url).then((response) => {
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
});

Promise.all([
  fetchJson(document.body.dataset.casesUrl),
  fetchJson(document.body.dataset.promptTranslationsUrl),
])
  .then(([data, promptTranslations]) => {
    sourceMaterials = data.sourceMaterials || [];
    for (const item of sourceMaterials) {
      item.promptFullZh = promptTranslations[item.id] || {};
    }
    const fragment = document.createDocumentFragment();
    for (const item of sourceMaterials) {
      const button = makeElement("button", "material-case");
      button.type = "button";
      button.dataset.materialId = item.id;
      button.setAttribute("aria-pressed", "false");
      button.append(
        makeElement("strong", "", `Case ${item.id.slice(-2)}`),
        makeElement("span", "", item.requestType)
      );
      button.addEventListener("click", () => selectMaterial(item, true));
      fragment.append(button);
    }
    materialsPicker.replaceChildren(fragment);
    if (sourceMaterials.length) selectMaterial(sourceMaterials[0], false);
    const referenceCount = sourceMaterials.reduce((sum, item) => sum + item.references.length, 0);
    const audioCount = sourceMaterials.reduce((sum, item) => sum + item.audios.length, 0);
    document.querySelector("#materials-count").textContent =
      `${sourceMaterials.length} 组请求 · ${referenceCount} 张参考图 · ${audioCount} 段独立音频`;
  })
  .catch(() => {
    materialsDetail.textContent = "素材清单暂时无法载入，请刷新页面后重试。";
  });

const caseGrid = document.querySelector("#case-grid");
if (caseGrid) {
  caseGrid.addEventListener("click", (event) => {
    const button = event.target.closest(".case-button");
    if (!button) return;
    const caseId = button.dataset.caseId;
    const item = sourceMaterials.find((candidate) => candidate.comparisonCaseId === caseId);
    if (item) selectMaterial(item, false);
  });
}
