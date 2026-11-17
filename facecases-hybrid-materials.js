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
  }
}

function formatSeconds(value) {
  if (!Number.isFinite(Number(value))) return "未记录";
  return `${Number(value).toFixed(2)} 秒`;
}

function renderMaterial(item) {
  materialsDetail.replaceChildren();

  const heading = makeElement("div", "material-detail-heading");
  heading.append(makeElement("h3", "", `Case ${item.id.slice(-2)} · ${item.requestType}`));
  heading.append(makeElement("span", "material-status", item.variantSuffix === "good" ? "选用 good 标记文件" : "已配对"));
  materialsDetail.append(heading);

  const summaryCard = makeElement("div", "material-copy-card");
  summaryCard.append(makeElement("h4", "", `Prompt 主题摘要 · ${item.category}`));
  summaryCard.append(makeElement("p", "", item.promptSummary));
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

fetch(document.body.dataset.casesUrl)
  .then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  })
  .then((data) => {
    sourceMaterials = data.sourceMaterials || [];
    const fragment = document.createDocumentFragment();
    for (const item of sourceMaterials) {
      const button = makeElement("button", "material-case");
      button.type = "button";
      button.dataset.materialId = item.id;
      button.setAttribute("aria-pressed", "false");
      button.append(
        makeElement("strong", "", `Case ${item.id.slice(-2)}`),
        makeElement("span", "", `${item.requestType}${item.variantSuffix === "good" ? " · good" : ""}`)
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

document.querySelector("#case-grid").addEventListener("click", (event) => {
  const button = event.target.closest(".case-button");
  if (!button) return;
  const caseId = button.dataset.caseId;
  const item = sourceMaterials.find((candidate) => candidate.comparisonCaseId === caseId);
  if (item) selectMaterial(item, false);
});
