# app/ml/food_features.py
"""
食物特徵（mock）層：
- 將 Vision/手動輸入的食物名稱，正規化後對應到「標準化食材 canonical name」。
- 目前用 alias 映射 + difflib 模糊比對；後續可替換成真正的 ML/embedding。

公開函式：
- extract_features(label: str) -> dict
  回傳格式：{"canonical": str, "confidence": float, "matched_from": "exact"|"alias"|"fuzzy"}
"""

from __future__ import annotations
import re
from difflib import SequenceMatcher, get_close_matches
from typing import Dict, List, Tuple

_WORD_RE = re.compile(r"[a-z0-9]+")


def _normalize(text: str) -> str:
    return " ".join(_WORD_RE.findall((text or "").lower())).strip()


# 簡易映射表（日後可改從 TFND 或 DB 載入）
# key: canonical；value: aliases（建議保留 canonical 本身於 aliases）
_CANONICAL_MAP: Dict[str, List[str]] = {
    "chicken breast": ["chicken breast", "chicken", "grilled chicken", "roasted chicken"],
    "broccoli": ["broccoli", "brocolli", "steamed broccoli"],  # 含常見錯字
    "white rice": ["white rice", "rice", "steamed rice", "plain rice"],
    "salmon": ["salmon", "grilled salmon", "baked salmon"],
    "egg": ["egg", "boiled egg", "fried egg", "scrambled egg", "eggs"],
    "tofu": ["tofu", "bean curd"],
}

# 建立「alias → canonical」反向索引，以及 canonical 的 normalize 參考
_ALIAS_TO_CANON: Dict[str, str] = {}
_CANON_NORMALS: Dict[str, str] = {}
for canon, aliases in _CANONICAL_MAP.items():
    canon_norm = _normalize(canon)
    _CANON_NORMALS[canon] = canon_norm
    _ALIAS_TO_CANON[canon_norm] = canon
    for a in aliases:
        _ALIAS_TO_CANON[_normalize(a)] = canon


def _fuzzy_best(label_norm: str) -> Tuple[str, float]:
    """
    使用 difflib 對 alias 字典做模糊比對，回傳 (canonical, confidence)
    若找不到合適者，回傳 (label_norm, 0.0) 作為 fallback。
    """
    population = list(_ALIAS_TO_CANON.keys())
    candidates = get_close_matches(label_norm, population, n=3, cutoff=0.6)

    best_score = 0.0
    best_canon = None
    for cand in candidates:
        score = SequenceMatcher(None, label_norm, cand).ratio()
        if score > best_score:
            best_score = score
            best_canon = _ALIAS_TO_CANON[cand]

    if best_canon is None:
        return label_norm, 0.0
    return best_canon, float(best_score)


def extract_features(label: str) -> Dict[str, object]:
    """
    主要入口：將任意食物名稱映射成 canonical。
    規則：
      - 命中 canonical 本字 → matched_from="exact"，confidence=1.0
      - 命中 alias（但非 canonical 本字）→ matched_from="alias"，confidence=1.0
      - 否則模糊比對 → matched_from="fuzzy"，confidence 為相似度（或 0.0）
    """
    if not label or not label.strip():
        raise ValueError("label is empty")

    label_norm = _normalize(label)

    if label_norm in _ALIAS_TO_CANON:
        canonical = _ALIAS_TO_CANON[label_norm]
        # 區分 exact / alias
        if label_norm == _CANON_NORMALS[canonical]:
            matched_from = "exact"
        else:
            matched_from = "alias"
        confidence = 1.0
    else:
        canonical, confidence = _fuzzy_best(label_norm)
        matched_from = "fuzzy"

    return {
        "canonical": canonical,
        "confidence": confidence,
        "matched_from": matched_from,
    }
