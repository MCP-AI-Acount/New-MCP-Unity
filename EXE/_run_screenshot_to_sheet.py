#!/usr/bin/env python3
# 사용자 실행 예시 (주석)
# cd /Users/Windows/Documents/Task/NewMCP && python3 collaboration/screenshot_to_sheet_pipeline.py --image temp/capture.png --template main rules/sheets_ocr_template.example.json --spreadsheet-id <스프레드시트ID>
# 드라이런: --dry-run

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from collaboration.__screenshot_to_sheet_pipeline import main

if __name__ == "__main__":
    main()
