from src.utils import _parse_rate_yen


def test_single_man_yen():
    assert _parse_rate_yen("60万円/月") == (600000, 600000)


def test_range_man_yen():
    assert _parse_rate_yen("60〜70万円") == (600000, 700000)


def test_single_yen_with_comma():
    assert _parse_rate_yen("650,000円") == (650000, 650000)


def test_range_yen_with_comma():
    assert _parse_rate_yen("650,000〜700,000円") == (650000, 700000)


def test_upper_only():
    assert _parse_rate_yen("〜60万円") == (0, 600000)


def test_lower_only():
    assert _parse_rate_yen("60万〜") == (600000, None)


def test_empty_string():
    assert _parse_rate_yen("") == (None, None)


def test_none_input():
    assert _parse_rate_yen(None) == (None, None)


def test_unparseable():
    assert _parse_rate_yen("応相談") == (None, None)


def test_sen_unit():
    assert _parse_rate_yen("800千円") == (800000, 800000)
