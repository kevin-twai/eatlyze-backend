# tests/test_food_features.py
import pytest
from app.ml.food_features import extract_features


def test_exact_alias_mapping():
    # "Grilled Chicken" 屬於 chicken breast 的 alias
    res = extract_features("Grilled Chicken")
    assert res["canonical"] == "chicken breast"
    assert res["confidence"] == 1.0
    assert res["matched_from"] == "alias"


def test_fuzzy_mapping_common_typo():
    # "Brocolli" 在表中屬 alias（常見錯字）；若未列 alias 也會走 fuzzy
    res = extract_features("Brocolli")
    assert res["canonical"] == "broccoli"
    assert 0.6 <= res["confidence"] <= 1.0
    assert res["matched_from"] in ("alias", "fuzzy")


def test_unknown_fallback_returns_normalized_label_with_zero_confidence():
    res = extract_features("Dragon Fruit Jelly")
    # 因為映射表沒有，會 fallback（canonical 會是 normalize 後字串）
    assert isinstance(res["canonical"], str)
    assert res["confidence"] in (0.0, pytest.approx(0.0))
    assert res["matched_from"] == "fuzzy"


def test_blank_label_raises():
    with pytest.raises(ValueError):
        extract_features("   ")
