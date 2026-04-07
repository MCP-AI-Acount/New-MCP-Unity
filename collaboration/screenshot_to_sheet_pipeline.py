"""
스크린샷 OCR → 템플릿 매핑 → Google Sheets 한 행 추가
"""

import argparse
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from common.google_sheets_client import append_row
from common.ocr_image import ocr_image_path
from common.template_fill import fill_row_from_template


def load_template(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve_path(p: str) -> str:
    if os.path.isabs(p):
        return p
    return os.path.join(_ROOT, p)


def run_pipeline(
    image_path: str,
    template_path: str,
    spreadsheet_id: str,
    dry_run: bool = False,
) -> dict:
    image_path = resolve_path(image_path)
    template_path = resolve_path(template_path)
    template = load_template(template_path)
    ocr_text = ocr_image_path(image_path)
    row = fill_row_from_template(ocr_text, template)
    append_range = template.get("append_range", "시트1!A:Z")
    out = {
        "ocr_preview": ocr_text[:4000],
        "row": row,
        "append_range": append_range,
    }
    if dry_run:
        out["dry_run"] = True
        return out
    result = append_row(spreadsheet_id, append_range, row)
    out["sheets_response"] = result
    return out


def main():
    parser = argparse.ArgumentParser(
        description="스크린샷 OCR 후 템플릿에 맞춰 Google 시트에 행 추가"
    )
    parser.add_argument("--image", required=True, help="이미지 파일 경로")
    parser.add_argument("--template", required=True, help="JSON 템플릿 경로")
    parser.add_argument(
        "--spreadsheet-id",
        default=os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID", ""),
        help="스프레드시트 ID (또는 환경변수 GOOGLE_SHEETS_SPREADSHEET_ID)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Sheets 업로드 없이 OCR·파싱 결과만 출력",
    )
    args = parser.parse_args()
    if not args.dry_run and not args.spreadsheet_id:
        parser.error("--spreadsheet-id 또는 GOOGLE_SHEETS_SPREADSHEET_ID 가 필요합니다 (--dry-run 제외)")

    result = run_pipeline(
        args.image,
        args.template,
        args.spreadsheet_id,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
