// check_engines.py から呼ばれる。標準入力のケースを site/calc.js で計算して期待値と比べる
const path = require("path");
const E = require(path.join(__dirname, "..", "site", "calc.js"));

let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => { input += chunk; });
process.stdin.on("end", () => {
  const cases = JSON.parse(input);
  let bad = 0;
  for (const c of cases) {
    const r = E.calculate(c.args);
    const got = [r.fullYears, r.normalDays, r.leapDays, r.totalDays, r.delayInterest, r.totalPayment, r.detailText];
    if (JSON.stringify(got) !== JSON.stringify(c.expected)) {
      if (bad++ < 5) console.log("NG calc.js:", JSON.stringify(c.args), "\n", got, "\n", c.expected);
    }
  }
  console.log(`calc.js との照合 ${cases.length} 件、不一致 ${bad} 件`);
  process.exit(bad ? 1 : 0);
});
