"""
遅延損害金計算エンジン
裁判所方式（端数期間暦年閏年説）準拠

計算式:
  特約なし: 元本 × 年利 × (年 + 平年日÷365 + 閏年日÷366)
  年365日日割: 元本 × 年利 × 総日数÷365

日数カウント:
  初日算入: 起算日そのまま。初日不算入: 翌日を計算開始日とする。
  計算開始日・支払日はどちらも日数に含める。
  年に満つる期間は応当日の前日に満了する（民法143条2項）。
    例: 7/1 開始 → 翌年 6/30 で満1年、端数期間は 7/1 から。
    2/29 開始で応当日がない年は、その月の末日（2/28）に満了する（同項ただし書）。
  端数期間は暦年ごとに区切り、両端の日を含めて数える。

端数処理（円未満切り捨て）は有理数（Fraction）で厳密に行う。
  浮動小数点のままだと、例えば 1,137,049.4 + 258,561.9 + 12,426.7 が
  1,408,037.999… になって切り捨てで1円少なくなる。
  CalcResult の amount_* は表示用の float（値は厳密計算と同じものを float にしたもの）。
"""

from dataclasses import dataclass
from datetime import date, timedelta
import calendar
import math
from fractions import Fraction


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


def exact_rate(rate: float) -> Fraction:
    """年利（小数）を有理数に戻す。画面の利率は小数4桁まで（％）なので、分母 10**6 以内で元の値に戻る"""
    return Fraction(rate).limit_denominator(10**6)


def is_leap_year(year: int) -> bool:
    return calendar.isleap(year)


def full_year_end(effective_start: date, years: int) -> date:
    """計算開始日から years 年の期間が満了する日（その日を含む）。民法143条2項"""
    year = effective_start.year + years
    try:
        return effective_start.replace(year=year) - timedelta(days=1)
    except ValueError:
        # 2/29 開始で応当日がない年 → その月の末日に満了
        return date(year, 2, 28)


def count_full_years(effective_start: date, end_date: date):
    """年に満つる年数と、端数期間の開始日を返す"""
    full_years = 0
    while full_year_end(effective_start, full_years + 1) <= end_date:
        full_years += 1
    if full_years == 0:
        return 0, effective_start
    return full_years, full_year_end(effective_start, full_years) + timedelta(days=1)


def split_days_by_leap(remainder_start: date, end_date: date):
    """
    端数期間（remainder_start〜end_date、両端を含む）を
    暦年ごとに平年/閏年の日数に分ける。
    """
    if remainder_start > end_date:
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

    r = exact_rate(rate)

    details = []
    details.append(f"元本: {principal:,}円")
    details.append(f"年利: {float(r * 100):g}%")
    details.append(f"起算日: {start_date} ({'初日算入' if include_first_day else '初日不算入'})")
    details.append(f"計算開始日: {effective_start}")
    details.append(f"支払日: {end_date}")
    details.append(f"総日数: {total_days}日")
    details.append("")

    if not consider_leap:
        exact_total = Fraction(principal) * r * total_days / 365
        amount_total = float(exact_total)
        details.append("【計算方法: 年365日日割特約（閏年無視）】")
        details.append(f"  {principal:,} × {rate} × {total_days}/365 = {amount_total:,.1f}")
        delay_interest = math.floor(exact_total)
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
        full_years, remainder_start = count_full_years(effective_start, end_date)
        normal_days, leap_days = split_days_by_leap(remainder_start, end_date)
        exact_years = Fraction(principal) * r * full_years
        exact_normal = Fraction(principal) * r * normal_days / 365
        exact_leap = Fraction(principal) * r * leap_days / 366
        amount_years = float(exact_years)
        amount_normal = float(exact_normal)
        amount_leap = float(exact_leap)

        details.append("【計算方法: 特約なし（端数期間暦年閏年説）】")
        details.append(f"  年に満つる期間: {full_years}年")
        if full_years > 0:
            details.append(f"    {effective_start} → {full_year_end(effective_start, full_years)}")
        if remainder_start <= end_date:
            details.append(f"  端数期間: {remainder_start} → {end_date}")
        else:
            details.append("  端数期間: なし")
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
            fy = math.floor(exact_years)
            fn = math.floor(exact_normal)
            fl = math.floor(exact_leap)
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
            ry = Fraction(math.floor(exact_years * 10), 10)
            rn = Fraction(math.floor(exact_normal * 10), 10)
            rl = Fraction(math.floor(exact_leap * 10), 10)
            raw_total = ry + rn + rl
            delay_interest = math.floor(raw_total)
            ry, rn, rl, raw_total = float(ry), float(rn), float(rl), float(raw_total)
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
