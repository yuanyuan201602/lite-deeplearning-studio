"use strict";

/* Lite DeepLearning Studio — data collection assistant page (self-contained). */

const state = JSON.parse(document.getElementById("collect-state").textContent);
const projectId = state.project.project_id;
const kind = state.dataset_kind;

/* ---------- helpers ---------- */

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function apiUpload(path, formData) {
  const response = await fetch(`/api/projects/${projectId}${path}`, {
    method: "POST",
    body: formData,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "上传失败，请重试。");
  return data;
}

async function apiJson(path, payload) {
  const response = await fetch(`/api/projects/${projectId}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "保存失败，请重试。");
  return data;
}

/* ---------- audio recording (WAV) — self-contained copy ---------- */

function writeWavString(view, offset, text) {
  for (let i = 0; i < text.length; i += 1) view.setUint8(offset + i, text.charCodeAt(i));
}

function encodeWav(samples, sampleRate) {
  const view = new DataView(new ArrayBuffer(44 + samples.length * 2));
  writeWavString(view, 0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeWavString(view, 8, "WAVE");
  writeWavString(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeWavString(view, 36, "data");
  view.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i += 1) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([view], { type: "audio/wav" });
}

function createWavRecorder() {
  let mediaStream = null;
  let audioContext = null;
  let source = null;
  let processor = null;
  let chunks = [];

  async function start() {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    source = audioContext.createMediaStreamSource(mediaStream);
    processor = audioContext.createScriptProcessor(4096, 1, 1);
    chunks = [];
    processor.onaudioprocess = (e) => chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    source.connect(processor);
    processor.connect(audioContext.destination);
  }

  function stop() {
    if (!audioContext) return null;
    processor.disconnect();
    source.disconnect();
    mediaStream.getTracks().forEach((t) => t.stop());
    const total = chunks.reduce((s, c) => s + c.length, 0);
    const merged = new Float32Array(total);
    let off = 0;
    for (const c of chunks) { merged.set(c, off); off += c.length; }
    const blob = encodeWav(merged, audioContext.sampleRate);
    audioContext.close();
    audioContext = null;
    return blob;
  }

  return { start, stop };
}

/* ---------- progress grid ---------- */

const MIN_RECOMMENDED = { image: 5, audio: 5, text: 5, sensor: 4, qa: 3 };

function renderProgress() {
  const grid = document.getElementById("progress-grid");
  if (!grid) return;
  grid.innerHTML = "";
  const dataset = state.dataset;
  const min = MIN_RECOMMENDED[kind] || 3;

  if (kind === "image" || kind === "audio") {
    const counts = dataset.class_counts || {};
    if (Object.keys(counts).length === 0) {
      grid.appendChild(el("p", "muted-note", "还没有任何类别。在下方选择类别后开始采集。"));
      return;
    }
    for (const [label, count] of Object.entries(counts)) {
      const badge = el("div", count >= min ? "collect-badge ready" : "collect-badge");
      badge.appendChild(el("div", "collect-badge-label", label));
      badge.appendChild(el("div", "collect-badge-count", `${count} 条${count >= min ? " ✓" : `（建议 ${min} 条以上）`}`));
      grid.appendChild(badge);
    }
  } else if (kind === "text") {
    const counts = dataset.class_counts || {};
    if (Object.keys(counts).length === 0) {
      grid.appendChild(el("p", "muted-note", "还没有任何类别。在下方输入文本后保存。"));
      return;
    }
    for (const [label, count] of Object.entries(counts)) {
      const badge = el("div", count >= min ? "collect-badge ready" : "collect-badge");
      badge.appendChild(el("div", "collect-badge-label", label));
      badge.appendChild(el("div", "collect-badge-count", `${count} 条${count >= min ? " ✓" : `（建议 ${min} 条以上）`}`));
      grid.appendChild(badge);
    }
  } else {
    const count = dataset.sample_count || 0;
    const badge = el("div", count >= min ? "collect-badge ready" : "collect-badge");
    const label = kind === "qa" ? "问答对" : "数据行";
    badge.appendChild(el("div", "collect-badge-label", `共 ${count} ${label}`));
    badge.appendChild(el("div", "collect-badge-count", count >= min ? "已达最低要求 ✓" : `建议至少 ${min} ${label}`));
    grid.appendChild(badge);
  }
}

function refreshDataset(newState) {
  if (newState && newState.dataset) Object.assign(state.dataset, newState.dataset);
  renderProgress();
}

/* ---------- image collector (webcam) ---------- */

function buildImageCollector() {
  const area = document.getElementById("collect-area");

  const classRow = el("div", "collect-class-row");
  const labelSelect = el("select", "input-field");
  const newLabelInput = el("input", "input-field");
  newLabelInput.placeholder = "输入新类别名称…";
  newLabelInput.maxLength = 40;
  classRow.appendChild(el("span", "", "当前类别："));
  classRow.appendChild(labelSelect);
  classRow.appendChild(el("span", "muted-note", "或新建："));
  classRow.appendChild(newLabelInput);

  function activeLabel() {
    return newLabelInput.value.trim() || labelSelect.value || "";
  }

  function refreshSelect() {
    const counts = state.dataset.class_counts || {};
    const current = labelSelect.value;
    labelSelect.innerHTML = "";
    const placeholder = el("option", "", "— 选择已有类别 —");
    placeholder.value = "";
    labelSelect.appendChild(placeholder);
    for (const label of Object.keys(counts)) {
      const opt = el("option", "", label);
      opt.value = label;
      labelSelect.appendChild(opt);
    }
    if (current) labelSelect.value = current;
  }
  refreshSelect();

  const webcamBox = el("div", "webcam-container");
  const video = document.createElement("video");
  video.className = "webcam-video";
  video.autoplay = true;
  video.playsInline = true;
  const canvas = document.createElement("canvas");
  canvas.className = "webcam-canvas";
  canvas.width = 640;
  canvas.height = 480;
  webcamBox.appendChild(video);

  const snapBtn = el("button", "btn-primary", "拍照");
  snapBtn.type = "button";
  const statusLine = el("p", "status-text", "");
  webcamBox.appendChild(snapBtn);
  webcamBox.appendChild(statusLine);

  let stream = null;
  navigator.mediaDevices.getUserMedia({ video: true }).then((s) => {
    stream = s;
    video.srcObject = s;
  }).catch(() => {
    statusLine.textContent = "无法使用摄像头：请允许浏览器使用摄像头，或改用直接上传图片。";
    statusLine.className = "status-text status-error";
    snapBtn.disabled = true;
  });

  snapBtn.addEventListener("click", async () => {
    const label = activeLabel();
    if (!label) { statusLine.textContent = "请先选择或输入类别名称。"; return; }
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, 640, 480);
    canvas.toBlob(async (blob) => {
      if (!blob) return;
      const fd = new FormData();
      fd.append("label", label);
      fd.append("files", new File([blob], `capture_${Date.now()}.jpg`, { type: "image/jpeg" }));
      snapBtn.disabled = true;
      try {
        const next = await apiUpload("/data/images", fd);
        refreshDataset(next);
        refreshSelect();
        if (newLabelInput.value.trim()) {
          labelSelect.value = label;
          newLabelInput.value = "";
        }
        const count = (state.dataset.class_counts || {})[label] || 0;
        statusLine.textContent = `已保存！"${label}" 共 ${count} 张。`;
        statusLine.className = "status-text status-ok";
      } catch (e) {
        statusLine.textContent = e.message;
        statusLine.className = "status-text status-error";
      } finally {
        snapBtn.disabled = false;
      }
    }, "image/jpeg", 0.85);
  });

  const uploadRow = el("div", "collect-class-row");
  const fileInput = document.createElement("input");
  fileInput.type = "file";
  fileInput.accept = "image/*";
  fileInput.multiple = true;
  fileInput.className = "file-input";
  const uploadBtn = el("button", "btn-secondary", "上传图片文件");
  uploadBtn.type = "button";
  const uploadStatus = el("span", "status-text", "");
  uploadBtn.addEventListener("click", async () => {
    const label = activeLabel();
    if (!label) { uploadStatus.textContent = "请先选择或输入类别名称。"; return; }
    if (!fileInput.files.length) { uploadStatus.textContent = "请先选择图片文件。"; return; }
    const fd = new FormData();
    fd.append("label", label);
    for (const f of fileInput.files) fd.append("files", f);
    uploadBtn.disabled = true;
    try {
      const next = await apiUpload("/data/images", fd);
      refreshDataset(next);
      refreshSelect();
      uploadStatus.textContent = `已上传 ${fileInput.files.length} 张。`;
      uploadStatus.className = "status-text status-ok";
      fileInput.value = "";
    } catch (e) {
      uploadStatus.textContent = e.message;
      uploadStatus.className = "status-text status-error";
    } finally {
      uploadBtn.disabled = false;
    }
  });
  uploadRow.appendChild(el("span", "muted-note", "或："));
  uploadRow.appendChild(fileInput);
  uploadRow.appendChild(uploadBtn);
  uploadRow.appendChild(uploadStatus);

  area.innerHTML = "";
  area.appendChild(el("h2", "", "图像采集"));
  area.appendChild(el("p", "panel-hint", '对准拍摄对象，选择类别后点击"拍照"。每次拍摄自动上传到该类别。'));
  area.appendChild(classRow);
  area.appendChild(webcamBox);
  area.appendChild(canvas);
  area.appendChild(uploadRow);
}

/* ---------- audio collector (microphone) ---------- */

function buildAudioCollector() {
  const area = document.getElementById("collect-area");

  const classRow = el("div", "collect-class-row");
  const labelSelect = el("select", "input-field");
  const newLabelInput = el("input", "input-field");
  newLabelInput.placeholder = "输入新类别名称…";
  newLabelInput.maxLength = 40;
  classRow.appendChild(el("span", "", "当前类别："));
  classRow.appendChild(labelSelect);
  classRow.appendChild(el("span", "muted-note", "或新建："));
  classRow.appendChild(newLabelInput);

  function activeLabel() {
    return newLabelInput.value.trim() || labelSelect.value || "";
  }

  function refreshSelect() {
    const counts = state.dataset.class_counts || {};
    const current = labelSelect.value;
    labelSelect.innerHTML = "";
    const placeholder = el("option", "", "— 选择已有类别 —");
    placeholder.value = "";
    labelSelect.appendChild(placeholder);
    for (const label of Object.keys(counts)) {
      const opt = el("option", "", label);
      opt.value = label;
      labelSelect.appendChild(opt);
    }
    if (current) labelSelect.value = current;
  }
  refreshSelect();

  const statusLine = el("p", "status-text", "");

  let recorder = null;
  const recBtn = el("button", "btn-secondary", "按住录音");
  recBtn.type = "button";
  recBtn.addEventListener("click", async () => {
    if (recorder) {
      const blob = recorder.stop();
      recorder = null;
      recBtn.textContent = "按住录音";
      recBtn.classList.remove("recording");
      if (!blob) return;
      const label = activeLabel();
      if (!label) { statusLine.textContent = "请先选择或输入类别名称。"; return; }
      const fd = new FormData();
      fd.append("label", label);
      fd.append("files", new File([blob], `rec_${Date.now()}.wav`, { type: "audio/wav" }));
      recBtn.disabled = true;
      try {
        const next = await apiUpload("/data/audio", fd);
        refreshDataset(next);
        refreshSelect();
        if (newLabelInput.value.trim()) { labelSelect.value = label; newLabelInput.value = ""; }
        const count = (state.dataset.class_counts || {})[label] || 0;
        statusLine.textContent = `已保存！"${label}" 共 ${count} 段。`;
        statusLine.className = "status-text status-ok";
      } catch (e) {
        statusLine.textContent = e.message;
        statusLine.className = "status-text status-error";
      } finally {
        recBtn.disabled = false;
      }
      return;
    }
    try {
      const next = createWavRecorder();
      await next.start();
      recorder = next;
      recBtn.textContent = "■ 停止录音";
      recBtn.classList.add("recording");
      statusLine.textContent = "正在录音…";
      statusLine.className = "status-text";
    } catch {
      statusLine.textContent = "无法使用麦克风：请允许浏览器使用麦克风，或改用上传文件。";
      statusLine.className = "status-text status-error";
    }
  });

  const uploadRow = el("div", "collect-class-row");
  const fileInput = document.createElement("input");
  fileInput.type = "file";
  fileInput.accept = ".wav,audio/wav";
  fileInput.multiple = true;
  fileInput.className = "file-input";
  const uploadBtn = el("button", "btn-secondary", "上传 WAV 文件");
  uploadBtn.type = "button";
  const uploadStatus = el("span", "status-text", "");
  uploadBtn.addEventListener("click", async () => {
    const label = activeLabel();
    if (!label) { uploadStatus.textContent = "请先选择或输入类别名称。"; return; }
    if (!fileInput.files.length) { uploadStatus.textContent = "请先选择 WAV 文件。"; return; }
    const fd = new FormData();
    fd.append("label", label);
    for (const f of fileInput.files) fd.append("files", f);
    uploadBtn.disabled = true;
    try {
      const next = await apiUpload("/data/audio", fd);
      refreshDataset(next);
      refreshSelect();
      uploadStatus.textContent = `已上传 ${fileInput.files.length} 段。`;
      uploadStatus.className = "status-text status-ok";
      fileInput.value = "";
    } catch (e) {
      uploadStatus.textContent = e.message;
      uploadStatus.className = "status-text status-error";
    } finally {
      uploadBtn.disabled = false;
    }
  });
  uploadRow.appendChild(el("span", "muted-note", "或："));
  uploadRow.appendChild(fileInput);
  uploadRow.appendChild(uploadBtn);
  uploadRow.appendChild(uploadStatus);

  area.innerHTML = "";
  area.appendChild(el("h2", "", "音频采集"));
  area.appendChild(el("p", "panel-hint", "选择类别后点击录音，录完再点一次停止，自动上传。"));
  area.appendChild(classRow);
  const recRow = el("div", "collect-class-row");
  recRow.appendChild(recBtn);
  recRow.appendChild(statusLine);
  area.appendChild(recRow);
  area.appendChild(uploadRow);
}

/* ---------- text collector ---------- */

function buildTextCollector() {
  const area = document.getElementById("collect-area");
  const localSamples = [];

  const classRow = el("div", "collect-class-row");
  const labelInput = el("input", "input-field");
  labelInput.placeholder = "类别名称（如：高兴、悲伤）";
  labelInput.maxLength = 40;
  classRow.appendChild(el("label", "", "类别名称："));
  classRow.appendChild(labelInput);

  const inputRow = el("div", "collect-class-row");
  const textInput = el("input", "input-field");
  textInput.placeholder = "输入一句话，然后点击添加…";
  textInput.maxLength = 500;
  textInput.style.flex = "1";
  const addBtn = el("button", "btn-secondary", "添加");
  addBtn.type = "button";
  const addStatus = el("span", "status-text", "");
  inputRow.appendChild(textInput);
  inputRow.appendChild(addBtn);
  inputRow.appendChild(addStatus);

  const preview = el("div", "collect-text-preview");
  const previewTitle = el("p", "panel-hint", "本次新增（0 条）");

  function refreshPreview() {
    preview.innerHTML = "";
    const counts = {};
    for (const s of localSamples) counts[s.label] = (counts[s.label] || 0) + 1;
    const lines = Object.entries(counts).map(([l, n]) => `${l}：${n} 条`).join("　");
    previewTitle.textContent = `本次新增（${localSamples.length} 条）${lines ? "  —  " + lines : ""}`;
    for (const s of localSamples.slice(-10)) {
      const row = el("div", "collect-pair");
      row.appendChild(el("span", "pack-tag", s.label));
      row.appendChild(el("span", "", "  " + s.text));
      preview.appendChild(row);
    }
    if (localSamples.length > 10) {
      preview.prepend(el("p", "muted-note", `…还有 ${localSamples.length - 10} 条未显示`));
    }
  }

  addBtn.addEventListener("click", () => {
    const label = labelInput.value.trim();
    const text = textInput.value.trim();
    if (!label) { addStatus.textContent = "请先填写类别名称。"; return; }
    if (!text) { addStatus.textContent = "请输入文本内容。"; return; }
    localSamples.push({ text, label });
    textInput.value = "";
    addStatus.textContent = "";
    refreshPreview();
  });
  textInput.addEventListener("keydown", (e) => { if (e.key === "Enter") addBtn.click(); });

  const saveBtn = el("button", "btn-primary", "保存全部到项目");
  saveBtn.type = "button";
  const saveStatus = el("p", "status-text", "");
  saveBtn.addEventListener("click", async () => {
    if (!localSamples.length) { saveStatus.textContent = "还没有添加任何文本。"; return; }
    saveBtn.disabled = true;
    try {
      const existing = (state.dataset.samples || []);
      const next = await apiJson("/data/text", { samples: [...existing, ...localSamples] });
      refreshDataset(next);
      localSamples.length = 0;
      refreshPreview();
      saveStatus.textContent = `已保存！项目中共 ${state.dataset.sample_count} 条文本。`;
      saveStatus.className = "status-text status-ok";
    } catch (e) {
      saveStatus.textContent = e.message;
      saveStatus.className = "status-text status-error";
    } finally {
      saveBtn.disabled = false;
    }
  });

  area.innerHTML = "";
  area.appendChild(el("h2", "", "文本采集"));
  area.appendChild(el("p", "panel-hint", '逐条输入文本并添加到对应类别，最后点击"保存全部"写入项目。'));
  area.appendChild(classRow);
  area.appendChild(inputRow);
  area.appendChild(previewTitle);
  area.appendChild(preview);
  area.appendChild(saveBtn);
  area.appendChild(saveStatus);
}

/* ---------- sensor collector ---------- */

function buildSensorCollector() {
  const area = document.getElementById("collect-area");
  const existing = state.dataset.csv || "";
  const existingCols = state.dataset.columns || [];

  const guidance = el("div", "collect-guidance");
  guidance.innerHTML = `<strong>CSV 格式要求</strong><br>
第一行为表头（最后一列是决策动作），后续每行一条数据。<br>
<br>示例：<br>
<code>temperature,heart_rate,action</code><br>
<code>36.5,75,正常</code><br>
<code>38.0,110,请就医</code><br>
<br>至少需要 2 种动作、4 行数据。列名和动作名可以用中文。`;

  const textarea = el("textarea", "big-textarea mono");
  textarea.rows = 14;
  textarea.placeholder = "在此粘贴或输入 CSV 数据…";
  textarea.value = existing;

  if (existingCols.length) {
    const hint = el("p", "panel-hint", `当前项目已有列：${existingCols.join("，")}`);
    area.appendChild(hint);
  }

  const saveBtn = el("button", "btn-primary", "保存 CSV 到项目");
  saveBtn.type = "button";
  const saveStatus = el("p", "status-text", "");
  saveBtn.addEventListener("click", async () => {
    const csv = textarea.value.trim();
    if (!csv) { saveStatus.textContent = "请先输入 CSV 数据。"; return; }
    saveBtn.disabled = true;
    try {
      const next = await apiJson("/data/sensor", { csv });
      refreshDataset(next);
      saveStatus.textContent = `已保存！共 ${state.dataset.sample_count} 行数据。`;
      saveStatus.className = "status-text status-ok";
    } catch (e) {
      saveStatus.textContent = e.message;
      saveStatus.className = "status-text status-error";
    } finally {
      saveBtn.disabled = false;
    }
  });

  area.innerHTML = "";
  area.appendChild(el("h2", "", "传感器数据采集"));
  area.appendChild(guidance);
  area.appendChild(textarea);
  area.appendChild(saveBtn);
  area.appendChild(saveStatus);
}

/* ---------- QA collector ---------- */

function buildQaCollector() {
  const area = document.getElementById("collect-area");
  const localPairs = [];

  const pairsContainer = el("div", "");

  function addPairRow(q = "", a = "") {
    const idx = localPairs.length;
    localPairs.push({ question: q, answer: a });
    const wrap = el("div", "collect-pair");
    const qLabel = el("label", "", `问题 ${idx + 1}`);
    const qInput = el("input", "input-field");
    qInput.value = q;
    qInput.placeholder = "输入问题…";
    qInput.maxLength = 500;
    qInput.addEventListener("input", () => { localPairs[idx].question = qInput.value.trim(); });
    const aLabel = el("label", "", `回答 ${idx + 1}`);
    const aInput = el("textarea", "input-field");
    aInput.rows = 2;
    aInput.value = a;
    aInput.placeholder = "输入回答…";
    aInput.maxLength = 2000;
    aInput.addEventListener("input", () => { localPairs[idx].answer = aInput.value.trim(); });
    wrap.appendChild(qLabel);
    wrap.appendChild(qInput);
    wrap.appendChild(aLabel);
    wrap.appendChild(aInput);
    pairsContainer.appendChild(wrap);
  }

  const addBtn = el("button", "btn-secondary", "添加一组问答");
  addBtn.type = "button";
  addBtn.addEventListener("click", () => addPairRow());

  const saveBtn = el("button", "btn-primary", "保存全部到项目");
  saveBtn.type = "button";
  const saveStatus = el("p", "status-text", "");
  saveBtn.addEventListener("click", async () => {
    const toSave = localPairs.filter((p) => p.question && p.answer);
    if (!toSave.length) { saveStatus.textContent = "还没有填写完整的问答对。"; return; }
    saveBtn.disabled = true;
    try {
      const existing = (state.dataset.pairs || []);
      const next = await apiJson("/data/qa", { pairs: [...existing, ...toSave] });
      refreshDataset(next);
      localPairs.length = 0;
      pairsContainer.innerHTML = "";
      saveStatus.textContent = `已保存！项目中共 ${state.dataset.sample_count} 组问答。`;
      saveStatus.className = "status-text status-ok";
    } catch (e) {
      saveStatus.textContent = e.message;
      saveStatus.className = "status-text status-error";
    } finally {
      saveBtn.disabled = false;
    }
  });

  addPairRow();
  addPairRow();

  area.innerHTML = "";
  area.appendChild(el("h2", "", "问答采集"));
  area.appendChild(el("p", "panel-hint", '填写问题和对应回答，点击"添加"可继续新增，最后统一保存到项目。'));
  area.appendChild(pairsContainer);
  const addRow = el("div", "collect-class-row");
  addRow.appendChild(addBtn);
  area.appendChild(addRow);
  area.appendChild(saveBtn);
  area.appendChild(saveStatus);
}

/* ---------- init ---------- */

renderProgress();

if (kind === "image") buildImageCollector();
else if (kind === "audio") buildAudioCollector();
else if (kind === "text") buildTextCollector();
else if (kind === "sensor") buildSensorCollector();
else if (kind === "qa") buildQaCollector();
else {
  const area = document.getElementById("collect-area");
  area.appendChild(el("p", "muted-note", `当前任务类型（${kind}）暂不支持在此页面采集，请返回项目页面直接编辑数据。`));
}
