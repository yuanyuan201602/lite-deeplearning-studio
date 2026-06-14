"use strict";

/* 目标检测项目页逻辑（独立于 app.js，按 ai_capability 条件加载）。
   四步：标注画框 → 训练（算法卡片）→ 测试画框 → 导出（下一期）。 */

const state = JSON.parse(document.getElementById("initial-state").textContent);
const projectId = state.project.project_id;

const BOX_COLORS = ["#d97757", "#4a6b8a", "#3e7c4f", "#9c4a2d", "#b8862f", "#6a5acd"];
const MIN_BOX = 8;
const CANVAS_W = 520;

/* ---------- helpers ---------- */

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function errorDetail(data) {
  const detail = data && data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((i) => i && i.msg).filter(Boolean).join("；") || "输入有误，请检查。";
  }
  return "操作失败，请重试。";
}

async function request(path, options) {
  const response = await fetch(`/api/projects/${projectId}${path}`, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(errorDetail(data));
  return data;
}

function setStatus(id, message, isError) {
  const node = document.getElementById(id);
  node.textContent = message;
  node.classList.toggle("status-error", Boolean(isError));
  node.classList.toggle("status-ok", !isError && Boolean(message));
}

/* ---------- stepper / locks ---------- */

const stepButtons = Array.from(document.querySelectorAll("#stepper .step"));
const stepsDone = {
  0: (state.dataset.sample_count || 0) > 0,
  1: Boolean(state.project.train_report),
  2: false,
  3: false,
};

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

function refreshChecks() {
  stepButtons.forEach((button, i) => {
    button.querySelector(".step-check").hidden = !stepsDone[i];
    button.classList.toggle("step-locked", !isStepUnlocked(i));
  });
}

stepButtons.forEach((button, index) => {
  button.addEventListener("click", () => {
    if (isStepUnlocked(index)) showStep(index);
  });
});

/* ---------- shared: draw image + boxes on a canvas ---------- */

const imageCache = new Map();

function loadImage(name) {
  if (imageCache.has(name)) return Promise.resolve(imageCache.get(name));
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      imageCache.set(name, img);
      resolve(img);
    };
    img.onerror = reject;
    img.src = `/api/projects/${projectId}/detect/image/${encodeURIComponent(name)}`;
  });
}

function fitCanvas(canvas, imgW, imgH) {
  const scale = CANVAS_W / imgW;
  canvas.width = CANVAS_W;
  canvas.height = Math.round(imgH * scale);
  return scale;
}

function drawBoxes(ctx, scale, boxes, colorFor, withScore) {
  ctx.lineWidth = 2;
  ctx.font = "13px sans-serif";
  ctx.textBaseline = "top";
  for (const box of boxes) {
    const color = colorFor(box.label);
    const x = box.x * scale;
    const y = box.y * scale;
    const w = box.w * scale;
    const h = box.h * scale;
    ctx.strokeStyle = color;
    ctx.strokeRect(x, y, w, h);
    const tag = withScore && box.score != null
      ? `${box.label} ${Math.round(box.score * 100)}%`
      : box.label;
    const tw = ctx.measureText(tag).width + 8;
    ctx.fillStyle = color;
    ctx.fillRect(x, Math.max(0, y - 18), tw, 18);
    ctx.fillStyle = "#fff";
    ctx.fillText(tag, x + 4, Math.max(0, y - 18) + 3);
  }
}

/* ====================================================================== */
/* 第 1 步：标注画框                                                        */
/* ====================================================================== */

const dataEditor = document.getElementById("data-editor");
const saveButton = document.getElementById("save-data");

let annotations = (state.dataset.items || []).map((item) => ({
  image: item.image,
  width: item.width,
  height: item.height,
  boxes: (item.boxes || []).map((b) => ({ ...b })),
}));
let current = 0;
let activeLabel = "";

function allLabels() {
  const set = [];
  for (const ann of annotations) {
    for (const box of ann.boxes) if (!set.includes(box.label)) set.push(box.label);
  }
  return set;
}

function colorFor(label) {
  const labels = allLabels();
  const index = labels.indexOf(label);
  return BOX_COLORS[(index < 0 ? labels.length : index) % BOX_COLORS.length];
}

