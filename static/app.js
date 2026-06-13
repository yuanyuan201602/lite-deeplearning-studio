"use strict";

/* Lite DeepLearning Studio — project workflow page logic. */

const state = JSON.parse(document.getElementById("initial-state").textContent);
const projectId = state.project.project_id;
const kind = state.dataset_kind;
const capability = state.capability;

const stepsDone = {
  0: (state.dataset.sample_count || 0) > 0,
  1: Boolean(state.project.train_report),
  2: false,
  3: Boolean(state.project.export_file),
};

/* ---------- helpers ---------- */

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function api(path, options = {}) {
  const response = await fetch(`/api/projects/${projectId}${path}`, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "操作失败，请重试。");
  }
  return data;
}

async function postJson(path, payload) {
  return api(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

function setStatus(id, message, isError) {
  const node = document.getElementById(id);
  node.textContent = message;
  node.classList.toggle("status-error", Boolean(isError));
  node.classList.toggle("status-ok", !isError && Boolean(message));
}

function percent(value) {
  return `${Math.round(value * 1000) / 10}%`;
}

function scoreBars(scores) {
  const wrap = el("div", "score-bars");
  const entries = Object.entries(scores).sort((a, b) => b[1] - a[1]);
  for (const [label, score] of entries) {
    const row = el("div", "score-row");
    row.appendChild(el("span", "score-label", label));
    const track = el("div", "score-track");
    const fill = el("div", "score-fill");
    fill.style.width = `${Math.max(2, score * 100)}%`;
    track.appendChild(fill);
    row.appendChild(track);
    row.appendChild(el("span", "score-value", percent(score)));
    wrap.appendChild(row);
  }
  return wrap;
}

/* ---------- audio recording (WAV) ---------- */

function writeWavString(view, offset, text) {
  for (let i = 0; i < text.length; i += 1) {
    view.setUint8(offset + i, text.charCodeAt(i));
  }
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
    const sample = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(44 + i * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
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
    processor.onaudioprocess = (event) => {
      chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
    };
    source.connect(processor);
    processor.connect(audioContext.destination);
  }

  function stop() {
    if (!audioContext) return null;
    processor.disconnect();
    source.disconnect();
    mediaStream.getTracks().forEach((track) => track.stop());
    const total = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
    const merged = new Float32Array(total);
    let offset = 0;
    for (const chunk of chunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }
    const blob = encodeWav(merged, audioContext.sampleRate);
    audioContext.close();
    audioContext = null;
    return blob;
  }

  return { start, stop };
}

const MIC_ERROR_MESSAGE = "无法使用麦克风：请允许浏览器使用麦克风，或改用上传 WAV 文件。";

function recorderButton(idleText, onClip, onError) {
  const button = el("button", "btn-secondary", idleText);
  button.type = "button";
  let recorder = null;
  button.addEventListener("click", async () => {
    if (recorder) {
      const blob = recorder.stop();
      recorder = null;
      button.textContent = idleText;
      button.classList.remove("recording");
      if (blob) onClip(blob);
      return;
    }
    try {
      const next = createWavRecorder();
      await next.start();
      recorder = next;
      button.textContent = "■ 停止录音";
      button.classList.add("recording");
    } catch (error) {
      recorder = null;
      onError(MIC_ERROR_MESSAGE);
    }
  });
  return button;
}

/* ---------- stepper ---------- */

const stepButtons = Array.from(document.querySelectorAll("#stepper .step"));

function showStep(index) {
  stepButtons.forEach((button, i) => {
    button.classList.toggle("step-active", i === index);
    document.getElementById(`panel-${i}`).hidden = i !== index;
  });
}

function isStepUnlocked(index) {
  if (index === 0) return true;
  return stepsDone[index - 1] || stepsDone[index];
}

function refreshLocks() {
  stepButtons.forEach((button, i) => {
    button.classList.toggle("step-locked", !isStepUnlocked(i));
  });
}

function refreshChecks() {
  stepButtons.forEach((button, i) => {
    button.querySelector(".step-check").hidden = !stepsDone[i];
  });
  refreshLocks();
  refreshTrainWarning();
}

stepButtons.forEach((button, index) => {
  button.addEventListener("click", () => {
    if (isStepUnlocked(index)) showStep(index);
  });
});

/* ---------- data editors ---------- */

const dataEditor = document.getElementById("data-editor");
const dataHint = document.getElementById("data-hint");
const saveButton = document.getElementById("save-data");

function groupSamplesByLabel(samples) {
  const groups = new Map();
  for (const sample of samples || []) {
    if (!groups.has(sample.label)) groups.set(sample.label, []);
    groups.get(sample.label).push(sample.text);
  }
  return groups;
}

function addClassBlock(container, label, lines, placeholder) {
  const block = el("div", "class-block");
  const head = el("div", "class-head");
  const labelInput = el("input", "class-label-input");
  labelInput.value = label || "";
  labelInput.placeholder = "类别名称，例如：传统戏剧";
  labelInput.maxLength = 40;
  const removeButton = el("button", "btn-ghost", "删除类别");
  removeButton.type = "button";
  removeButton.addEventListener("click", () => block.remove());
  head.appendChild(labelInput);
  head.appendChild(removeButton);
  const textarea = el("textarea", "class-samples");
  textarea.rows = 5;
  textarea.placeholder = placeholder;
  textarea.value = (lines || []).join("\n");
  block.appendChild(head);
  block.appendChild(textarea);
  container.appendChild(block);
}

/* ---------- sample pack modal ---------- */

function openPackModal() {
  const overlay = el("div", "modal-overlay");
  const dialog = el("div", "modal-dialog");

  const header = el("div", "modal-header");
  header.appendChild(el("h3", "", "加载样本数据包"));
  const closeBtn = el("button", "modal-close", "×");
  closeBtn.type = "button";
  closeBtn.addEventListener("click", () => overlay.remove());
  overlay.addEventListener("click", (e) => { if (e.target === overlay) overlay.remove(); });
  header.appendChild(closeBtn);
  dialog.appendChild(header);

  const grid = el("div", "pack-grid");
  const loading = el("p", "pack-empty", "正在加载…");
  dialog.appendChild(loading);
  dialog.appendChild(grid);
  overlay.appendChild(dialog);
  document.body.appendChild(overlay);

  fetch("/api/data-packs")
    .then((r) => r.json())
    .then((packs) => {
      loading.remove();
      const filtered = packs.filter(
        (p) =>
          p.capability === capability &&
          p.dataset_kind !== "image" &&
          p.dataset_kind !== "audio"
      );
      if (!filtered.length) {
        grid.appendChild(el("p", "pack-empty", "暂无适合当前任务的样本包。"));
        return;
      }
      for (const pack of filtered) {
        const card = el("div", "pack-card");
        card.appendChild(el("h4", "", pack.name));
        card.appendChild(el("p", "", pack.description));
        const tags = el("div", "");
        for (const tag of pack.tags) tags.appendChild(el("span", "pack-tag", tag));
        if (pack.sample_count) tags.appendChild(el("span", "pack-tag", `${pack.sample_count} 条`));
        card.appendChild(tags);
        card.addEventListener("click", async () => {
          card.style.opacity = "0.6";
          card.style.pointerEvents = "none";
          try {
            const next = await postJson("/data/pack", { pack_file: pack.file });
            Object.assign(state, next);
            overlay.remove();
            dataEditor.innerHTML = "";
            editors[kind]();
            afterDataSaved(`已加载「${pack.name}」。可继续添加自己的数据。`);
          } catch (err) {
            card.style.opacity = "";
            card.style.pointerEvents = "";
            setStatus("data-status", err.message, true);
          }
        });
        grid.appendChild(card);
      }
    })
    .catch(() => { loading.textContent = "加载失败，请重试。"; });
}

function packButton() {
  const btn = el("button", "btn-ghost", "加载样本包");
  btn.type = "button";
  btn.addEventListener("click", openPackModal);
  return btn;
}

function collectLink() {
  const a = document.createElement("a");
  a.className = "btn-ghost";
  a.textContent = "前往采集助手（摄像头/麦克风）→";
  a.href = `/collect/${projectId}`;
  return a;
}

function buildTextEditor() {
  dataHint.textContent =
    "给每个类别起名字，再粘贴这个类别的例句，每行一句。每个类别至少 2 句，越多越准。";
  const container = el("div", "class-list");
  const groups = groupSamplesByLabel(state.dataset.samples);
  if (groups.size === 0) {
    addClassBlock(container, "", [], "每行一句例句，例如：昆曲 唱腔 舞台 表演");
    addClassBlock(container, "", [], "每行一句例句");
  } else {
    for (const [label, lines] of groups) {
      addClassBlock(container, label, lines, "每行一句例句");
    }
  }
  const addButton = el("button", "btn-secondary", "添加类别");
  addButton.type = "button";
  addButton.addEventListener("click", () =>
    addClassBlock(container, "", [], "每行一句例句")
  );
  dataEditor.appendChild(container);
  dataEditor.appendChild(addButton);

  saveButton.addEventListener("click", async () => {
    const samples = [];
    for (const block of container.querySelectorAll(".class-block")) {
      const label = block.querySelector(".class-label-input").value.trim();
      const lines = block
        .querySelector(".class-samples")
        .value.split("\n")
        .map((line) => line.trim())
        .filter(Boolean);
      for (const text of lines) samples.push({ text, label });
    }
    await saveData(() => postJson("/data/text", { samples }));
  });
  dataEditor.appendChild(packButton());
}

function buildQaEditor() {
  dataHint.textContent =
    "每行一组问答，用“|”隔开问题和答案，例如：什么是非遗|非遗是世代相传的传统文化。至少 3 组。";
  const textarea = el("textarea", "big-textarea");
  textarea.rows = 10;
  textarea.placeholder = "什么是非遗|非遗是世代相传的传统文化表现形式。\n为什么要保护非遗|保护非遗有助于传承文化记忆。";
  textarea.value = (state.dataset.pairs || [])
    .map((pair) => `${pair.question}|${pair.answer}`)
    .join("\n");
  dataEditor.appendChild(textarea);

  saveButton.addEventListener("click", async () => {
    const pairs = textarea.value
      .split("\n")
      .map((line) => line.replace("｜", "|"))
      .filter((line) => line.includes("|"))
      .map((line) => {
        const index = line.indexOf("|");
        return { question: line.slice(0, index).trim(), answer: line.slice(index + 1).trim() };
      });
    await saveData(() => postJson("/data/qa", { pairs }));
  });
  dataEditor.appendChild(packButton());
}

function buildSensorEditor() {
  dataHint.textContent =
    "粘贴表格数据：第一行是列名，最后一列是动作，其余列是传感器数字。至少 4 行数据。";
  const textarea = el("textarea", "big-textarea mono");
  textarea.rows = 10;
  textarea.placeholder = "temperature,distance,action\n38.6,12,提醒就诊\n36.5,30,继续观察";
  textarea.value = state.dataset.csv || "";
  dataEditor.appendChild(textarea);

  saveButton.addEventListener("click", async () => {
    await saveData(() => postJson("/data/sensor", { csv: textarea.value }));
  });
  dataEditor.appendChild(packButton());
}

function buildOcrEditor() {
  dataHint.textContent = "输入知识卡片上的正确文字。可以再粘贴一条拍照识别的文字做练习样例。";
  const correctLabel = el("label", "field-label", "正确文字（必填）");
  const correct = el("textarea", "big-textarea");
  correct.rows = 3;
  correct.placeholder = "例如：保护为主抢救第一";
  correct.value = state.dataset.correct_text || "";
  const observedLabel = el("label", "field-label", "识别出的文字样例（选填）");
  const observed = el("textarea", "big-textarea");
  observed.rows = 3;
  observed.placeholder = "例如：保护为王抢救第一";
  observed.value = state.dataset.observed_sample || "";
  dataEditor.append(correctLabel, correct, observedLabel, observed);

  saveButton.addEventListener("click", async () => {
    await saveData(() =>
      postJson("/data/ocr", {
        correct_text: correct.value,
        observed_sample: observed.value,
      })
    );
  });
}

function buildImageEditor() {
  dataHint.textContent =
    "给每个类别起名字并上传图片，每类至少 2 张，建议 5 张以上。支持 PNG / JPG。";
  saveButton.hidden = true;
  const container = el("div", "class-list");
  dataEditor.appendChild(container);

  function renderImageClasses() {
    container.innerHTML = "";
    const counts = state.dataset.class_counts || {};
    for (const [label, count] of Object.entries(counts)) {
      container.appendChild(imageClassBlock(label, count));
    }
  }

  function imageClassBlock(label, count) {
    const block = el("div", "class-block");
    const head = el("div", "class-head");
    head.appendChild(el("strong", "", label));
    head.appendChild(el("span", "img-count", `${count} 张图片`));
    const removeButton = el("button", "btn-ghost", "删除类别");
    removeButton.type = "button";
    removeButton.addEventListener("click", async () => {
      try {
        const next = await postJson("/data/images/remove", { label });
        Object.assign(state, next);
        renderImageClasses();
        afterDataSaved("已删除类别。");
      } catch (error) {
        setStatus("data-status", error.message, true);
      }
    });
    head.appendChild(removeButton);
    block.appendChild(head);
    block.appendChild(uploadRow(label));
    return block;
  }

  function uploadRow(label) {
    const row = el("div", "upload-row");
    const fileInput = el("input");
    fileInput.type = "file";
    fileInput.multiple = true;
    fileInput.accept = "image/*";
    const uploadButton = el("button", "btn-secondary", "上传到这个类别");
    uploadButton.type = "button";
    uploadButton.addEventListener("click", () => uploadImages(label, fileInput));
    row.append(fileInput, uploadButton);
    return row;
  }

  async function uploadImages(label, fileInput) {
    if (!fileInput.files.length) {
      setStatus("data-status", "请先选择图片文件。", true);
      return;
    }
    const form = new FormData();
    form.append("label", label);
    for (const file of fileInput.files) form.append("files", file);
    try {
      const next = await api("/data/images", { method: "POST", body: form });
      Object.assign(state, next);
      renderImageClasses();
      afterDataSaved(`已上传 ${next.saved} 张图片。`);
    } catch (error) {
      setStatus("data-status", error.message, true);
    }
  }

  const newRow = el("div", "new-class-row");
  const newLabel = el("input", "class-label-input");
  newLabel.placeholder = "新类别名称，例如：红色卡片";
  newLabel.maxLength = 40;
  const newFiles = el("input");
  newFiles.type = "file";
  newFiles.multiple = true;
  newFiles.accept = "image/*";
  const addButton = el("button", "btn-secondary", "添加类别并上传");
  addButton.type = "button";
  addButton.addEventListener("click", async () => {
    const label = newLabel.value.trim();
    if (!label) {
      setStatus("data-status", "请先填写类别名称。", true);
      return;
    }
    await uploadImages(label, newFiles);
    newLabel.value = "";
    newFiles.value = "";
  });
  newRow.append(newLabel, newFiles, addButton);
  dataEditor.appendChild(newRow);
  dataEditor.appendChild(collectLink());

  renderImageClasses();
}

function buildAudioEditor() {
  dataHint.textContent =
    "给每个类别起名字，用「录一段声音」按钮录音（录完自动保存），每类至少 2 段。也可以上传 WAV 文件。";
  saveButton.hidden = true;
  const container = el("div", "class-list");
  dataEditor.appendChild(container);

  function renderAudioClasses() {
    container.innerHTML = "";
    const counts = state.dataset.class_counts || {};
    for (const [label, count] of Object.entries(counts)) {
      container.appendChild(audioClassBlock(label, count));
    }
  }

  function audioClassBlock(label, count) {
    const block = el("div", "class-block");
    const head = el("div", "class-head");
    head.appendChild(el("strong", "", label));
    head.appendChild(el("span", "img-count", `${count} 段声音`));
    const removeButton = el("button", "btn-ghost", "删除类别");
    removeButton.type = "button";
    removeButton.addEventListener("click", async () => {
      try {
        const next = await postJson("/data/audio/remove", { label });
        Object.assign(state, next);
        renderAudioClasses();
        afterDataSaved("已删除类别。");
      } catch (error) {
        setStatus("data-status", error.message, true);
      }
    });
    head.appendChild(removeButton);
    block.appendChild(head);
    block.appendChild(audioUploadRow(label));
    return block;
  }

  function audioUploadRow(label) {
    const row = el("div", "upload-row");
    const record = recorderButton(
      "🎙 录一段声音",
      (blob) => uploadAudio(label, [blob]),
      (message) => setStatus("data-status", message, true)
    );
    const fileInput = el("input");
    fileInput.type = "file";
    fileInput.multiple = true;
    fileInput.accept = ".wav,audio/wav";
    const uploadButton = el("button", "btn-secondary", "上传到这个类别");
    uploadButton.type = "button";
    uploadButton.addEventListener("click", () => {
      if (!fileInput.files.length) {
        setStatus("data-status", "请先选择 WAV 文件。", true);
        return;
      }
      uploadAudio(label, Array.from(fileInput.files));
      fileInput.value = "";
    });
    row.append(record, fileInput, uploadButton);
    return row;
  }

  async function uploadAudio(label, clips) {
    const form = new FormData();
    form.append("label", label);
    for (const clip of clips) form.append("files", clip, clip.name || "clip.wav");
    try {
      const next = await api("/data/audio", { method: "POST", body: form });
      Object.assign(state, next);
      renderAudioClasses();
      afterDataSaved(`已保存 ${next.saved} 段声音。`);
    } catch (error) {
      setStatus("data-status", error.message, true);
    }
  }

  const newRow = el("div", "new-class-row");
  const newLabel = el("input", "class-label-input");
  newLabel.placeholder = "新类别名称，例如：拍手声";
  newLabel.maxLength = 40;
  const newRecord = recorderButton(
    "🎙 录音并添加类别",
    (blob) => {
      const label = newLabel.value.trim();
      if (!label) {
        setStatus("data-status", "请先填写类别名称。", true);
        return;
      }
      uploadAudio(label, [blob]).then(() => {
        newLabel.value = "";
      });
    },
    (message) => setStatus("data-status", message, true)
  );
  const newFiles = el("input");
  newFiles.type = "file";
  newFiles.multiple = true;
  newFiles.accept = ".wav,audio/wav";
  const addButton = el("button", "btn-secondary", "添加类别并上传");
  addButton.type = "button";
  addButton.addEventListener("click", async () => {
    const label = newLabel.value.trim();
    if (!label) {
      setStatus("data-status", "请先填写类别名称。", true);
      return;
    }
    if (!newFiles.files.length) {
      setStatus("data-status", "请先选择 WAV 文件，或用录音按钮。", true);
      return;
    }
    await uploadAudio(label, Array.from(newFiles.files));
    newLabel.value = "";
    newFiles.value = "";
  });
  newRow.append(newLabel, newRecord, newFiles, addButton);
  dataEditor.appendChild(newRow);
  dataEditor.appendChild(collectLink());

  renderAudioClasses();
}

async function saveData(action) {
  try {
    const next = await action();
    Object.assign(state, next);
    afterDataSaved("已保存。");
  } catch (error) {
    setStatus("data-status", error.message, true);
  }
}

function afterDataSaved(message) {
  stepsDone[0] = (state.dataset.sample_count || 0) > 0;
  refreshChecks();
  const suffix = stepsDone[0] ? " 现在可以去第 2 步训练了。" : "";
  setStatus("data-status", message + suffix, false);
}

/* ---------- training ---------- */

const trainButton = document.getElementById("train-button");
const compareButton = document.getElementById("compare-button");
const compareResult = document.getElementById("compare-result");
const trainReport = document.getElementById("train-report");
const trainLog = document.getElementById("train-log");
const modelPicker = document.getElementById("model-picker");
let selectedClassifier = "";

/* 数据量预警：样本太少时在训练面板提示 */
const MIN_PER_CLASS = 10;
const MIN_TOTAL = 20;
const trainWarning = el("p", "train-warning");
trainWarning.hidden = true;
document.querySelector("#panel-1 .panel-head").appendChild(trainWarning);

function refreshTrainWarning() {
  const total = state.dataset.sample_count || 0;
  if (total === 0 || capability === "ocr_typo_checker") {
    trainWarning.hidden = true;
    return;
  }
  const counts = state.dataset.class_counts || {};
  const thin = Object.entries(counts).filter(([, n]) => n < MIN_PER_CLASS);
  if (total < MIN_TOTAL || thin.length) {
    const detail = thin.length
      ? `其中 ${thin.map(([name, n]) => `“${name}”只有 ${n} 条`).join("、")}。`
      : "";
    trainWarning.textContent =
      `数据偏少：现在共 ${total} 条。${detail}每类建议 ${MIN_PER_CLASS} 条以上，` +
      "太少模型会死记硬背，遇到新数据容易出错。可以回第 1 步加载样本包或继续采集。";
    trainWarning.hidden = false;
  } else {
    trainWarning.hidden = true;
  }
}

/* 训练日志：终端风格逐行播放真实训练结果 */
const LOG_LINE_DELAY_MS = 380;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function logLine(text, cls) {
  const line = el("div", `log-line${cls ? ` ${cls}` : ""}`, text);
  trainLog.appendChild(line);
  return line;
}

async function playTrainingLog(report, elapsedMs) {
  const labelCount = (report.labels || []).length;
  const dataLine = labelCount
    ? `读取数据：${report.sample_count} 条样本、${labelCount} 个类别`
    : `读取数据：${report.sample_count} 条`;
  logLine(`[1/4] ${dataLine}`, "log-ok");
  await sleep(LOG_LINE_DELAY_MS);
  if (report.model_name) {
    logLine(`[2/4] 使用模型：${report.model_name}`, "log-ok");
    await sleep(LOG_LINE_DELAY_MS);
  }
  const fitLine =
    report.train_accuracy !== null && report.train_accuracy !== undefined
      ? `拟合训练数据：训练准确率 ${percent(report.train_accuracy)}`
      : "拟合训练数据：完成";
  logLine(`[3/4] ${fitLine}（耗时 ${Math.max(1, Math.round(elapsedMs))} 毫秒）`, "log-ok");
  await sleep(LOG_LINE_DELAY_MS);
  if (report.cross_val_accuracy) {
    logLine(`[4/4] 交叉验证：把数据分组轮流考试，平均分 ${percent(report.cross_val_accuracy)}`, "log-ok");
  } else if (report.train_accuracy !== null && report.train_accuracy !== undefined) {
    logLine("[4/4] 交叉验证：数据不够，跳过（每类 10 条以上才能模拟考试）", "log-warn");
  } else {
    logLine("[4/4] 已建立检索索引", "log-ok");
  }
  await sleep(LOG_LINE_DELAY_MS);
  logLine("模型已保存。详细报告 ↓，然后去第 3 步测试。", "log-done");
}

if (capability === "ocr_typo_checker") {
  document.getElementById("train-hint").textContent =
    "这一步会把正确文字记住，作为查错的标准答案。";
  trainButton.textContent = "保存正确文字";
}

function buildModelPicker() {
  const choices = state.model_choices || [];
  if (!choices.length) return;
  compareButton.hidden = false;
  document.getElementById("train-hint").textContent =
    "先选一个模型再训练。不确定选哪个？点「对比所有模型」，用同一份数据让它们比一场。";

  const heading = el("p", "field-label", "选择模型");
  const grid = el("div", "model-grid");
  for (const choice of choices) {
    const card = el("div", "model-card");
    card.dataset.slug = choice.slug;
    card.tabIndex = 0;
    card.setAttribute("role", "button");
    const head = el("div", "model-card-head");
    head.appendChild(el("strong", "", choice.name));
    head.appendChild(el("span", "model-school", choice.school));
    card.appendChild(head);
    card.appendChild(el("p", "model-principle", choice.principle));
    const meta = el("ul", "model-meta");
    meta.appendChild(el("li", "model-pro", `优点：${choice.strengths}`));
    meta.appendChild(el("li", "model-con", `局限：${choice.weaknesses}`));
    meta.appendChild(el("li", "model-fit", `适合：${choice.best_for}`));
    card.appendChild(meta);
    const select = () => {
      selectedClassifier = choice.slug;
      grid.querySelectorAll(".model-card").forEach((node) =>
        node.classList.toggle("selected", node === card)
      );
    };
    card.addEventListener("click", select);
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") select();
    });
    if (choice.default && !selectedClassifier) {
      selectedClassifier = choice.slug;
      card.classList.add("selected");
    }
    grid.appendChild(card);
  }
  modelPicker.append(heading, grid);
}
buildModelPicker();

