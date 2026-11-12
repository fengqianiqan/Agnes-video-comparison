const originalTrack = document.querySelector("#video-original");
const lmsTrack = document.querySelector("#video-refined");
const audioOptions = document.querySelectorAll('input[name="pair-audio"]');
const materialPicker = document.querySelector("#material-picker");
const materialDetail = document.querySelector("#material-detail");
let materials = [];

function setComparisonAudio(mode) {
  originalTrack.muted = mode !== "original";
  lmsTrack.muted = mode !== "lms";
}

for (const option of audioOptions) {
  option.addEventListener("change", () => {
    if (option.checked) setComparisonAudio(option.value);
  });
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderDetailedDescription(translationText) {
  const translation = element("div", "prompt-translation");
  const paragraphs = translationText.split(/\n\s*\n/).filter(Boolean);

  for (const text of paragraphs) {
    const paragraph = element("p", "prompt-paragraph");
    const shot = text.match(/^(【镜头\s*\d+】)\s*([\s\S]*)$/);
    if (shot) {
      paragraph.append(element("span", "shot-label", shot[1]));
      paragraph.append(document.createTextNode(shot[2]));
    } else {
      paragraph.textContent = text;
    }
    translation.append(paragraph);
  }

  return translation;
}

function renderMaterials(item) {
  materialDetail.replaceChildren();

  const heading = element("div", "material-detail-heading");
  heading.append(element("h3", "", "Facecases4 · " + item.id.slice(-2)));
  heading.append(element(
    "span",
    "material-status" + (item.status === "paired" ? "" : " is-pending"),
    item.status === "paired" ? "已有视频对比" : "本轮未生成"
  ));
  materialDetail.append(heading);

  const promptCard = element("div", "material-copy-card");
  promptCard.append(element("h4", "", "全部 Prompt 完整中文翻译"));
  if (item.promptDetailedDescriptionZh) {
    promptCard.append(renderDetailedDescription(item.promptDetailedDescriptionZh));
  } else {
    promptCard.append(element("p", "pending-copy", "此案例未提供 Prompt，因此没有完整中文译文。"));
  }

  materialDetail.append(promptCard);

  if (item.notRunReasonZh) materialDetail.append(element("p", "retest-note", item.notRunReasonZh));

  materialDetail.append(element("h4", "material-assets-heading", "参考图片 · 点击查看原图"));
  const references = element("div", "reference-grid");
  for (const reference of item.references) {
    const link = element("a", "reference-tile");
    link.href = reference.src;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    const image = element("img");
    image.src = reference.src;
    image.alt = "Facecases4 " + item.id.slice(-2) + " " + reference.label;
    image.loading = "lazy";
    link.append(image, element("span", "", reference.label));
    references.append(link);
  }
  materialDetail.append(references);

  if (item.audios.length) {
    materialDetail.append(element("h4", "material-assets-heading", "独立音频参考"));
    const audioGrid = element("div", "audio-reference-grid");
    for (const source of item.audios) {
      const card = element("div", "audio-reference");
      card.append(element("span", "", source.label + " · " + Number(source.duration).toFixed(2) + " 秒"));
      const audio = element("audio");
      audio.controls = true;
      audio.preload = "none";
      audio.src = source.src;
      card.append(audio);
      audioGrid.append(card);
    }
    materialDetail.append(audioGrid);
  }
}

function selectMaterial(item, syncComparison) {
  for (const button of materialPicker.querySelectorAll(".material-case")) {
    button.setAttribute("aria-pressed", String(button.dataset.materialId === item.id));
  }
  renderMaterials(item);
  if (syncComparison && item.comparisonCaseId) {
    const compareButton = document.querySelector(
      '.case-button[data-case-id="' + item.comparisonCaseId + '"]'
    );
    if (compareButton) compareButton.click();
  }
}

fetch("data/facecases4_lms_step02.json?v=expanded-4")
  .then((response) => {
    if (!response.ok) throw new Error("Facecases4 source manifest unavailable");
    return response.json();
  })
  .then((data) => {
    materials = data.sourceMaterials || [];
    for (const item of materials) {
      const button = element("button", "material-case");
      button.type = "button";
      button.dataset.materialId = item.id;
      button.setAttribute("aria-pressed", "false");
      button.append(
        element("strong", "", "Case " + item.id.slice(-2)),
        element("span", "", item.status === "paired" ? "可比较" : "未生成")
      );
      button.addEventListener("click", () => selectMaterial(item, true));
      materialPicker.append(button);
    }
    if (materials.length) selectMaterial(materials[0], false);
    document.querySelector("#materials-count").textContent =
      materials.length + " 组复测条目 · " +
      materials.reduce((total, item) => total + item.references.length, 0) + " 张参考图 · " +
      materials.reduce((total, item) => total + item.audios.length, 0) + " 段独立音频";
  })
  .catch(() => {
    materialDetail.textContent = "素材清单暂时无法载入，请刷新页面后重试。";
  });

document.querySelector("#case-grid").addEventListener("click", (event) => {
  const button = event.target.closest(".case-button");
  if (!button) return;
  const number = button.dataset.caseId.slice(-2);
  const item = materials.find((candidate) => candidate.id === "case" + number);
  if (item) selectMaterial(item, false);
});
