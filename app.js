const originalVideo = document.querySelector("#video-original");
const refinedVideo = document.querySelector("#video-refined");
const stage = document.querySelector("#compare-stage");
const divider = document.querySelector("#split-divider");
const loading = document.querySelector("#stage-loading");
const playButtons = [document.querySelector("#play-control"), document.querySelector("#stage-play")];
const playIcons = [document.querySelector("#control-play-icon"), document.querySelector("#play-icon")];
const timeline = document.querySelector("#timeline");
const currentTimeLabel = document.querySelector("#current-time");
const durationLabel = document.querySelector("#duration");
const statusMessage = document.querySelector("#status-message");

let cases = [];
let selectedCase = null;
let split = 50;
let pointerId = null;
let dragFrame = 0;
let playbackSyncFrame = 0;
let lastSyncAt = 0;
let metadataReady = 0;
let detailZoomEnabled = false;
const detailZoomControl = document.querySelector("#detail-zoom-control");

function formatTime(seconds) {
  const whole = Math.max(0, Math.floor(Number.isFinite(seconds) ? seconds : 0));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

function setSplit(value) {
  split = Math.max(0, Math.min(100, value));
  stage.style.setProperty("--split", `${split}%`);
  stage.setAttribute("aria-valuenow", String(Math.round(split)));
  stage.setAttribute("aria-valuetext", `${Math.round(split)} percent original, ${100 - Math.round(split)} percent refined`);
}

function setPlayingUi(playing) {
  for (const button of playButtons) button.setAttribute("aria-label", playing ? "Pause both videos" : "Play both videos");
  for (const icon of playIcons) icon.textContent = playing ? "Ⅱ" : "▶";
}

function updateProgress() {
  const duration = originalVideo.duration;
  const current = originalVideo.currentTime || 0;
  if (Number.isFinite(duration) && duration > 0) {
    timeline.value = String(Math.round((current / duration) * Number(timeline.max)));
    durationLabel.textContent = formatTime(duration);
    currentTimeLabel.textContent = formatTime(current);
  }
}

function clearSyncLoop() {
  if (playbackSyncFrame) cancelAnimationFrame(playbackSyncFrame);
  playbackSyncFrame = 0;
}

function syncPlaybackFrame(now) {
  if (originalVideo.paused || refinedVideo.paused) {
    clearSyncLoop();
    return;
  }
  if (now - lastSyncAt > 220) {
    lastSyncAt = now;
    const drift = refinedVideo.currentTime - originalVideo.currentTime;
    if (Math.abs(drift) > 0.08) {
      try { refinedVideo.currentTime = originalVideo.currentTime; } catch (_) { /* Metadata may be changing. */ }
    }
  }
  playbackSyncFrame = requestAnimationFrame(syncPlaybackFrame);
}

function startSyncLoop() {
  clearSyncLoop();
  lastSyncAt = 0;
  playbackSyncFrame = requestAnimationFrame(syncPlaybackFrame);
}

async function playPair() {
  statusMessage.textContent = "";
  try {
    const starts = await Promise.all([originalVideo.play(), refinedVideo.play()]);
    if (starts.length === 2) startSyncLoop();
    setPlayingUi(true);
  } catch (error) {
    setPlayingUi(false);
    statusMessage.textContent = "Playback was blocked by the browser. Press play to start both clips.";
  }
}

function pausePair() {
  originalVideo.pause();
  refinedVideo.pause();
  clearSyncLoop();
  setPlayingUi(false);
}

function togglePlayback() {
  if (originalVideo.paused || refinedVideo.paused) playPair();
  else pausePair();
}

function hideLoading() {
  if (metadataReady >= 2) loading.classList.add("is-hidden");
}

function fitStage(width, height) {
  if (!width || !height) return;
  const ratio = width / height;
  const availableWidth = stage.parentElement.clientWidth;
  const useLargeViewer = document.body.dataset.largeViewer === "true";
  const maxHeight = useLargeViewer
    ? Math.min(window.innerHeight * 0.86, 1000)
    : Math.min(window.innerHeight * 0.72, 760);
  stage.style.aspectRatio = `${width} / ${height}`;
  stage.style.width = `${Math.min(availableWidth, maxHeight * ratio)}px`;
}

function onMetadata(video) {
  metadataReady += 1;
  if (metadataReady === 2 && selectedCase) {
    const widthMatches = originalVideo.videoWidth === refinedVideo.videoWidth;
    const heightMatches = originalVideo.videoHeight === refinedVideo.videoHeight;
    const durationMatches = Math.abs(originalVideo.duration - refinedVideo.duration) <= 0.05;
    if (!widthMatches || !heightMatches || !durationMatches) {
      statusMessage.textContent = document.body.dataset.mismatchMessage || "This pair has a resolution or duration mismatch; playback is synchronized to the original clip.";
    }
    originalVideo.currentTime = 0;
    refinedVideo.currentTime = 0;
    updateProgress();
    hideLoading();
    playPair();
  } else {
    hideLoading();
  }
  if (video.videoWidth && video.videoHeight && metadataReady === 2) {
    fitStage(originalVideo.videoWidth, originalVideo.videoHeight);
    if (!selectedCase.specText) {
      document.querySelector("#video-spec").textContent = `${video.videoWidth} × ${video.videoHeight} · ${formatTime(video.duration)}`;
    }
  }
}

function setSelectedButton(caseId) {
  for (const button of document.querySelectorAll(".case-button")) {
    button.setAttribute("aria-current", button.dataset.caseId === caseId ? "true" : "false");
  }
}

function selectCase(item) {
  if (!item || item.id === selectedCase?.id) return;
  pausePair();
  selectedCase = item;
  metadataReady = 0;
  loading.classList.remove("is-hidden");
  statusMessage.textContent = "";
  document.querySelector("#case-kicker").textContent = item.kicker || `${item.id.toUpperCase()} / ${item.type.toUpperCase()}`;
  document.querySelector("#case-title").textContent = item.title || `Production output · ${item.type.toUpperCase()}`;
  document.querySelector("#video-spec").textContent = item.specText || `${item.width} × ${item.height} · ${formatTime(item.duration)}`;
  const originalResolution = document.querySelector("#original-resolution");
  const refinedResolution = document.querySelector("#refined-resolution");
  if (originalResolution && item.originalMeta) {
    originalResolution.textContent = `${item.originalMeta.width} × ${item.originalMeta.height} · 原始分辨率`;
  }
  if (refinedResolution && item.refinedMeta) {
    refinedResolution.textContent = `${item.refinedMeta.width} × ${item.refinedMeta.height} · Open-H3 输出`;
  }
  fitStage(item.width, item.height);
  timeline.value = "0";
  currentTimeLabel.textContent = "0:00";
  durationLabel.textContent = formatTime(item.duration);
  setSelectedButton(item.id);
  originalVideo.src = item.original;
  refinedVideo.src = item.refined;
  originalVideo.load();
  refinedVideo.load();
}

function renderCaseButtons() {
  const grid = document.querySelector("#case-grid");
  const fragment = document.createDocumentFragment();
  for (const item of cases) {
    const button = document.createElement("button");
    button.className = "case-button";
    button.type = "button";
    button.dataset.caseId = item.id;
    button.setAttribute("aria-current", "false");
    button.setAttribute("aria-label", `Show ${item.title || item.id}, ${item.type}`);
    const number = document.createElement("span");
    number.className = "case-number";
    number.textContent = item.id.replace("case_", "Case ");
    const label = document.createElement("span");
    label.className = "case-type";
    label.textContent = item.dimension || item.type.toUpperCase();
    button.append(number, label);
    button.addEventListener("click", () => selectCase(item));
    fragment.append(button);
  }
  grid.replaceChildren(fragment);
  document.querySelector("#case-count").textContent = `${cases.length} matched pairs`;
}

function updateFromPointer(event) {
  const rect = stage.getBoundingClientRect();
  setSplit(((event.clientX - rect.left) / rect.width) * 100);
}

stage.addEventListener("pointerdown", (event) => {
  if (event.button !== undefined && event.button !== 0) return;
  pointerId = event.pointerId;
  stage.setPointerCapture(pointerId);
  updateFromPointer(event);
});

stage.addEventListener("pointermove", (event) => {
  if (event.pointerId !== pointerId) return;
  if (dragFrame) cancelAnimationFrame(dragFrame);
  dragFrame = requestAnimationFrame(() => {
    updateFromPointer(event);
    dragFrame = 0;
  });
});

function finishDrag(event) {
  if (event.pointerId !== pointerId) return;
  pointerId = null;
  if (dragFrame) cancelAnimationFrame(dragFrame);
  dragFrame = 0;
}

stage.addEventListener("pointerup", finishDrag);
stage.addEventListener("pointercancel", finishDrag);
stage.addEventListener("lostpointercapture", () => { pointerId = null; });
stage.addEventListener("keydown", (event) => {
  if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
    event.preventDefault();
    setSplit(split + (event.key === "ArrowRight" ? 1 : -1));
  } else if (event.key === "Home") setSplit(0);
  else if (event.key === "End") setSplit(100);
});