trainButton.addEventListener("click", async () => {
  trainButton.disabled = true;
  setStatus("train-status", "", false);
  trainReport.innerHTML = "";
  trainLog.hidden = false;
  trainLog.innerHTML = "";
  logLine(`$ python train.py${selectedClassifier ? ` --model ${selectedClassifier}` : ""}`, "log-cmd");
  const running = logLine("正在训练", "log-run");
  trainLog.scrollIntoView({ behavior: "smooth", block: "nearest" });
  const startedAt = performance.now();
  try {
    const next = await postJson("/train", { classifier: selectedClassifier });
    const elapsedMs = performance.now() - startedAt;
    running.remove();
    await playTrainingLog(next.report, elapsedMs);
    Object.assign(state, { project: next.project, dataset: next.dataset });
    renderTrainReport(next.report);
    stepsDone[1] = true;
    refreshChecks();
    setStatus("train-status", "训练完成！去第 3 步测试一下吧。", false);
    trainReport.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (error) {
    running.remove();
    logLine(`训练失败：${error.message}`, "log-err");
    setStatus("train-status", error.message, true);
  } finally {
    trainButton.disabled = false;
  }
});

compareButton.addEventListener("click", async () => {
  compareButton.disabled = true;
  setStatus("train-status", "正在用同一份数据训练所有模型……", false);
  try {
    const result = await postJson("/train/compare", {});
    renderCompareTable(result.rows);
    setStatus("train-status", "对比完成。点中意的模型卡片，再点「开始训练」正式训练。", false);
  } catch (error) {
    setStatus("train-status", error.message, true);
  } finally {
    compareButton.disabled = false;
  }
});

function renderCompareTable(rows) {
  compareResult.innerHTML = "";
  if (!rows || !rows.length) return;
  const card = el("div", "report-card");
  card.appendChild(el("p", "field-label", "同一份数据，不同模型的成绩单"));
  const table = el("table", "compare-table");
  const head = el("tr");
  for (const text of ["模型", "训练准确率", "交叉验证", "训练耗时"]) {
    head.appendChild(el("th", "", text));
  }
  table.appendChild(head);

  const best = rows.reduce((acc, row) =>
    (row.cross_val_accuracy ?? -1) > (acc.cross_val_accuracy ?? -1) ? row : acc
  );
  for (const row of rows) {
    const tr = el("tr");
    const isBest = row === best && row.cross_val_accuracy !== null;
    tr.appendChild(el("td", "", `${isBest ? "★ " : ""}${row.name}`));
    tr.appendChild(el("td", "", percent(row.train_accuracy)));
    tr.appendChild(
      el("td", "", row.cross_val_accuracy === null ? "数据不够" : percent(row.cross_val_accuracy))
    );
    tr.appendChild(el("td", "", `${row.train_ms} 毫秒`));
    if (isBest) tr.classList.add("compare-best");
    table.appendChild(tr);
  }
  card.appendChild(table);
  const note = el("p", "report-classes");
  note.textContent =
    "★ 是交叉验证最高的模型。交叉验证比训练准确率更接近真实水平；" +
    "如果某个模型训练准确率很高但交叉验证低很多，说明它在“死记硬背”（过拟合）。" +
    "每类数据满 3 条才能算交叉验证。";
  card.appendChild(note);
  compareResult.appendChild(card);
}

function renderTrainReport(report) {
  trainReport.innerHTML = "";
  if (!report) return;
  const card = el("div", "report-card");
  const facts = el("div", "report-facts");
  facts.appendChild(reportFact("数据量", `${report.sample_count}`));
  if (report.labels && report.labels.length) {
    facts.appendChild(reportFact("类别数", `${report.labels.length}`));
  }
  if (report.train_accuracy !== null && report.train_accuracy !== undefined) {
    facts.appendChild(reportFact("训练准确率", percent(report.train_accuracy)));
  }
  if (report.cross_val_accuracy) {
    facts.appendChild(reportFact("交叉验证准确率", percent(report.cross_val_accuracy)));
  }
  if (report.model_name) {
    facts.appendChild(reportFact("使用模型", report.model_name));
  }
  card.appendChild(facts);
  if (report.cross_val_accuracy) {
    const note = el("p", "report-classes");
    note.textContent =
      "交叉验证准确率：把数据分成几份，轮流留一份当考题考模型，算出的平均分。它比训练准确率更接近模型遇到新数据时的真实水平。";
    card.appendChild(note);
  }
  if (report.feature_mode) {
    const note = el("p", "report-classes");
    note.textContent =
      report.feature_mode === "mobilenet_v2"
        ? "特征提取：MobileNet 迁移学习——用在上百万张图片上预训练好的网络理解你的图片，少量样本也能学得稳。"
        : "特征提取：原始像素（基础模式）。让老师运行 python scripts/download_pretrained.py 可升级为 MobileNet 迁移学习。";
    card.appendChild(note);
  }
  if (report.class_counts && Object.keys(report.class_counts).length) {
    const list = el("p", "report-classes");
    list.textContent =
      "每类数据量：" +
      Object.entries(report.class_counts)
        .map(([label, count]) => `${label} ${count} 条`)
        .join("，");
    card.appendChild(list);
  }
  if (report.rules_text) {
    const details = el("details", "rules-details");
    details.appendChild(el("summary", "", "看看模型学到的决策规则"));
    const pre = el("pre", "mono");
    pre.textContent = report.rules_text;
    details.appendChild(pre);
    card.appendChild(details);
  }
  if (report.feature_importances) {
    const ranked = Object.entries(report.feature_importances).sort((a, b) => b[1] - a[1]);
    const box = el("div", "imp-list");
    box.appendChild(el("p", "field-label", "模型眼中各传感器的重要程度"));
    for (const [name, value] of ranked) {
      const pct = Math.round(value * 100);
      const row = el("div", "imp-row");
      row.appendChild(el("span", "imp-name", name));
      const track = el("div", "imp-track");
      const bar = el("div", "imp-bar");
      bar.style.width = `${Math.max(2, pct)}%`;
      track.appendChild(bar);
      row.appendChild(track);
      row.appendChild(el("span", "imp-value", `${pct}%`));
      box.appendChild(row);
    }
    card.appendChild(box);
  }
  trainReport.appendChild(card);
}

if (state.project.train_report) {
  renderTrainReport(state.project.train_report);
}

function reportFact(name, value) {
  const fact = el("div", "report-fact");
  fact.appendChild(el("span", "fact-value", value));
  fact.appendChild(el("span", "fact-name", name));
  return fact;
}

/* ---------- testing ---------- */

const testArea = document.getElementById("test-area");
const testResult = document.getElementById("test-result");

function buildTextTest(placeholder, buttonText) {
  const input = el("textarea", "big-textarea");
  input.rows = 3;
  input.placeholder = placeholder;
  const button = el("button", "btn-primary", buttonText);
  button.type = "button";
  button.addEventListener("click", async () => {
    try {
      const result = await postJson("/predict", { text: input.value });
      renderPredictResult(result);
      stepsDone[2] = true;
      refreshChecks();
    } catch (error) {
      renderPredictError(error.message);
    }
  });
  testArea.append(input, button);
}

function buildSensorTest() {
  const columns = (state.dataset.columns || []).slice(0, -1);
  const wrap = el("div", "sensor-inputs");
  const inputs = new Map();

  function renderInputs(names) {
    wrap.innerHTML = "";
    inputs.clear();
    for (const name of names) {
      const label = el("label", "field-label", name);
      const input = el("input", "sensor-input");
      input.type = "number";
      input.step = "any";
      inputs.set(name, input);
      label.appendChild(input);
      wrap.appendChild(label);
    }
  }
  renderInputs(columns);

  const button = el("button", "btn-primary", "看看模型的决定");
  button.type = "button";
  button.addEventListener("click", async () => {
    // Re-sync inputs if columns changed after page load (e.g. data pack loaded post-init)
    const liveColumns = (state.dataset.columns || []).slice(0, -1);
    if (liveColumns.join(",") !== [...inputs.keys()].join(",")) {
      const saved = Object.fromEntries([...inputs.entries()].map(([k, v]) => [k, v.value]));
      renderInputs(liveColumns);
      for (const [name, inp] of inputs) if (saved[name] !== undefined) inp.value = saved[name];
    }
    if (inputs.size === 0) {
      renderPredictError("请先在第一步准备传感器数据，训练后再来测试。");
      return;
    }
    const values = {};
    for (const [name, input] of inputs) values[name] = input.value;
    try {
      const result = await postJson("/predict", { values });
      renderPredictResult(result);
      stepsDone[2] = true;
      refreshChecks();
    } catch (error) {
      renderPredictError(error.message);
    }
  });
  testArea.append(wrap, button);
}

function buildImageTest() {
  const fileInput = el("input");
  fileInput.type = "file";
  fileInput.accept = "image/*";
  const preview = el("img", "test-preview");
  preview.hidden = true;
  fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) {
      preview.src = URL.createObjectURL(fileInput.files[0]);
      preview.hidden = false;
    }
  });
  const button = el("button", "btn-primary", "识别这张图片");
  button.type = "button";
  button.addEventListener("click", async () => {
    if (!fileInput.files.length) {
      renderPredictError("请先选择一张图片。");
      return;
    }
    const form = new FormData();
    form.append("file", fileInput.files[0]);
    try {
      const result = await api("/predict/image", { method: "POST", body: form });
      renderPredictResult(result);
      stepsDone[2] = true;
      refreshChecks();
    } catch (error) {
      renderPredictError(error.message);
    }
  });
  testArea.append(fileInput, preview, button);
}

