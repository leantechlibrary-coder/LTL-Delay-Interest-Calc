"""
計算エンジンの検証スクリプト（依存ライブラリなし）

  python tests/check_engines.py

1. 手計算で確かめた代表例と一致すること
2. calc_engine.py の年数・日数が、1日ずつ数える別実装と一致すること
3. site/calc.js が calc_engine.py と全項目・明細文まで一致すること（node がある場合）
"""

import calendar
import json
import random
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from calc_engine import calculate  # noqa: E402

# (元本, 年利, 起算日, 支払日, 初日算入, 閏年考慮, 各区間切り捨て) → 遅延損害金
KNOWN = [
    # 満1年ちょうど（応当日の前日に満了）
    ((100_000_000, 0.03, date(2023, 7, 1), date(2024, 6, 30), True, True, True), 3_000_000),
    # 1年 + 1日（その1日は閏年 2024 年に属する → 1/366）
    ((100_000_000, 0.03, date(2023, 7, 1), date(2024, 7, 1), True, True, True), 3_008_196),
    # 初日不算入なら1日ずれて満1年
    ((100_000_000, 0.03, date(2023, 6, 30), date(2024, 6, 30), False, True, True), 3_000_000),
    # 2/29 開始は翌年 2/28 に満了、3/1 が端数1日（平年 → 1/365）
    ((100_000_000, 0.03, date(2024, 2, 29), date(2025, 2, 28), True, True, True), 3_000_000),
    ((100_000_000, 0.03, date(2024, 2, 29), date(2025, 3, 1), True, True, True), 3_008_219),
    # 起算日当日の支払（1日分）
    ((1_000_000, 0.03, date(2025, 4, 1), date(2025, 4, 1), True, True, True), 82),
    # 年365日日割特約: 100万 × 3% × 366/365 = 30,082.19…
    ((1_000_000, 0.03, date(2024, 1, 1), date(2024, 12, 31), True, False, True), 30_082),
    # 端数処理の違い: 平年 184日分 31,117.85… + 閏年 181日分 30,526.96…
    #   各区間切り捨て: 31,117 + 30,526 = 61,643
    #   合算後切り捨て: 31,117.8 + 30,526.9 = 61,644.7 → 61,644
    ((1_234_567, 0.05, date(2023, 7, 1), date(2024, 6, 29), True, True, True), 61_643),
    ((1_234_567, 0.05, date(2023, 7, 1), date(2024, 6, 29), True, True, False), 61_644),
]


def reference_days(start, end, include_first_day):
    """年数と平年/閏年の日数を、1日ずつ数えて求める"""
    first = start if include_first_day else start + timedelta(days=1)

    def year_end(n):
        y = first.year + n
        if (first.month, first.day) == (2, 29) and not calendar.isleap(y):
            return date(y, 2, 28)
        return date(y, first.month, first.day) - timedelta(days=1)

    years = 0
    while year_end(years + 1) <= end:
        years += 1
    day = first if years == 0 else year_end(years) + timedelta(days=1)
    normal = leap = 0
    while day <= end:
        if calendar.isleap(day.year):
            leap += 1
        else:
            normal += 1
        day += timedelta(days=1)
    return years, normal, leap


def build_cases():
    random.seed(1)
    periods = []
    # 年末年始・2月末をまたぐ起算日 × 短期と応当日前後の支払日
    for base in [date(2019, 12, 25), date(2023, 2, 20), date(2024, 2, 25), date(2027, 12, 28)]:
        for i in range(12):
            start = base + timedelta(days=i)
            spans = list(range(0, 40)) + [k for y in (1, 2, 3, 4, 5, 8) for k in range(365 * y - 4, 365 * y + 8)]
            periods += [(start, start + timedelta(days=j)) for j in spans]
    for _ in range(3000):
        start = date(1927, 1, 1) + timedelta(days=random.randrange(38000))
        periods.append((start, start + timedelta(days=random.randrange(0, 9000))))

    cases = []
    for start, end in periods:
        for include in (True, False):
            if not include and start == end:
                continue
            for principal, rate in ((1_000_000, 0.03), (123_456_789, 0.146), (999_999_999_999, 0.000125)):
                for leap in (True, False):
                    for each in (True, False):
                        cases.append((principal, rate, start, end, include, leap, each))
    return cases


def main():
    failures = 0

    for args, expected in KNOWN:
        got = calculate(*args).delay_interest
        if got != expected:
            failures += 1
            print(f"NG 代表例: {args} → {got}（期待 {expected}）")
    print(f"代表例 {len(KNOWN)} 件")

    cases = build_cases()
    payload = []
    for args in cases:
        principal, rate, start, end, include, leap, each = args
        r = calculate(*args)
        if leap and (r.full_years, r.normal_days, r.leap_days) != reference_days(start, end, include):
            failures += 1
            print(f"NG 日数: {args}")
        payload.append({
            "args": {
                "principal": principal, "rate": rate,
                "startDate": {"y": start.year, "m": start.month, "d": start.day},
                "endDate": {"y": end.year, "m": end.month, "d": end.day},
                "includeFirstDay": include, "considerLeap": leap, "truncateEach": each,
            },
            "expected": [r.full_years, r.normal_days, r.leap_days, r.total_days,
                         r.delay_interest, r.total_payment, r.detail_text],
        })
    print(f"別実装との日数照合 {len(cases)} 件")

    node = shutil.which("node")
    if node:
        out = subprocess.run(
            [node, str(ROOT / "tests" / "run_calc.js")],
            input=json.dumps(payload), capture_output=True, text=True, encoding="utf-8",
        )
        print(out.stdout.strip())
        if out.returncode != 0:
            failures += 1
            print(out.stderr.strip())
    else:
        print("node が見つからないため calc.js との照合は省略")

    print("NG あり" if failures else "すべて一致")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
