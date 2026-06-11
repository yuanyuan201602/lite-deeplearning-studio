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

/* ---------- stepper ---------- */

const stepButtons = Array.from(document.querySelectorAll("#stepper .step"));

function showStep(index) {
  stepButtons.forEach((button, i) => {
    button.classList.toggle("step-active", i === index);
    document.getElementById(`panel-${i}`).hidden = i !== index;
  });
}

function refreshChecks() {
  stepButtons.forEach((button, i) => {
    button.querySelector(".step-check").hidden = !stepsDone[i];
  });
}

stepButtons.forEach((button, index) => {
  button.addEventListener("click", () => showStep(index));
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

  renderImageClasses();
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
const trainReport = document.getElementById("train-report");

if (capability === "ocr_typo_checker") {
  document.getElementById("train-hint").textContent =
    "这一步会把正确文字记住，作为查错的标准答案。";
  trainButton.textContent = "保存正确文字";
}

trainButton.addEventListener("click", async () => {
  trainButton.disabled = true;
  setStatus("train-status", "正在训练，请稍候……", false);
  try {
    const next = await postJson("/train", {});
    Object.assign(state, { project: next.project, dataset: next.dataset });
    renderTrainReport(next.report);
    stepsDone[1] = true;
    refreshChecks();
    setStatus("train-status", "训练完成！去第 3 步测试一下吧。", false);
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
  card.appendChild(facts);
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
};
editors[kind]();

const testBuilders = {
  text: () => buildTextTest("输入一句新的话，看看模型分到哪个类别。", "测试分类"),
  qa: () => buildTextTest("输入一个问题，看看模型怎么回答。", "提问"),
  ocr: () => buildTextTest("粘贴拍照识别出来的文字，模型会找出错别字。", "开始查错"),
  sensor: buildSensorTest,
  image: buildImageTest,
};
testBuilders[kind]();

refreshChecks();
showStep(0);
