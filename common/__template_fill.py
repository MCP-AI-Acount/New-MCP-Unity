"""
OCR 텍스트 + JSON 템플릿으로 시트 한 행 값 생성
"""

import re
from typing import Any, Dict, List


def _flags_from_string(s: str) -> int:
    flags = 0
    if not s:
        return flags
    mapping = {
        "IGNORECASE": re.IGNORECASE,
        "MULTILINE": re.MULTILINE,
        "DOTALL": re.DOTALL,
    }
    for part in s.replace("|", " ").split():
        part = part.strip()
        if part in mapping:
            flags |= mapping[part]
    return flags


def fill_row_from_template(ocr_text: str, template: Dict[str, Any]) -> List[Any]:
    columns: List[str] = template["columns"]
    defaults: Dict[str, Any] = template.get("defaults", {})
    extract_rules = template.get("extract", [])
    by_column = {r["column"]: r for r in extract_rules}

    row: List[Any] = []
    for col in columns:
        if col not in by_column:
            row.append(defaults.get(col, ""))
            continue
        rule = by_column[col]
        pattern = rule["pattern"]
        flagstr = rule.get("flags", "")
        fl = _flags_from_string(flagstr)
        m = re.search(pattern, ocr_text, fl)
        if not m:
            row.append(defaults.get(col, ""))
            continue
        group = rule.get("group", 1)
        try:
            val = m.group(group)
        except IndexError:
            val = m.group(0)
        row.append(val.strip() if isinstance(val, str) else val)

    return row
