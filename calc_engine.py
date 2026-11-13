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

金額はすべて整数演算で厳密に切り捨てる（浮動小数点の誤差で1円ずれないように）。
  明細に出す各区間の金額は小数第2位以下を切り捨てた値（四捨五入しない）。

site/calc.js はこのファイルと同じ結果・同じ明細文を返す（tests/check_engines.py で照合）。
"""

from dataclasses import dataclass
from datetime import date, timedelta
import calendar

RATE_DEN = 10**6  # 年利は 10^6 分の整数で持つ（％で小数4桁まで）


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
    delay_interest: int
    total_payment: int
    detail_text: str


def rate_num(rate: float) -> int:
    """年利（小数）を 10^6 分の整数に戻す。3% → 30000"""
    return round(rate * RATE_DEN)


def fmt_rate(num: int) -> str:
    """10^6 分の整数の年利を ％ 表記にする。30000 → "3"、146000 → "14.6" """
    whole, frac = divmod(num, 10**4)
    frac_text = f"{frac:04d}".rstrip("0")
    return f"{whole}.{frac_text}" if frac_text else str(whole)


def fmt_tenths(tenths: int) -> str:
    """10倍した整数を小数1位の金額表記にする。81967 → "8,196.7" """
    return f"{tenths // 10:,}.{tenths % 10}"


def floor_term(principal: int, num: int, days: int, denom: int, scale: int = 1) -> int:
    """floor(元本 × 年利 × 日数 × scale ÷ 分母)"""
    return principal * num * days * scale // (RATE_DEN * denom)


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
    normal_days = 0
    leap_days = 0
    current = remainder_start

    while current <= end_date:
        segment_end = min(date(current.year, 12, 31), end_date)
        days_in_segment = (segment_end - current).days + 1

        if calendar.isleap(current.year):
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
    include_first_day: bool = True,
    consider_leap: bool = True,
    truncate_each: bool = True,
) -> CalcResult:
    if include_first_day:
        effective_start = start_date
        total_days = (end_date - start_date).days + 1
    else:
        effective_start = start_date + timedelta(days=1)
        total_days = (end_date - start_date).days

    base = dict(
        principal=principal, rate=rate,
        start_date=start_date, end_date=end_date,
        include_first_day=include_first_day,
        consider_leap=consider_leap, truncate_each=truncate_each,
    )

    if total_days <= 0:
        return CalcResult(
            **base,
            full_years=0, normal_days=0, leap_days=0, total_days=0,
            delay_interest=0, total_payment=principal,
            detail_text="期間が0日以下です。"
        )

    num = rate_num(rate)
    rate_text = fmt_rate(num)

    details = []
    details.append(f"元本: {principal:,}円")
    details.append(f"年利: {rate_text}%")
    details.append(f"起算日: {start_date} ({'初日算入' if include_first_day else '初日不算入'})")
    details.append(f"計算開始日: {effective_start}")
    details.append(f"支払日: {end_date}")
    details.append(f"総日数: {total_days}日")
    details.append("")

    if not consider_leap:
        tenths = floor_term(principal, num, total_days, 365, 10)
        delay_interest = tenths // 10
        details.append("【計算方法: 年365日日割特約（閏年無視）】")
        details.append(
            f"  {principal:,} × {rate_text}% × {total_days}/365 = {fmt_tenths(tenths)}"
            f" → 円未満切り捨て {delay_interest:,}円"
        )
        full_years, normal_days, leap_days = 0, total_days, 0

    else:
        full_years, remainder_start = count_full_years(effective_start, end_date)
        normal_days, leap_days = split_days_by_leap(remainder_start, end_date)
        # 各区間の金額を10倍した整数（＝小数1位まで、第2位以下切り捨て）
        ty = floor_term(principal, num, full_years, 1, 10)
        tn = floor_term(principal, num, normal_days, 365, 10)
        tl = floor_term(principal, num, leap_days, 366, 10)

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
            details.append(f"  ① 年単位: {principal:,} × {rate_text}% × {full_years} = {fmt_tenths(ty)}")
        else:
            details.append("  ① 年単位: なし")
        if normal_days > 0:
            details.append(f"  ② 平年分: {principal:,} × {rate_text}% × {normal_days}/365 = {fmt_tenths(tn)}")
        else:
            details.append("  ② 平年分: なし")
        if leap_days > 0:
            details.append(f"  ③ 閏年分: {principal:,} × {rate_text}% × {leap_days}/366 = {fmt_tenths(tl)}")
        else:
            details.append("  ③ 閏年分: なし")
        details.append("")

        used = [(full_years, "①", ty), (normal_days, "②", tn), (leap_days, "③", tl)]
        if truncate_each:
            # 各区間ごとに円未満切り捨て（謙抑的方式）
            delay_interest = ty // 10 + tn // 10 + tl // 10
            parts = [f"{mark}{t // 10:,}" for n, mark, t in used if n > 0]
            details.append(f"  各区間切り捨て: {' + '.join(parts)} = {delay_interest:,}円")
        else:
            # 東京地裁執行部方式: 各区間を小数第2位で切り捨て → 合算 → 円未満切り捨て
            total_tenths = ty + tn + tl
            delay_interest = total_tenths // 10
            parts = [f"{mark}{fmt_tenths(t)}" for n, mark, t in used if n > 0]
            details.append(
                f"  合算(小数1位): {' + '.join(parts)} = {fmt_tenths(total_tenths)}"
                f" → 円未満切り捨て {delay_interest:,}円"
            )

    return CalcResult(
        **base,
        full_years=full_years, normal_days=normal_days, leap_days=leap_days,
        total_days=total_days,
        delay_interest=delay_interest,
        total_payment=principal + delay_interest,
        detail_text="\n".join(details)
    )