function buildAudioTest() {
  let pendingClip = null;
  const preview = el("audio");
  preview.controls = true;
  preview.hidden = true;

  function setClip(blob) {
    pendingClip = blob;
    preview.src = URL.createObjectURL(blob);
    preview.hidden = false;
  }

  const record = recorderButton("🎙 录一段新声音", setClip, renderPredictError);
  const fileInput = el("input");
  fileInput.type = "file";
  fileInput.accept = ".wav,audio/wav";
  fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) setClip(fileInput.files[0]);
  });

  const button = el("button", "btn-primary", "听听是哪一类");
  button.type = "button";
  button.addEventListener("click", async () => {
    if (!pendingClip) {
      renderPredictError("请先录一段声音，或选择一个 WAV 文件。");
      return;
    }
    const form = new FormData();
    form.append("file", pendingClip, pendingClip.name || "probe.wav");
    try {
      const result = await api("/predict/audio", { method: "POST", body: form });
      renderPredictResult(result);
      stepsDone[2] = true;
      refreshChecks();
    } catch (error) {
      renderPredictError(error.message);
    }
  });
  testArea.append(record, fileInput, preview, button);
}

function renderPredictError(message) {
  testResult.innerHTML = "";
  testResult.appendChild(el("p", "form-error", message));
}

