#!/usr/bin/env python3
"""
Google Sheets MCP + 스크린샷 OCR → 템플릿 → 시트 저장 (common 모듈 사용)
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, ListToolsResult, Tool

from common.__google_sheets_client import append_row, get_values
from common.__ocr_image import ocr_image_path
from common.__template_fill import fill_row_from_template

server = Server("google-sheets")


def _resolve_path(p: str) -> str:
    if os.path.isabs(p):
        return p
    return os.path.join(_ROOT, p)


def _load_template(path: str) -> dict:
    path = _resolve_path(path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@server.list_tools()
async def handle_list_tools() -> ListToolsResult:
    return ListToolsResult(
        tools=[
            Tool(
                name="sheets_get_values",
                description="스프레드시트 범위 읽기 (A1)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_id": {
                            "type": "string",
                            "description": "스프레드시트 ID",
                        },
                        "range_a1": {
                            "type": "string",
                            "description": "예: 시트1!A1:Z10",
                        },
                    },
                    "required": ["spreadsheet_id", "range_a1"],
                },
            ),
            Tool(
                name="sheets_append_row",
                description="한 행 추가 (append, USER_ENTERED)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_id": {"type": "string"},
                        "range_a1": {
                            "type": "string",
                            "description": "append 대상 열 범위 예: 시트1!A:Z",
                        },
                        "values": {
                            "type": "array",
                            "description": "셀 값 배열 (한 행)",
                        },
                    },
                    "required": ["spreadsheet_id", "range_a1", "values"],
                },
            ),
            Tool(
                name="ocr_from_image_path",
                description="이미지 파일 경로에서 Tesseract OCR 텍스트 추출",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "image_path": {"type": "string"},
                        "lang": {
                            "type": "string",
                            "description": "기본 kor+eng, 환경변수 OCR_TESSERACT_LANG 로도 설정 가능",
                        },
                    },
                    "required": ["image_path"],
                },
            ),
            Tool(
                name="screenshot_to_sheet",
                description="스크린샷 + JSON 템플릿으로 OCR 후 시트에 한 행 저장",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "image_path": {"type": "string"},
                        "template_path": {"type": "string"},
                        "spreadsheet_id": {
                            "type": "string",
                            "description": "비우면 env GOOGLE_SHEETS_SPREADSHEET_ID",
                        },
                        "dry_run": {
                            "type": "boolean",
                            "description": "True면 Sheets 업로드 없이 OCR·파싱만",
                        },
                    },
                    "required": ["image_path", "template_path"],
                },
            ),
        ]
    )


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    try:
        if name == "sheets_get_values":
            return await _sheets_get_values(arguments)
        if name == "sheets_append_row":
            return await _sheets_append_row(arguments)
        if name == "ocr_from_image_path":
            return await _ocr_from_image_path(arguments)
        if name == "screenshot_to_sheet":
            return await _screenshot_to_sheet(arguments)
        return CallToolResult(
            content=[{"type": "text", "text": f"알 수 없는 도구: {name}"}]
        )
    except Exception as e:
        return CallToolResult(
            content=[{"type": "text", "text": f"오류: {str(e)}"}]
        )


async def _sheets_get_values(args: Dict[str, Any]) -> CallToolResult:
    sid = args["spreadsheet_id"]
    r = args["range_a1"]
    result = get_values(sid, r)
    return CallToolResult(
        content=[
            {
                "type": "text",
                "text": json.dumps(result, ensure_ascii=False, indent=2),
            }
        ]
    )


async def _sheets_append_row(args: Dict[str, Any]) -> CallToolResult:
    sid = args["spreadsheet_id"]
    r = args["range_a1"]
    values = args["values"]
    result = append_row(sid, r, values)
    return CallToolResult(
        content=[
            {
                "type": "text",
                "text": json.dumps(result, ensure_ascii=False, indent=2),
            }
        ]
    )


async def _ocr_from_image_path(args: Dict[str, Any]) -> CallToolResult:
    path = _resolve_path(args["image_path"])
    lang = args.get("lang")
    if lang:
        text = ocr_image_path(path, lang=lang)
    else:
        text = ocr_image_path(path)
    return CallToolResult(content=[{"type": "text", "text": text}])


async def _screenshot_to_sheet(args: Dict[str, Any]) -> CallToolResult:
    from collaboration.__screenshot_to_sheet_pipeline import run_pipeline

    image_path = args["image_path"]
    template_path = args["template_path"]
    sid = args.get("spreadsheet_id") or os.environ.get(
        "GOOGLE_SHEETS_SPREADSHEET_ID", ""
    )
    dry_run = bool(args.get("dry_run", False))
    if not dry_run and not sid:
        return CallToolResult(
            content=[
                {
                    "type": "text",
                    "text": "spreadsheet_id 또는 환경변수 GOOGLE_SHEETS_SPREADSHEET_ID 가 필요합니다.",
                }
            ]
        )
    result = run_pipeline(image_path, template_path, sid, dry_run=dry_run)
    return CallToolResult(
        content=[
            {
                "type": "text",
                "text": json.dumps(result, ensure_ascii=False, indent=2),
            }
        ]
    )


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="google-sheets",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None,
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
