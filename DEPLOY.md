/*
 * 遅延損害金計算エンジン (JavaScript port)
 * 裁判所方式（端数期間暦年閏年説）準拠
 * Python版 calc_engine.py と数値完全一致を検証済み
 *
 * 計算式:
 *   特約なし: 元本 × 年利 × (年 + 平年日÷365 + 閏年日÷366)
 *   年365日日割: 元本 × 年利 × 総日数÷365
 *
 * Copyright (c) 2026 Lean Tech Library
 * License: AGPL-3.0
 * Source: https://github.com/leantechlibrary-coder/LTL-Delay-Interest-Calc
 */
(function (global) {
  "use strict";

  // ---- 日付ユーティリティ（タイムゾーン非依存: {y, m, d} プレーンオブジェクト） ----

  function isLeapYear(y) {
    return (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;
  }

  const DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

  function daysInMonth(y, m) {
    if (m === 2 && isLeapYear(y)) return 29;
    return DAYS_IN_MONTH[m - 1];
  }

  function isValidDate(y, m, d) {
    return (
      Number.isInteger(y) && Number.isInteger(m) && Number.isInteger(d) &&
      m >= 1 && m <= 12 && d >= 1 && d <= daysInMonth(y, m)
    );
  }

  // 通算日数（proleptic Gregorian, epoch任意）— 差分専用
  function toOrdinal(dt) {
    // Rata Die (0001-01-01 = 1) 相当
    const y = dt.y - 1;
    let days = y * 365 + Math.floor(y / 4) - Math.floor(y / 100) + Math.floor(y / 400);
    for (let m = 1; m < dt.m; m++) days += daysInMonth(dt.y, m);
    return days + dt.d;
  }

  function diffDays(a, b) {
    // (a - b) in days
    return toOrdinal(a) - toOrdinal(b);
  }

  function addDays(dt, n) {
    let { y, m, d } = dt;
    d += n;
    while (d > daysInMonth(y, m)) {
      d -= daysInMonth(y, m);
      m += 1;
      if (m > 12) { m = 1; y += 1; }
    }
    while (d < 1) {
      m -= 1;
      if (m < 1) { m = 12; y -= 1; }
      d += daysInMonth(y, m);
    }
    return { y, m, d };
  }

  // dateutil.relativedelta(years=n) と同一挙動:
  // 応当日が存在しない場合（2/29 → 平年）は月末（2/28）に丸める
  function addYears(dt, n) {
    const y = dt.y + n;
    const d = Math.min(dt.d, daysInMonth(y, dt.m));
    return { y, m: dt.m, d };
  }

  function cmp(a, b) {
    if (a.y !== b.y) return a.y - b.y;
    if (a.m !== b.m) return a.m - b.m;
    return a.d - b.d;
  }

  function fmtDate(dt) {
    const p = (n, w) => String(n).padStart(w, "0");
    return `${p(dt.y, 4)}-${p(dt.m, 2)}-${p(dt.d, 2)}`;
  }

  function fmtYen(n) {
    return Math.trunc(n).toLocaleString("ja-JP");
  }

  function fmtNum1(x) {
    // Python の f"{x:,.1f}" 相当（小数1位固定・桁区切り）
    const neg = x < 0;
    const v = Math.abs(x);
    const s = v.toFixed(1);
    const [int_, frac] = s.split(".");
    const grouped = int_.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    return (neg ? "-" : "") + grouped + "." + frac;
  }

  // ---- エンジン本体（calc_engine.py と同一構造・同一演算順序） ----

  function countFullYears(effectiveStart, endDate) {
    let fullYears = 0;
    while (cmp(addYears(effectiveStart, fullYears + 1), endDate) <= 0) {
      fullYears += 1;
    }
    const remainderStart = addYears(effectiveStart, fullYears);
    return [fullYears, remainderStart];
  }

  function splitDaysByLeap(remainderStart, endDate) {
    if (cmp(remainderStart, endDate) >= 0) return [0, 0];

    let normalDays = 0;
    let leapDays = 0;
    let current = remainderStart;

    while (cmp(current, endDate) <= 0) {
      const yearEnd = { y: current.y, m: 12, d: 31 };
      const segmentEnd = cmp(yearEnd, endDate) < 0 ? yearEnd : endDate;
      const daysInSegment = diffDays(segmentEnd, current) + 1;

      if (isLeapYear(current.y)) leapDays += daysInSegment;
      else normalDays += daysInSegment;

      if (cmp(segmentEnd, endDate) >= 0) break;
      current = { y: current.y + 1, m: 1, d: 1 };
    }
    return [normalDays, leapDays];
  }

  /**
   * @param {Object} p
   * @param {number} p.principal   元本（整数円）
   * @param {number} p.rate        年利（小数, 3% → 0.03）
   * @param {{y,m,d}} p.startDate  起算日
   * @param {{y,m,d}} p.endDate    支払日
   * @param {boolean} p.includeFirstDay 初日算入
   * @param {boolean} p.considerLeap    閏年考慮（false = 年365日日割特約）
   * @param {boolean} p.truncateEach    各区間ごと切り捨て（false = 東京地裁執行部方式）
   * @param {string}  [p.ratePercentText] 明細表示用の利率文字列（例 "3"）
   */
  function calculate(p) {
    const {
      principal, rate, startDate, endDate,
      includeFirstDay = false, considerLeap = true, truncateEach = true,
    } = p;
    const rateText = p.ratePercentText != null ? p.ratePercentText : String(rate * 100);

    let effectiveStart, totalDays;
    if (includeFirstDay) {
      effectiveStart = startDate;
      totalDays = diffDays(endDate, startDate) + 1;
    } else {
      effectiveStart = addDays(startDate, 1);
      totalDays = diffDays(endDate, startDate);
    }

    const base = {
      principal, rate, startDate, endDate,
      includeFirstDay, considerLeap, truncateEach,
    };

    if (totalDays <= 0) {
      return {
        ...base,
        fullYears: 0, normalDays: 0, leapDays: 0, totalDays: 0,
        amountYears: 0, amountNormal: 0, amountLeap: 0,
        delayInterest: 0, totalPayment: principal,
        detailText: "期間が0日以下です。",
      };
    }

    const details = [];
    details.push(`元本: ${fmtYen(principal)}円`);
    details.push(`年利: ${rateText}%`);
    details.push(`起算日: ${fmtDate(startDate)} (${includeFirstDay ? "初日算入" : "初日不算入"})`);
    details.push(`計算開始日: ${fmtDate(effectiveStart)}`);
    details.push(`支払日: ${fmtDate(endDate)}`);
    details.push(`総日数: ${totalDays}日`);
    details.push("");

    const [fullYears, remainderStart] = countFullYears(effectiveStart, endDate);

    if (!considerLeap) {
      const amountTotal = principal * rate * totalDays / 365;
      details.push("【計算方法: 年365日日割特約（閏年無視）】");
      details.push(`  ${fmtYen(principal)} × ${rateText}% × ${totalDays}/365 = ${fmtNum1(amountTotal)}`);
      const delayInterest = Math.floor(amountTotal);
      details.push(`  遅延損害金: ${fmtYen(delayInterest)}円`);
      details.push(`  合計振込額: ${fmtYen(principal + delayInterest)}円`);

      return {
        ...base,
        fullYears: 0, normalDays: totalDays, leapDays: 0, totalDays,
        amountYears: 0, amountNormal: amountTotal, amountLeap: 0,
        delayInterest,
        totalPayment: principal + delayInterest,
        detailText: details.join("\n"),
      };
    }

    const [normalDays, leapDays] = splitDaysByLeap(remainderStart, endDate);
    const amountYears = principal * rate * fullYears;
    const amountNormal = normalDays > 0 ? principal * rate * normalDays / 365 : 0.0;
    const amountLeap = leapDays > 0 ? principal * rate * leapDays / 366 : 0.0;

    details.push("【計算方法: 特約なし（端数期間暦年閏年説）】");
    details.push(`  年に満つる期間: ${fullYears}年`);
    if (fullYears > 0) {
      const yearEndDate = addDays(addYears(effectiveStart, fullYears), -1);
      details.push(`    ${fmtDate(effectiveStart)} → ${fmtDate(yearEndDate)}`);
    }
    details.push(`  端数期間: ${fmtDate(remainderStart)} → ${fmtDate(endDate)}`);
    details.push(`    平年日数: ${normalDays}日, 閏年日数: ${leapDays}日`);
    details.push("");

    if (fullYears > 0) {
      details.push(`  ① 年単位: ${fmtYen(principal)} × ${rateText}% × ${fullYears} = ${fmtNum1(amountYears)}`);
    } else {
      details.push("  ① 年単位: なし");
    }
    if (normalDays > 0) {
      details.push(`  ② 平年分: ${fmtYen(principal)} × ${rateText}% × ${normalDays}/365 = ${fmtNum1(amountNormal)}`);
    } else {
      details.push("  ② 平年分: なし");
    }
    if (leapDays > 0) {
      details.push(`  ③ 閏年分: ${fmtYen(principal)} × ${rateText}% × ${leapDays}/366 = ${fmtNum1(amountLeap)}`);
    } else {
      details.push("  ③ 閏年分: なし");
    }

    let delayInterest;
    if (truncateEach) {
      const fy = Math.floor(amountYears);
      const fn = Math.floor(amountNormal);
      const fl = Math.floor(amountLeap);
      delayInterest = fy + fn + fl;
      details.push("");
      const parts = [];
      if (fullYears > 0) parts.push(`①${fmtYen(fy)}`);
      if (normalDays > 0) parts.push(`②${fmtYen(fn)}`);
      if (leapDays > 0) parts.push(`③${fmtYen(fl)}`);
      details.push(`  各区間切り捨て: ${parts.join(" + ")}`);
    } else {
      // 東京地裁執行部方式: 各区間を小数第2位切り捨て → 合算 → 円未満切り捨て
      const ry = Math.floor(amountYears * 10) / 10;
      const rn = Math.floor(amountNormal * 10) / 10;
      const rl = Math.floor(amountLeap * 10) / 10;
      const rawTotal = ry + rn + rl;
      delayInterest = Math.floor(rawTotal);
      details.push("");
      const parts = [];
      if (fullYears > 0) parts.push(`①${fmtNum1(ry)}`);
      if (normalDays > 0) parts.push(`②${fmtNum1(rn)}`);
      if (leapDays > 0) parts.push(`③${fmtNum1(rl)}`);
      details.push(`  合算(小数1位): ${parts.join(" + ")} = ${fmtNum1(rawTotal)}`);
    }

    details.push(`  遅延損害金: ${fmtYen(delayInterest)}円`);
    details.push(`  合計振込額: ${fmtYen(principal + delayInterest)}円`);

    return {
      ...base,
      fullYears, normalDays, leapDays, totalDays,
      amountYears, amountNormal, amountLeap,
      delayInterest,
      totalPayment: principal + delayInterest,
      detailText: details.join("\n"),
    };
  }

  const api = {
    calculate, isLeapYear, isValidDate, daysInMonth,
    addDays, addYears, diffDays, cmp, fmtDate, fmtYen,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api; // Node (検証用)
  }
  global.CalcEngine = api; // ブラウザ
})(typeof globalThis !== "undefined" ? globalThis : this);
