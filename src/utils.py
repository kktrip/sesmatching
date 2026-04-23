import re


def _parse_rate_yen(rate_str) -> tuple:
    """単価文字列から (min_yen, max_yen) を返す。パース失敗時は (None, None)。"""
    if not rate_str:
        return (None, None)

    s = rate_str.replace(",", "").replace("，", "")

    if "万" in s:
        unit = 10000
    elif "千" in s:
        unit = 1000
    else:
        unit = 1

    sep_match = re.search(r"[〜~～]", s)

    if not sep_match:
        numbers = re.findall(r"\d+(?:\.\d+)?", s)
        if not numbers:
            return (None, None)
        val = int(float(numbers[0]) * unit)
        return (val, val)

    sep_pos = sep_match.start()
    left_part = s[:sep_pos]
    right_part = s[sep_pos + 1:]

    left_nums = re.findall(r"\d+(?:\.\d+)?", left_part)
    right_nums = re.findall(r"\d+(?:\.\d+)?", right_part)

    min_val = int(float(left_nums[0]) * unit) if left_nums else 0
    max_val = int(float(right_nums[0]) * unit) if right_nums else None

    return (min_val, max_val)
