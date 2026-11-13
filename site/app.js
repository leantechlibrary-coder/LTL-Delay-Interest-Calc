/* 遅延損害金計算機 Web版 UI
 * Copyright (c) 2026 Lean Tech Library / AGPL-3.0 */
(function () {
  "use strict";

  const APP_VERSION = "1.4.0";
  // 入力の上限（デスクトップ版 main.py と同じ値）
  const MAX_PRINCIPAL = 999999999999;
  const MAX_RATE_PERCENT = 100;
  const E = CalcEngine;

  // ---- 元号（デスクトップ版 main.py の ERAS と同一定義。新しい順） ----
  const ERAS = [
    { name: "令和", start: { y: 2019, m: 5, d: 1 }, offset: 2018 },
    { name: "平成", start: { y: 1989, m: 1, d: 8 }, offset: 1988 },
    { name: "昭和", start: { y: 1926, m: 12, d: 25 }, offset: 1925 },
  ];

  function warekiToSeireki(eraName, wy) {
    if (eraName === "西暦") return wy;
    const era = ERAS.find((e) => e.name === eraName);
    return era ? wy + era.offset : wy;
  }

  // 西暦の日付 → [元号名, 和暦年]。昭和より前は ["西暦", 西暦年]
  function seirekiToWareki(dt) {
    for (const e of ERAS) {
      if (E.cmp(dt, e.start) >= 0) return [e.name, dt.y - e.offset];
    }
    return ["西暦", dt.y];
  }

  // dt がその元号の期間内か（例: 令和1年1月1日は平成なので false）
  function inEra(eraName, dt) {
    return eraName === "西暦" || seirekiToWareki(dt)[0] === eraName;
  }

  // ---- 和暦日付ウィジェット ----
  function createDateWidget(containerId, seirekiId) {
    const box = document.getElementById(containerId);
    const seirekiLabel = document.getElementById(seirekiId);

    const era = document.createElement("select");
    era.setAttribute("aria-label", "元号");
    for (const name of ["令和", "平成", "昭和", "西暦"]) {
      const o = document.createElement("option");
      o.value = o.textContent = name;
      era.appendChild(o);
    }

    function numInput(label, min, max) {
      const i = document.createElement("input");
      i.type = "number";
      i.inputMode = "numeric";
      i.min = min; i.max = max;
      i.className = "num";
      i.setAttribute("aria-label", label);
      i.placeholder = label;
      return i;
    }
    const yy = numInput("年", 1, 9999);
    const mm = numInput("月", 1, 12);
    const dd = numInput("日", 1, 31);

    box.appendChild(era);
    box.appendChild(yy);
    box.appendChild(mm);
    box.appendChild(dd);

    function getDate() {
      const wy = parseInt(yy.value, 10);
      const m = parseInt(mm.value, 10);
      const d = parseInt(dd.value, 10);
      if (!Number.isInteger(wy) || !Number.isInteger(m) || !Number.isInteger(d)) return null;
      if (wy < 1 || wy > (era.value === "西暦" ? 9999 : 99)) return null;
      const sy = warekiToSeireki(era.value, wy);
      if (!E.isValidDate(sy, m, d)) return null;
      const dt = { y: sy, m, d };
      return inEra(era.value, dt) ? dt : null;
    }

    function setDate(dt) {
      const [eraName, wy] = seirekiToWareki(dt);
      era.value = prevEra = eraName;
      yy.value = wy;
      mm.value = dt.m;
      dd.value = dt.d;
      update();
    }

    function update() {
      const dt = getDate();
      if (dt) {
        const [en, wy] = seirekiToWareki(dt);
        // 昭和より前は対応する元号を持っていないので和暦は出さない
        const w = era.value === "西暦" && en !== "西暦" ? `${en}${wy}年` : "";
        seirekiLabel.textContent = `（${dt.y}/${String(dt.m).padStart(2, "0")}/${String(dt.d).padStart(2, "0")}${w ? " ＝ " + w : ""}）`;
        seirekiLabel.classList.remove("bad");
      } else {
        seirekiLabel.textContent = "（無効な日付・元号の範囲外）";
        seirekiLabel.classList.add("bad");
      }
    }

    // 元号/西暦を切り替えても同じ年を指すように年の数字を換算する
    let prevEra = era.value;
    era.addEventListener("change", () => {
      const wy = parseInt(yy.value, 10);
      if (Number.isInteger(wy)) {
        const converted = warekiToSeireki(prevEra, wy) - warekiToSeireki(era.value, 0);
        if (converted >= 1) yy.value = converted;
      }
      prevEra = era.value;
    });

    for (const el of [era, yy, mm, dd]) {
      el.addEventListener("input", update);
      el.addEventListener("change", update);
    }

    return { getDate, setDate };
  }

  function todayDate() {
    const t = new Date();
    return { y: t.getFullYear(), m: t.getMonth() + 1, d: t.getDate() };
  }

  function oneYearAgo() {
    return E.addYears(todayDate(), -1);
  }

  // ---- ウィジェット初期化 ----
  const startW = createDateWidget("startDate", "startSeireki");
  const endW = createDateWidget("endDate", "endSeireki");
  let presetDates = { start: oneYearAgo(), end: todayDate() };
  startW.setDate(presetDates.start);
  endW.setDate(presetDates.end);

  // PWA復帰時: 日付が未編集（プリセットのまま）なら今日基準に更新する。
  // ユーザーが変更した日付には触れない。
  function refreshUntouchedDates() {
    const newPreset = { start: oneYearAgo(), end: todayDate() };
    if (E.cmp(newPreset.end, presetDates.end) === 0) return; // 日付が変わっていない
    const curStart = startW.getDate();
    const curEnd = endW.getDate();
    if (curStart && E.cmp(curStart, presetDates.start) === 0) startW.setDate(newPreset.start);
    if (curEnd && E.cmp(curEnd, presetDates.end) === 0) endW.setDate(newPreset.end);
    presetDates = newPreset;
  }
  window.addEventListener("pageshow", refreshUntouchedDates);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") refreshUntouchedDates();
  });

  // ---- セグメント切替 ----
  function seg(id) {
    const box = document.getElementById(id);
    const btns = [...box.querySelectorAll("button")];
    for (const b of btns) {
      b.addEventListener("click", () => {
        for (const x of btns) x.setAttribute("aria-pressed", x === b ? "true" : "false");
      });
    }
    return {
      get value() {
        return box.querySelector("button[aria-pressed=true]").dataset.v === "1";
      },
      reset(v) {
        for (const x of btns) x.setAttribute("aria-pressed", (x.dataset.v === (v ? "1" : "0")) ? "true" : "false");
      },
    };
  }
  const segFirst = seg("segFirst"); // true = 算入（既定）
  const segLeap = seg("segLeap");   // true = 考慮
  const segTrunc = seg("segTrunc"); // true = 各区間切捨て

  // ---- 入力補助 ----
  const principalEl = document.getElementById("principal");
  const rateEl = document.getElementById("rate");
  const errEl = document.getElementById("errMsg");

  principalEl.addEventListener("blur", () => {
    const v = principalEl.value.replace(/[,，\s]/g, "");
    if (/^\d+$/.test(v)) principalEl.value = Number(v).toLocaleString("ja-JP");
  });

  for (const chip of document.querySelectorAll(".chip")) {
    chip.addEventListener("click", () => { rateEl.value = chip.dataset.rate; });
  }

  function showError(msg) {
    errEl.textContent = msg;
    errEl.classList.add("show");
  }
  function clearError() {
    errEl.textContent = "";
    errEl.classList.remove("show");
  }

  // ---- 計算 ----
  const delayEl = document.getElementById("delayAmt");
  const totalEl = document.getElementById("totalAmt");
  const detailEl = document.getElementById("detail");
  const copyBtn = document.getElementById("copyBtn");
  const slipDateEl = document.getElementById("slipDate");
  let lastText = null;

  document.getElementById("calcBtn").addEventListener("click", () => {
    clearError();

    const pText = principalEl.value.replace(/[,，\s]/g, "");
    if (!pText) return showError("元本を入力してください。");
    if (!/^\d+$/.test(pText)) return showError("元本は整数で入力してください。");
    const principal = Number(pText);
    if (principal <= 0) return showError("元本は正の整数で入力してください。");
    if (principal > MAX_PRINCIPAL) return showError(`元本は${E.fmtYen(MAX_PRINCIPAL)}円以下で入力してください。`);

    const rText = rateEl.value.replace(/[,，\s]/g, "");
    if (!rText) return showError("年利を入力してください。");
    if (!/^(\d+\.?\d*|\.\d+)$/.test(rText)) return showError("年利は数値で入力してください。");
    // 計算エンジンは年利を小数4桁（％）までの値として厳密計算する（デスクトップ版と同じ上限）
    if (/\.\d{5,}$/.test(rText)) return showError("年利は小数第4位までで入力してください。");
    const ratePercent = Number(rText);
    if (ratePercent <= 0) return showError("年利は正の値を入力してください。");
    if (ratePercent > MAX_RATE_PERCENT) return showError(`年利は${MAX_RATE_PERCENT}%以下で入力してください。`);

    const startDate = startW.getDate();
    const endDate = endW.getDate();
    if (!startDate) return showError("起算日が無効です。日付を確認してください。");
    if (!endDate) return showError("支払日が無効です。日付を確認してください。");
    // 初日算入なら起算日当日の支払（1日分）も計算できる
    const includeFirstDay = segFirst.value;
    if (includeFirstDay && E.cmp(startDate, endDate) > 0) return showError("支払日は起算日以降の日付にしてください。");
    if (!includeFirstDay && E.cmp(startDate, endDate) >= 0) return showError("支払日は起算日より後の日付にしてください。");

    const r = E.calculate({
      principal,
      rate: ratePercent / 100.0,
      startDate,
      endDate,
      includeFirstDay,
      considerLeap: segLeap.value,
      truncateEach: segTrunc.value,
    });

    delayEl.innerHTML = `${E.fmtYen(r.delayInterest)}<span class="unit">円</span>`;
    totalEl.innerHTML = `${E.fmtYen(r.totalPayment)}<span class="unit">円</span>`;

    const t = todayDate();
    slipDateEl.textContent = `${t.y}/${String(t.m).padStart(2, "0")}/${String(t.d).padStart(2, "0")} 作成`;

    const header =
      `遅延損害金: ${E.fmtYen(r.delayInterest)}円\n` +
      `合計振込額: ${E.fmtYen(r.totalPayment)}円\n` +
      "──────────────────────\n";
    lastText = header + r.detailText;
    detailEl.textContent = lastText;
    copyBtn.disabled = false;
    copyBtn.textContent = "計算結果・明細をコピー";
  });

  // ---- クリア ----
  document.getElementById("clearBtn").addEventListener("click", () => {
    principalEl.value = "";
    rateEl.value = "";
    presetDates = { start: oneYearAgo(), end: todayDate() };
    startW.setDate(presetDates.start);
    endW.setDate(presetDates.end);
    segFirst.reset(true);
    segLeap.reset(true);
    segTrunc.reset(true);
    delayEl.textContent = "―";
    totalEl.textContent = "―";
    detailEl.textContent = "";
    slipDateEl.textContent = "";
    lastText = null;
    copyBtn.disabled = true;
    copyBtn.textContent = "計算結果・明細をコピー";
    clearError();
    principalEl.focus();
  });

  // ---- コピー ----
  copyBtn.addEventListener("click", async () => {
    if (!lastText) return;
    try {
      await navigator.clipboard.writeText(lastText);
      copyBtn.textContent = "コピーしました ✓";
    } catch {
      // フォールバック（clipboard API不可の環境）
      const ta = document.createElement("textarea");
      ta.value = lastText;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); copyBtn.textContent = "コピーしました ✓"; }
      catch { copyBtn.textContent = "コピーできませんでした"; }
      document.body.removeChild(ta);
    }
    setTimeout(() => { copyBtn.textContent = "計算結果・明細をコピー"; }, 1800);
  });

  // ---- About ----
  const dlg = document.getElementById("aboutDlg");
  document.getElementById("aboutBtn").addEventListener("click", () => dlg.showModal());
  document.getElementById("aboutClose").addEventListener("click", () => dlg.close());
  dlg.addEventListener("click", (ev) => { if (ev.target === dlg) dlg.close(); });

  // ---- バージョン表示・Service Worker ----
  document.getElementById("verLabel").textContent = `v${APP_VERSION}`;

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("sw.js").catch(() => {});
    });
  }
})();
