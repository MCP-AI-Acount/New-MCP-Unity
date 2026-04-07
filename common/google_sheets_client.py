"""
Google Sheets API — OAuth2 + token_sheets.json (캘린더용 token.json과 분리)
"""

import os
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MCP_SERVER_DIR = os.path.join(_ROOT, "MCP_Server")
_TOKEN_PATH = os.path.join(_MCP_SERVER_DIR, "token_sheets.json")
_CREDENTIALS_PATH = os.path.join(_MCP_SERVER_DIR, "credentials.json")

_service = None


def _build_credentials() -> Optional[Credentials]:
    creds = None
    if os.path.exists(_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(_TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.isfile(_CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"credentials.json 이 없습니다: {_CREDENTIALS_PATH}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(_CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(_TOKEN_PATH, "w", encoding="utf-8") as token:
            token.write(creds.to_json())
    return creds


def get_sheets_service():
    global _service
    if _service is None:
        creds = _build_credentials()
        _service = build("sheets", "v4", credentials=creds)
    return _service


def reset_sheets_service_cache():
    global _service
    _service = None


def append_row(
    spreadsheet_id: str,
    range_a1: str,
    row_values: List[Any],
) -> Dict[str, Any]:
    service = get_sheets_service()
    body = {"values": [row_values]}
    return (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=range_a1,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body,
        )
        .execute()
    )


def get_values(spreadsheet_id: str, range_a1: str) -> Dict[str, Any]:
    service = get_sheets_service()
    return (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_a1)
        .execute()
    )