for (const button of playButtons) button.addEventListener("click", togglePlayback);
if (detailZoomControl) {
  detailZoomControl.addEventListener("click", () => {
    detailZoomEnabled = !detailZoomEnabled;
    stage.classList.toggle("is-detail-zoomed", detailZoomEnabled);
    detailZoomControl.setAttribute("aria-pressed", String(detailZoomEnabled));
    detailZoomControl.textContent = detailZoomEnabled ? "返回完整画面" : "查看细节 · 2×";
  });
}
document.querySelector("#fullscreen-control").addEventListener("click", async () => {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await document.querySelector(".viewer-card").requestFullscreen();
  } catch (_) { statusMessage.textContent = "Fullscreen is not available in this browser."; }
});
window.addEventListener("resize", () => {
  if (selectedCase) fitStage(selectedCase.width, selectedCase.height);
});

timeline.addEventListener("input", () => {
  const duration = originalVideo.duration;
  if (!Number.isFinite(duration)) return;
  const time = (Number(timeline.value) / Number(timeline.max)) * duration;
  originalVideo.currentTime = time;
  refinedVideo.currentTime = Math.min(time, refinedVideo.duration || time);
  updateProgress();
});

originalVideo.addEventListener("loadedmetadata", () => onMetadata(originalVideo));
refinedVideo.addEventListener("loadedmetadata", () => onMetadata(refinedVideo));
originalVideo.addEventListener("timeupdate", updateProgress);
originalVideo.addEventListener("play", () => setPlayingUi(true));
refinedVideo.addEventListener("play", () => setPlayingUi(true));
originalVideo.addEventListener("pause", () => {
  if (refinedVideo && !refinedVideo.paused) refinedVideo.pause();
  clearSyncLoop();
  setPlayingUi(false);
});
refinedVideo.addEventListener("pause", () => {
  if (originalVideo && !originalVideo.paused) originalVideo.pause();
  clearSyncLoop();
  setPlayingUi(false);
});
originalVideo.addEventListener("waiting", () => loading.classList.remove("is-hidden"));
originalVideo.addEventListener("playing", hideLoading);
refinedVideo.addEventListener("playing", hideLoading);
for (const video of [originalVideo, refinedVideo]) video.addEventListener("error", () => {
  loading.classList.add("is-hidden");
  statusMessage.textContent = "A video could not be loaded. Check that both files are present in the videos folders.";
});

fetch(document.body.dataset.casesUrl || "data/cases.json")
  .then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  })
  .then((data) => {
    cases = data.cases;
    renderCaseButtons();
    if (cases.length) selectCase(cases[0]);
  })
  .catch((error) => {
    loading.classList.add("is-hidden");
    document.querySelector("#case-title").textContent = "Comparison manifest unavailable";
    statusMessage.textContent = "Run the local web server from this project folder and confirm data/cases.json exists.";
    console.error(error);
  });
