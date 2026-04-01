"""
遅延損害金計算エンジン
裁判所方式（端数期間暦年閏年説）準拠

計算式:
  特約なし: 元本 × 年利 × (年 + 平年日÷365 + 閏年日÷366)
  年365日日割: 元本 × 年利 × 総日数÷365

日数カウント:
  初日算入: 起算日そのまま。年計算は応当日で区切る。
  初日不算入: 翌日を起算日とする。
  端数期間の暦年分割: 最初のセグメントは起算日含む(+1)、
                     以降は年初からのdate diff。
"""

from dataclasses import dataclass
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import calendar
import math


@dataclass
class CalcResult:
    principal: int
    rate: float
    start_date: date
    end_date: date
    include_first_day: bool
    consider_leap: bool
    truncate_each: bool
    full_years: int
    normal_days: int
    leap_days: int
    total_days: int
    amount_years: float
    amount_normal: float
    amount_leap: float
    delay_interest: int
    total_payment: int
    detail_text: str


def is_leap_year(year: int) -> bool:
    return calendar.isleap(year)


def count_full_years(effective_start: date, end_date: date):
    full_years = 0
    while effective_start + relativedelta(years=full_years + 1) <= end_date:
        full_years += 1
    remainder_start = effective_start + relativedelta(years=full_years)
    return full_years, remainder_start


def split_days_by_leap(remainder_start: date, end_date: date):
    """
    端数期間を暦年ごとに平年/閏年に分割。
    各セグメントは両端を含む日数(+1)で計算する。
    ただし隣接セグメントの境界日(12/31と1/1)は重複しないよう、
    各セグメントの起算日を含め終了日も含める方式。
    """
    if remainder_start >= end_date:
        return 0, 0

    normal_days = 0
    leap_days = 0
    current = remainder_start

    while current <= end_date:
        year_end = date(current.year, 12, 31)
        segment_end = min(year_end, end_date)
        # 起算日と終了日の両方を含む日数
        days_in_segment = (segment_end - current).days + 1

        if is_leap_year(current.year):
            leap_days += days_in_segment
        else:
            normal_days += days_in_segment

        if segment_end >= end_date:
            break
        current = date(current.year + 1, 1, 1)

    return normal_days, leap_days