function buildAnnotator() {
  dataEditor.innerHTML = "";

  // 上传 + 类别工具条
  const toolbar = el("div", "detect-toolbar");
  const uploadLabel = el("label", "btn-secondary detect-upload");
  uploadLabel.appendChild(el("span", "", "+ 上传图片"));
  const fileInput = el("input");
  fileInput.type = "file";
  fileInput.accept = "image/png,image/jpeg";
  fileInput.multiple = true;
  fileInput.hidden = true;
  fileInput.addEventListener("change", () => uploadImages(fileInput.files));
  uploadLabel.appendChild(fileInput);
  toolbar.appendChild(uploadLabel);

  const labelBar = el("div", "detect-labels");
  labelBar.appendChild(el("span", "field-label", "当前类别："));
  for (const label of labelsForChips()) {
    const chip = el("button", `detect-chip${label === activeLabel ? " active" : ""}`, label);
    chip.type = "button";
    chip.style.setProperty("--chip", colorFor(label));
    chip.addEventListener("click", () => {
      activeLabel = label;
      buildAnnotator();
    });
    labelBar.appendChild(chip);
  }
  const newInput = el("input", "detect-newlabel");
  newInput.placeholder = "新类别名…";
  newInput.maxLength = 20;
  const addBtn = el("button", "btn-secondary", "添加");
  addBtn.type = "button";
  addBtn.addEventListener("click", () => {
    const name = newInput.value.trim();
    if (name) {
      activeLabel = name;
      // a label only "exists" once used; keep it active so the next box adopts it
      ensurePlaceholderLabel(name);
      buildAnnotator();
    }
  });
  labelBar.append(newInput, addBtn);
  toolbar.appendChild(labelBar);
  dataEditor.appendChild(toolbar);

  if (!annotations.length) {
    dataEditor.appendChild(
      el("p", "detect-empty", "还没有图片。点「上传图片」加几张，再在图上把要识别的目标框出来。")
    );
    return;
  }

  current = Math.min(current, annotations.length - 1);
  const ann = annotations[current];

  // 画布
  const stage = el("div", "detect-stage");
  const canvas = el("canvas", "detect-canvas");
  stage.appendChild(canvas);
  dataEditor.appendChild(stage);

  const hint = el("p", "detect-hint");
  hint.textContent = activeLabel
    ? `在图上拖动鼠标，把「${activeLabel}」框出来。`
    : "先在上面添加 / 选择一个类别，再到图上拖动画框。";
  dataEditor.appendChild(hint);

  loadImage(ann.image).then((img) => {
    const scale = fitCanvas(canvas, ann.width || img.width, ann.height || img.height);
    redrawAnnotator(canvas, img, scale, ann);
    attachDrawing(canvas, img, scale, ann);
  });

  // 图片导航
  const nav = el("div", "detect-nav");
  const prev = el("button", "btn-secondary", "‹ 上一张");
  prev.type = "button";
  prev.disabled = current === 0;
  prev.addEventListener("click", () => { current -= 1; buildAnnotator(); });
  const pos = el("span", "detect-pos", `第 ${current + 1} / ${annotations.length} 张`);
  const next = el("button", "btn-secondary", "下一张 ›");
  next.type = "button";
  next.disabled = current === annotations.length - 1;
  next.addEventListener("click", () => { current += 1; buildAnnotator(); });
  const del = el("button", "btn-secondary detect-del", "删除本图");
  del.type = "button";
  del.addEventListener("click", () => {
    annotations.splice(current, 1);
    buildAnnotator();
  });
  nav.append(prev, pos, next, del);
  dataEditor.appendChild(nav);

  // 当前图的框列表
  const list = el("div", "detect-boxlist");
  if (!ann.boxes.length) {
    list.appendChild(el("p", "detect-hint", "这张图还没框任何目标。"));
  }
  ann.boxes.forEach((box, i) => {
    const row = el("div", "detect-boxrow");
    const dot = el("span", "detect-dot");
    dot.style.background = colorFor(box.label);
    row.append(dot, el("span", "detect-boxlabel", box.label));
    const rm = el("button", "detect-boxrm", "✕");
    rm.type = "button";
    rm.title = "删除这个框";
    rm.addEventListener("click", () => {
      ann.boxes.splice(i, 1);
      buildAnnotator();
    });
    row.appendChild(rm);
    list.appendChild(row);
  });
  dataEditor.appendChild(list);
}

// keep a just-typed label selectable even before it's used on a box
const placeholderLabels = new Set();
function ensurePlaceholderLabel(name) {
  placeholderLabels.add(name);
}
function labelsForChips() {
  const used = allLabels();
  for (const p of placeholderLabels) if (!used.includes(p)) used.push(p);
  return used;
}

function redrawAnnotator(canvas, img, scale, ann) {
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
  drawBoxes(ctx, scale, ann.boxes, colorFor, false);
}

