/* 深度学习地图页的互动演示（阶段 3）。全部用「查表式」预置数据，不做真实训练。 */
(() => {
  "use strict";
  const SVG = "http://www.w3.org/2000/svg";

  /* ---------- 通用 ---------- */
  function demoShell(mount, title, intro) {
    mount.classList.add("demo-card");
    mount.innerHTML = "";
    const h = document.createElement("p");
    h.className = "demo-title";
    h.textContent = title;
    mount.appendChild(h);
    if (intro) {
      const p = document.createElement("p");
      p.className = "demo-intro";
      p.textContent = intro;
      mount.appendChild(p);
    }
    return mount;
  }

  /* ========== 1. 数据量 vs 准确率（滑块） ========== */
  function mountDataSize(mount) {
    demoShell(
      mount,
      "玩一玩：数据越多，模型越准吗？",
      "拖动滑块改变「每个类别的样本数」，看准确率怎么变。（这是示意曲线，不是真实训练。）"
    );

    const W = 320;
    const H = 170;
    const PAD = 30;
    const base = 0.5; // 两类时瞎猜的水平
    const plateau = 0.93; // 数据再多也到不了 100%
    const acc = (n) => plateau - (plateau - base) * Math.exp(-0.06 * n);
    const x = (n) => PAD + (n / 100) * (W - PAD - 8);
    const y = (a) => H - PAD - ((a - 0.4) / 0.6) * (H - PAD - 8);

    let d = `M ${x(1)} ${y(acc(1))}`;
    for (let n = 2; n <= 100; n += 1) d += ` L ${x(n)} ${y(acc(n))}`;

    const svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.classList.add("demo-svg");
    svg.innerHTML =
      `<line class="demo-axis" x1="${PAD}" y1="${H - PAD}" x2="${W - 6}" y2="${H - PAD}"/>` +
      `<line class="demo-axis" x1="${PAD}" y1="8" x2="${PAD}" y2="${H - PAD}"/>` +
      `<text class="demo-axislab" x="${W - 6}" y="${H - PAD + 16}" text-anchor="end">每类样本数 →</text>` +
      `<text class="demo-axislab" x="${PAD - 6}" y="14" text-anchor="end">准确率</text>` +
      `<path class="demo-curve" d="${d}"/>` +
      `<line class="demo-marker" id="ds-marker" x1="0" y1="8" x2="0" y2="${H - PAD}"/>` +
      `<circle class="demo-dot" id="ds-dot" r="5"/>`;
    mount.appendChild(svg);

    const slider = document.createElement("input");
    slider.type = "range";
    slider.min = "1";
    slider.max = "100";
    slider.value = "5";
    slider.className = "demo-slider";
    mount.appendChild(slider);

    const readout = document.createElement("p");
    readout.className = "demo-readout";
    mount.appendChild(readout);

    const dot = svg.querySelector("#ds-dot");
    const marker = svg.querySelector("#ds-marker");
    function update() {
      const n = Number(slider.value);
      const a = acc(n);
      dot.setAttribute("cx", x(n));
      dot.setAttribute("cy", y(a));
      marker.setAttribute("x1", x(n));
      marker.setAttribute("x2", x(n));
      let verdict;
      if (n <= 3) verdict = "数据太少，几乎在瞎猜——这种模型不能信。";
      else if (n <= 20) verdict = "每加一点数据，准确率都明显往上走，这是最划算的阶段。";
      else if (n <= 50) verdict = "还在涨，但慢下来了。";
      else verdict = "基本到顶了：再加数据也几乎不动了，这时候与其堆数量，不如去把数据弄得更干净、更多样。";
      readout.innerHTML = `每类 <b>${n}</b> 条 → 准确率约 <b>${Math.round(a * 100)}%</b>。${verdict}`;
    }
    slider.addEventListener("input", update);
    update();
  }

  /* ========== 2. 神经网络前向传播（点击） ========== */
  function mountForward(mount) {
    demoShell(
      mount,
      "玩一玩：点一个输入，看信号怎么传到输出",
      "点左边任意一个圆圈，看信号怎样一层层「点亮」神经元，最后得出判断——这就是「前向传播」。"
    );

    const inputs = [
      [60, 45],
      [60, 100],
      [60, 155],
    ];
    const hidden = [
      [180, 30],
      [180, 75],
      [180, 125],
      [180, 170],
    ];
    const outputs = [
      [300, 70],
      [300, 130],
    ];
    const svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("viewBox", "0 0 360 200");
    svg.classList.add("demo-svg", "demo-net");

    let edges = "";
    inputs.forEach((a, i) =>
      hidden.forEach((b, j) => {
        edges += `<line class="net-edge e-i${i}" data-from="i${i}" x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}"/>`;
      })
    );
    hidden.forEach((a, j) =>
      outputs.forEach((b) => {
        edges += `<line class="net-edge e-h${j}" x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}"/>`;
      })
    );
    const nodes = (arr, cls, prefix) =>
      arr
        .map((p, i) => `<circle class="net-node ${cls}" id="${prefix}${i}" cx="${p[0]}" cy="${p[1]}" r="15"/>`)
        .join("");

    svg.innerHTML =
      edges +
      nodes(inputs, "net-in", "n-i") +
      nodes(hidden, "net-hid", "n-h") +
      nodes(outputs, "net-out", "n-o") +
      `<text class="demo-axislab" x="60" y="195" text-anchor="middle">输入</text>` +
      `<text class="demo-axislab" x="180" y="195" text-anchor="middle">隐藏层</text>` +
      `<text class="demo-axislab" x="300" y="195" text-anchor="middle">输出</text>`;
    mount.appendChild(svg);

    const readout = document.createElement("p");
    readout.className = "demo-readout";
    readout.textContent = "（点一个左边的圆圈试试）";
    mount.appendChild(readout);

    function clear() {
      svg.querySelectorAll(".lit").forEach((n) => n.classList.remove("lit"));
    }
    inputs.forEach((_, i) => {
      svg.querySelector(`#n-i${i}`).addEventListener("click", () => {
        clear();
        svg.querySelector(`#n-i${i}`).classList.add("lit");
        readout.textContent = "信号从这个输入出发……";
        setTimeout(() => {
          svg.querySelectorAll(`.e-i${i}`).forEach((e) => e.classList.add("lit"));
          svg.querySelectorAll(".net-hid").forEach((n) => n.classList.add("lit"));
          readout.textContent = "……先传到隐藏层，每个神经元各自把收到的信号算一算……";
        }, 420);
        setTimeout(() => {
          svg.querySelectorAll(".e-h0,.e-h1,.e-h2,.e-h3").forEach((e) => e.classList.add("lit"));
          svg.querySelectorAll(".net-out").forEach((n) => n.classList.add("lit"));
          readout.textContent = "……最后汇总到输出层，给出最终判断。这一路只往前走，就叫「前向传播」。";
        }, 900);
      });
    });
  }

  /* ========== 3. 决策边界（不同算法 / 过拟合） ========== */
  function mountBoundary(mount) {
    demoShell(
      mount,
      "玩一玩：同样的点，不同算法画出不同的分界线",
      "下面有两类点，其中 2 个「捣乱点」混进了对方的地盘。换不同算法，看它们怎么把两类分开。"
    );

    const reds = [
      [60, 150],
      [85, 168],
      [50, 120],
      [95, 138],
      [72, 190],
      [115, 162],
      [190, 122],
    ]; // 最后一个是混进蓝区的红点
    const blues = [
      [205, 70],
      [225, 92],
      [182, 58],
      [240, 112],
      [212, 48],
      [172, 96],
      [120, 150],
    ]; // 最后一个是混进红区的蓝点

    const options = {
      logistic: {
        name: "逻辑回归",
        path: "M 95 205 L 250 20",
        desc: "画一条直线。简单又稳，那 2 个捣乱点会分错——但它不会为了迁就个别点，就把整条线画歪。",
      },
      tree: {
        name: "决策树",
        path: "M 150 205 L 150 110 L 255 110 L 255 20",
        desc: "用横平竖直的「台阶」分界（每一步只问一个「是不是」）。规则看得懂，但边界有点生硬。",
      },
      knn: {
        name: "K 近邻",
        path: "M 95 205 C 150 150 150 120 175 110 C 210 95 215 70 250 25",
        desc: "顺着数据的形状弯。更贴合点的分布，但也更容易被个别点带偏。",
      },
      overfit: {
        name: "过拟合（死记）",
        path:
          "M 95 205 C 150 160 130 150 120 150 C 150 150 150 130 175 120 C 200 130 190 122 190 122 C 205 105 215 70 250 25",
        desc: "为了把每个捣乱点都「圈对」，边界扭成一团。在训练的这些点上 100% 正确，但一换新数据就翻车——这就是过拟合。",
      },
    };

    const svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("viewBox", "0 0 300 220");
    svg.classList.add("demo-svg", "demo-scatter");
    const pts = (arr, cls) =>
      arr.map((p) => `<circle class="pt ${cls}" cx="${p[0]}" cy="${p[1]}" r="6"/>`).join("");
    svg.innerHTML =
      `<path class="demo-boundary" id="bd-path" d=""/>` + pts(reds, "pt-a") + pts(blues, "pt-b");
    mount.appendChild(svg);

    const tabs = document.createElement("div");
    tabs.className = "demo-tabs";
    Object.entries(options).forEach(([key, opt], idx) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "demo-tab" + (idx === 0 ? " active" : "");
      b.textContent = opt.name;
      b.dataset.key = key;
      tabs.appendChild(b);
    });
    mount.appendChild(tabs);

    const readout = document.createElement("p");
    readout.className = "demo-readout";
    mount.appendChild(readout);

    const path = svg.querySelector("#bd-path");
    function show(key) {
      const opt = options[key];
      path.setAttribute("d", opt.path);
      path.classList.toggle("boundary-overfit", key === "overfit");
      readout.innerHTML = `<b>${opt.name}</b>：${opt.desc}`;
      tabs.querySelectorAll(".demo-tab").forEach((t) => t.classList.toggle("active", t.dataset.key === key));
    }
    tabs.querySelectorAll(".demo-tab").forEach((t) =>
      t.addEventListener("click", () => show(t.dataset.key))
    );
    show("logistic");
  }

  /* ---------- 挂载 ---------- */
  const ds = document.getElementById("demo-datasize");
  if (ds) mountDataSize(ds);
  const fw = document.getElementById("demo-forward");
  if (fw) mountForward(fw);
  const bd = document.getElementById("demo-boundary");
  if (bd) mountBoundary(bd);
})();
