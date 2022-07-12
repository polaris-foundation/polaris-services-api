from datetime import date, timedelta


def offset_date(days: int = 0, weeks: int = 0, months: int = 0, years: int = 0) -> str:
    """Returns a date offset from today by the specified days, weeks, months, and years
    (negative for past)
    Result is a string with format YYYY-MM-DD
    """
    today = date.today()
    year = today.year + years
    month = today.month + months
    year, month = year + (month - 1) // 12, (month - 1) % 12 + 1
    days = today.day + days + weeks * 7 - 1
    target_date = date(year=year, month=month, day=1) + timedelta(days=days)
    return target_date.strftime("%Y-%m-%d")
