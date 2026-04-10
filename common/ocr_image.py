"""
스크린샷 이미지에서 OCR 텍스트 추출 (Tesseract)
"""

import os
from typing import Optional

from PIL import Image


def ocr_image_path(image_path: str, lang: Optional[str] = None) -> str:
    import pytesseract

    if not os.path.isfile(image_path):
        raise FileNotFoundError(image_path)

    if lang is None:
        lang = os.environ.get("OCR_TESSERACT_LANG", "kor+eng")

    img = Image.open(image_path)
    try:
        text = pytesseract.image_to_string(img, lang=lang)
    except pytesseract.TesseractNotFoundError as e:
        raise RuntimeError(
            "Tesseract 가 설치되어 있지 않습니다. macOS: brew install tesseract tesseract-lang"
        ) from e
    except Exception as e:
        msg = str(e).lower()
        if "traineddata" in msg or "kor" in msg:
            raise RuntimeError(
                "한글 OCR 언어팩이 없을 수 있습니다. macOS: brew install tesseract-lang "
                "또는 OCR_TESSERACT_LANG=eng 만 사용해 보세요."
            ) from e
        raise
    return text