function attachDrawing(canvas, img, scale, ann) {
  let start = null;
  const toImg = (event) => {
    const rect = canvas.getBoundingClientRect();
    const cx = ((event.clientX - rect.left) / rect.width) * canvas.width;
    const cy = ((event.clientY - rect.top) / rect.height) * canvas.height;
    return { x: cx / scale, y: cy / scale };
  };
  canvas.addEventListener("mousedown", (e) => {
    if (!activeLabel) return;
    start = toImg(e);
  });
  canvas.addEventListener("mousemove", (e) => {
    if (!start) return;
    const now = toImg(e);
    redrawAnnotator(canvas, img, scale, ann);
    const ctx = canvas.getContext("2d");
    ctx.strokeStyle = colorFor(activeLabel);
    ctx.setLineDash([5, 4]);
    ctx.strokeRect(
      start.x * scale, start.y * scale,
      (now.x - start.x) * scale, (now.y - start.y) * scale
    );
    ctx.setLineDash([]);
  });
  const finish = (e) => {
    if (!start) return;
    const end = toImg(e);
    const x = Math.round(Math.min(start.x, end.x));
    const y = Math.round(Math.min(start.y, end.y));
    const w = Math.round(Math.abs(end.x - start.x));
    const h = Math.round(Math.abs(end.y - start.y));
    start = null;
    if (w >= MIN_BOX && h >= MIN_BOX) {
      ann.boxes.push({ x, y, w, h, label: activeLabel });
      buildAnnotator();
    } else {
      redrawAnnotator(canvas, img, scale, ann);
    }
  };
  canvas.addEventListener("mouseup", finish);
  canvas.addEventListener("mouseleave", () => { start = null; });
}

async function uploadImages(files) {
  if (!files || !files.length) return;
  setStatus("data-status", "正在上传图片…", false);
  try {
    for (const file of files) {
      const form = new FormData();
      form.append("file", file);
      const info = await request("/data/detect/image", { method: "POST", body: form });
      annotations.push({ image: info.image, width: info.width, height: info.height, boxes: [] });
    }
    current = annotations.length - 1;
    buildAnnotator();
    setStatus("data-status", "图片已上传，开始框目标吧。", false);
  } catch (error) {
    setStatus("data-status", error.message, true);
  }
}

saveButton.addEventListener("click", async () => {
  saveButton.disabled = true;
  try {
    const next = await request("/data/detect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items: annotations }),
    });
    Object.assign(state, { dataset: next.dataset });
    const total = next.dataset.box_count || 0;
    stepsDone[0] = total > 0;
    refreshChecks();
    if (total > 0) {
      setStatus("data-status", `已保存：${next.dataset.image_count} 张图、${total} 个框。去第 2 步训练。`, false);
    } else {
      setStatus("data-status", "还没有任何框，请先在图上把目标框出来。", true);
    }
  } catch (error) {
    setStatus("data-status", error.message, true);
  } finally {
    saveButton.disabled = false;
  }
});

buildAnnotator();

/* ====================================================================== */
/* 第 2 步：算法卡片 + 训练                                                 */
/* ====================================================================== */

const modelPicker = document.getElementById("model-picker");
const trainButton = document.getElementById("train-button");
const compareButton = document.getElementById("compare-button");
const trainReport = document.getElementById("train-report");
if (compareButton) compareButton.hidden = true;

let selectedAlgorithm = "lite";

function buildAlgorithmCards() {
  modelPicker.innerHTML = "";
  const cards = state.model_choices || [];
  modelPicker.appendChild(el("p", "field-label", "选一个检测算法"));
  modelPicker.appendChild(
    el("p", "field-sub", "两种算法都能做检测，但思路不一样——点开卡片看它们各自的区别。")
  );
  const grid = el("div", "model-grid");
  for (const card of cards) {
    const locked = card.trainable === false;
    const node = el("div", `model-card${locked ? " locked" : ""}${card.slug === selectedAlgorithm ? " selected" : ""}`);
    const head = el("div", "model-card-head");
    const title = el("div", "model-title");
    title.appendChild(el("strong", "", card.name));
    if (card.en_name) title.appendChild(el("span", "model-en", card.en_name));
    head.appendChild(title);
    if (locked) head.appendChild(el("span", "model-lock", "下一期"));
    node.appendChild(head);
    node.appendChild(el("p", "model-principle", card.principle || ""));
    if (card.strengths) node.appendChild(el("p", "model-line", `优点：${card.strengths}`));
    if (card.weaknesses) node.appendChild(el("p", "model-line", `局限：${card.weaknesses}`));
    if (card.note) node.appendChild(el("p", "model-note", card.note));
    if (!locked) {
      node.addEventListener("click", () => {
        selectedAlgorithm = card.slug;
        buildAlgorithmCards();
      });
    }
    grid.appendChild(node);
  }
  modelPicker.appendChild(grid);
}
buildAlgorithmCards();