function renderPredictResult(result) {
  testResult.innerHTML = "";
  const card = el("div", "result-card");

  if (capability === "ocr_typo_checker") {
    card.appendChild(el("p", "result-main", result.label));
    if (result.typos && result.typos.length) {
      const list = el("ul", "typo-list");
      for (const typo of result.typos) {
        list.appendChild(
          el("li", "", `第 ${typo.position} 个字：“${typo.observed || "缺字"}” → “${typo.correct}”`)
        );
      }
      card.appendChild(list);
    }
  } else if (capability === "qa_retrieval") {
    card.appendChild(el("p", "result-main", result.label));
    if (result.matched_question) {
      card.appendChild(el("p", "result-sub", `匹配到的问题：${result.matched_question}`));
    }
  } else {
    card.appendChild(el("p", "result-main", `识别结果：${result.label}`));
    if (result.scores) {
      card.appendChild(scoreBars(result.scores));
    }
  }
  testResult.appendChild(card);
}

/* ---------- export ---------- */

const exportButton = document.getElementById("export-button");
const exportResult = document.getElementById("export-result");

exportButton.addEventListener("click", async () => {
  exportButton.disabled = true;
  setStatus("export-status", "正在打包……", false);
  try {
    const result = await postJson("/export", {});
    exportResult.innerHTML = "";
    const link = el("a", "btn-download", "下载比赛材料包 (.zip)");
    link.href = result.download_url;
    exportResult.appendChild(link);
    const details = el("details", "files-details");
    details.appendChild(el("summary", "", `包里有 ${result.files.length} 个文件`));
    const list = el("ul", "files-list mono");
    for (const file of result.files) list.appendChild(el("li", "", file));
    details.appendChild(list);
    exportResult.appendChild(details);
    stepsDone[3] = true;
    refreshChecks();
    setStatus("export-status", "打包完成！", false);
  } catch (error) {
    setStatus("export-status", error.message, true);
  } finally {
    exportButton.disabled = false;
  }
});

/* ---------- init ---------- */

const editors = {
  text: buildTextEditor,
  qa: buildQaEditor,
  sensor: buildSensorEditor,
  ocr: buildOcrEditor,
  image: buildImageEditor,
  audio: buildAudioEditor,
};
editors[kind]();

const testBuilders = {
  text: () => buildTextTest("输入一句新的话，看看模型分到哪个类别。", "测试分类"),
  qa: () => buildTextTest("输入一个问题，看看模型怎么回答。", "提问"),
  ocr: () => buildTextTest("粘贴拍照识别出来的文字，模型会找出错别字。", "开始查错"),
  sensor: buildSensorTest,
  image: buildImageTest,
  audio: buildAudioTest,
};
testBuilders[kind]();

refreshChecks();
showStep(0);