def calculate(
    principal: int,
    rate: float,
    start_date: date,
    end_date: date,
    include_first_day: bool = False,
    consider_leap: bool = True,
    truncate_each: bool = True,
) -> CalcResult:
    if include_first_day:
        effective_start = start_date
        total_days = (end_date - start_date).days + 1
    else:
        effective_start = start_date + timedelta(days=1)
        total_days = (end_date - start_date).days

    if total_days <= 0:
        return CalcResult(
            principal=principal, rate=rate,
            start_date=start_date, end_date=end_date,
            include_first_day=include_first_day,
            consider_leap=consider_leap, truncate_each=truncate_each,
            full_years=0, normal_days=0, leap_days=0, total_days=0,
            amount_years=0, amount_normal=0, amount_leap=0,
            delay_interest=0, total_payment=principal,
            detail_text="期間が0日以下です。"
        )

    details = []
    details.append(f"元本: {principal:,}円")
    details.append(f"年利: {rate*100}%")
    details.append(f"起算日: {start_date} ({'初日算入' if include_first_day else '初日不算入'})")
    details.append(f"計算開始日: {effective_start}")
    details.append(f"支払日: {end_date}")
    details.append(f"総日数: {total_days}日")
    details.append("")

    full_years, remainder_start = count_full_years(effective_start, end_date)

    if not consider_leap:
        amount_total = principal * rate * total_days / 365
        details.append("【計算方法: 年365日日割特約（閏年無視）】")
        details.append(f"  {principal:,} × {rate} × {total_days}/365 = {amount_total:,.1f}")
        delay_interest = math.floor(amount_total)
        details.append(f"  遅延損害金: {delay_interest:,}円")
        details.append(f"  合計振込額: {principal + delay_interest:,}円")

        return CalcResult(
            principal=principal, rate=rate,
            start_date=start_date, end_date=end_date,
            include_first_day=include_first_day,
            consider_leap=consider_leap, truncate_each=truncate_each,
            full_years=0, normal_days=total_days, leap_days=0,
            total_days=total_days,
            amount_years=0, amount_normal=amount_total, amount_leap=0,
            delay_interest=delay_interest,
            total_payment=principal + delay_interest,
            detail_text="\n".join(details)
        )

    else:
        normal_days, leap_days = split_days_by_leap(remainder_start, end_date)
        amount_years = principal * rate * full_years
        amount_normal = principal * rate * normal_days / 365 if normal_days > 0 else 0.0
        amount_leap = principal * rate * leap_days / 366 if leap_days > 0 else 0.0

        details.append("【計算方法: 特約なし（端数期間暦年閏年説）】")
        details.append(f"  年に満つる期間: {full_years}年")
        if full_years > 0:
            year_end_date = effective_start + relativedelta(years=full_years) - timedelta(days=1)
            details.append(f"    {effective_start} → {year_end_date}")
        details.append(f"  端数期間: {remainder_start} → {end_date}")
        details.append(f"    平年日数: {normal_days}日, 閏年日数: {leap_days}日")
        details.append("")

        if full_years > 0:
            details.append(f"  ① 年単位: {principal:,} × {rate} × {full_years} = {amount_years:,.1f}")
        else:
            details.append(f"  ① 年単位: なし")
        if normal_days > 0:
            details.append(f"  ② 平年分: {principal:,} × {rate} × {normal_days}/365 = {amount_normal:,.1f}")
        else:
            details.append(f"  ② 平年分: なし")
        if leap_days > 0:
            details.append(f"  ③ 閏年分: {principal:,} × {rate} × {leap_days}/366 = {amount_leap:,.1f}")
        else:
            details.append(f"  ③ 閏年分: なし")

        if truncate_each:
            # 各区間ごとに円未満切り捨て（謙抑的方式）
            fy = math.floor(amount_years)
            fn = math.floor(amount_normal)
            fl = math.floor(amount_leap)
            delay_interest = fy + fn + fl
            details.append("")
            parts = []
            if full_years > 0: parts.append(f"①{fy:,}")
            if normal_days > 0: parts.append(f"②{fn:,}")
            if leap_days > 0: parts.append(f"③{fl:,}")
            details.append(f"  各区間切り捨て: {' + '.join(parts)}")
        else:
            # 東京地裁執行部方式:
            # 各区間を小数点第2位で切り捨て（小数点1位まで残す）→
            # 合算 → 小数点第1位以下を切り捨て
            ry = math.floor(amount_years * 10) / 10
            rn = math.floor(amount_normal * 10) / 10
            rl = math.floor(amount_leap * 10) / 10
            raw_total = ry + rn + rl
            delay_interest = math.floor(raw_total)
            details.append("")
            parts = []
            if full_years > 0: parts.append(f"①{ry:,.1f}")
            if normal_days > 0: parts.append(f"②{rn:,.1f}")
            if leap_days > 0: parts.append(f"③{rl:,.1f}")
            details.append(f"  合算(小数1位): {' + '.join(parts)} = {raw_total:,.1f}")

        details.append(f"  遅延損害金: {delay_interest:,}円")
        details.append(f"  合計振込額: {principal + delay_interest:,}円")

        return CalcResult(
            principal=principal, rate=rate,
            start_date=start_date, end_date=end_date,
            include_first_day=include_first_day,
            consider_leap=consider_leap, truncate_each=truncate_each,
            full_years=full_years,
            normal_days=normal_days, leap_days=leap_days,
            total_days=total_days,
            amount_years=amount_years,
            amount_normal=amount_normal,
            amount_leap=amount_leap,
            delay_interest=delay_interest,
            total_payment=principal + delay_interest,
            detail_text="\n".join(details)
        )