trainButton.addEventListener("click", async () => {
  trainButton.disabled = true;
  setStatus("train-status", "正在训练……（裁剪每个框、提特征、学分类，几秒完成）", false);
  trainReport.innerHTML = "";
  try {
    const next = await request("/train", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ classifier: selectedAlgorithm }),
    });
    Object.assign(state, { project: next.project });
    renderTrainReport(next.report);
    stepsDone[1] = true;
    refreshChecks();
    setStatus("train-status", "训练完成！去第 3 步上传一张新图测试。", false);
  } catch (error) {
    setStatus("train-status", error.message, true);
  } finally {
    trainButton.disabled = false;
  }
});

function renderTrainReport(report) {
  trainReport.innerHTML = "";
  if (!report) return;
  const card = el("div", "report-card");
  const facts = el("div", "report-facts");
  const add = (name, value) => {
    const f = el("div", "report-fact");
    f.appendChild(el("span", "fact-value", String(value)));
    f.appendChild(el("span", "fact-name", name));
    facts.appendChild(f);
  };
  add("类别数", (report.labels || []).length);
  add("框数", report.box_count || 0);
  add("图片数", report.image_count || 0);
  add("背景样本", report.background_count || 0);
  if (report.model_name) add("使用算法", report.model_name);
  card.appendChild(facts);
  if (report.class_counts && Object.keys(report.class_counts).length) {
    card.appendChild(
      el("p", "report-classes",
        "每类框数：" + Object.entries(report.class_counts).map(([l, c]) => `${l} ${c} 个`).join("，"))
    );
  }
  card.appendChild(
    el("p", "report-classes",
      "模型学会了认出每个候选框里是什么——还多学了一个「背景」类，用来把没东西的框排除掉。" +
      "去第 3 步上传一张新图，看它画的框。")
  );
  trainReport.appendChild(card);
}
if (state.project.train_report) renderTrainReport(state.project.train_report);

/* ====================================================================== */
/* 第 3 步：测试（上传图 → 画预测框）                                       */
/* ====================================================================== */

const testArea = document.getElementById("test-area");
const testResult = document.getElementById("test-result");

function buildTester() {
  testArea.innerHTML = "";
  const uploadLabel = el("label", "btn-primary detect-upload");
  uploadLabel.appendChild(el("span", "", "上传一张新图测试"));
  const fileInput = el("input");
  fileInput.type = "file";
  fileInput.accept = "image/png,image/jpeg";
  fileInput.hidden = true;
  fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) runDetect(fileInput.files[0]);
  });
  uploadLabel.appendChild(fileInput);
  testArea.appendChild(uploadLabel);
  testArea.appendChild(
    el("p", "detect-hint", "选一张训练时没用过的图，看模型找得到、框得准、认得对吗。")
  );
}

async function runDetect(file) {
  testResult.innerHTML = "";
  setStatus("test-result", "", false);
  const loading = el("p", "detect-hint", "正在检测……");
  testResult.appendChild(loading);
  try {
    const form = new FormData();
    form.append("file", file);
    const result = await request("/predict/detect", { method: "POST", body: form });
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      testResult.innerHTML = "";
      const canvas = el("canvas", "detect-canvas");
      const scale = fitCanvas(canvas, result.width || img.width, result.height || img.height);
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      drawBoxes(ctx, scale, result.boxes, colorFor, true);
      const stage = el("div", "detect-stage");
      stage.appendChild(canvas);
      testResult.appendChild(stage);
      const msg = result.count
        ? `模型画出了 ${result.count} 个框。检查一下：位置准不准、标签对不对？`
        : "模型没找到任何目标。可能是这张图和训练图差别太大，或者预训练网络压根没在上面找出候选框（轻量检测的局限）。";
      testResult.appendChild(el("p", "report-classes", msg));
      URL.revokeObjectURL(url);
      stepsDone[2] = true;
      refreshChecks();
    };
    img.src = url;
  } catch (error) {
    testResult.innerHTML = "";
    setStatus("test-result", error.message, true);
  }
}
buildTester();

/* ====================================================================== */
/* 第 4 步：导出（下一期）                                                  */
/* ====================================================================== */

const exportButton = document.getElementById("export-button");
const downloadButton = document.getElementById("download-button");
const exportResult = document.getElementById("export-result");
if (exportButton) {
  exportButton.disabled = true;
  exportButton.textContent = "导出材料包（下一期上线）";
}
if (downloadButton) downloadButton.classList.add("is-disabled");
if (exportResult) {
  exportResult.appendChild(
    el("p", "detect-hint",
      "检测的材料包（能运行的检测脚本和模型）将在下一期上线。现在先把标注、训练、测试这三步玩透——" +
      "也可以在卡片里看看「YOLO」端到端检测和这里的「轻量检测」有什么不同。")
  );
}

/* 初始：定位到第一个未完成的步骤并刷新锁 */
refreshChecks();
showStep(stepsDone[0] ? (stepsDone[1] ? 2 : 1) : 0);
