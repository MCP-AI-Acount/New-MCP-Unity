#!/usr/bin/env python3
"""
Google Calendar MCP Server
구글 캘린더 API를 통한 이벤트 조회, 생성, 수정, 삭제 기능 제공
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
)

# Google Calendar API 설정
SCOPES = ['https://www.googleapis.com/auth/calendar']

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_TOKEN_PATH = os.path.join(_SCRIPT_DIR, 'token.json')
_CREDENTIALS_PATH = os.path.join(_SCRIPT_DIR, 'credentials.json')

# 환경변수에서 설정 가져오기
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# MCP 서버 초기화
server = Server("google-calendar")

class GoogleCalendarAPI:
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Google Calendar API 인증"""
        try:
            # API 키를 사용한 간단한 인증 (읽기 전용)
            if self.api_key:
                self.service = build('calendar', 'v3', developerKey=self.api_key)
            else:
                # OAuth2 인증 (전체 권한)
                creds = None
                
                if os.path.exists(_TOKEN_PATH):
                    creds = Credentials.from_authorized_user_file(_TOKEN_PATH, SCOPES)
                
                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                    else:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            _CREDENTIALS_PATH, SCOPES)
                        creds = flow.run_local_server(port=0)
                    
                    with open(_TOKEN_PATH, 'w') as token:
                        token.write(creds.to_json())
                
                self.service = build('calendar', 'v3', credentials=creds)
        except Exception as e:
            print(f"Google Calendar API 인증 실패: {e}")
    
    def get_calendars(self) -> Dict[str, Any]:
        """캘린더 목록 조회"""
        try:
            if not self.service:
                return {"error": "Google Calendar API가 초기화되지 않았습니다."}
            
            calendars = self.service.calendarList().list().execute()
            return calendars
        except Exception as e:
            return {"error": f"캘린더 목록 조회 실패: {str(e)}"}
    
    def get_events(self, calendar_id: str = 'primary', time_min: str = None, time_max: str = None, max_results: int = 10) -> Dict[str, Any]:
        """이벤트 조회"""
        try:
            if not self.service:
                return {"error": "Google Calendar API가 초기화되지 않았습니다."}
            
            if not time_min:
                time_min = datetime.utcnow().isoformat() + 'Z'
            if not time_max:
                time_max = (datetime.utcnow() + timedelta(days=7)).isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result
        except Exception as e:
            return {"error": f"이벤트 조회 실패: {str(e)}"}
    
    def create_event(self, calendar_id: str = 'primary', summary: str = '', start: str = None, end: str = None, description: str = '', location: str = '') -> Dict[str, Any]:
        """이벤트 생성"""
        try:
            if not self.service:
                return {"error": "Google Calendar API가 초기화되지 않았습니다."}
            
            if not start:
                start = datetime.utcnow().isoformat() + 'Z'
            if not end:
                end = (datetime.utcnow() + timedelta(hours=1)).isoformat() + 'Z'
            
            event = {
                'summary': summary,
                'description': description,
                'location': location,
                'start': {
                    'dateTime': start,
                    'timeZone': 'Asia/Seoul',
                },
                'end': {
                    'dateTime': end,
                    'timeZone': 'Asia/Seoul',
                },
            }
            
            event_result = self.service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()
            
            return event_result
        except Exception as e:
            return {"error": f"이벤트 생성 실패: {str(e)}"}
    
    def update_event(self, calendar_id: str = 'primary', event_id: str = '', summary: str = None, start: str = None, end: str = None, description: str = None, location: str = None) -> Dict[str, Any]:
        """이벤트 수정"""
        try:
            if not self.service:
                return {"error": "Google Calendar API가 초기화되지 않았습니다."}
            
            # 기존 이벤트 조회
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            # 업데이트할 필드만 수정
            if summary:
                event['summary'] = summary
            if description:
                event['description'] = description
            if location:
                event['location'] = location
            if start:
                event['start']['dateTime'] = start
            if end:
                event['end']['dateTime'] = end
            
            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            
            return updated_event
        except Exception as e:
            return {"error": f"이벤트 수정 실패: {str(e)}"}
    
    def delete_event(self, calendar_id: str = 'primary', event_id: str = '') -> Dict[str, Any]:
        """이벤트 삭제"""
        try:
            if not self.service:
                return {"error": "Google Calendar API가 초기화되지 않았습니다."}
            
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            return {"success": True, "message": "이벤트가 삭제되었습니다."}
        except Exception as e:
            return {"error": f"이벤트 삭제 실패: {str(e)}"}

# Google Calendar API 클라이언트 초기화
calendar_api = GoogleCalendarAPI(GOOGLE_API_KEY)

@server.list_tools()
async def handle_list_tools() -> ListToolsResult:
    """사용 가능한 도구 목록 반환"""
    return ListToolsResult(
        tools=[
            Tool(
                name="get_calendars",
                description="구글 캘린더 목록 조회",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="get_events",
                description="구글 캘린더에서 이벤트 조회",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {"type": "string", "description": "캘린더 ID (기본값: primary)"},
                        "time_min": {"type": "string", "description": "시작 시간 (ISO 8601)"},
                        "time_max": {"type": "string", "description": "종료 시간 (ISO 8601)"},
                        "max_results": {"type": "integer", "description": "최대 결과 수 (기본값: 10)"}
                    }
                }
            ),
            Tool(
                name="create_event",
                description="구글 캘린더에 새 이벤트 생성",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {"type": "string", "description": "캘린더 ID (기본값: primary)"},
                        "summary": {"type": "string", "description": "이벤트 제목"},
                        "start": {"type": "string", "description": "시작 시간 (ISO 8601)"},
                        "end": {"type": "string", "description": "종료 시간 (ISO 8601)"},
                        "description": {"type": "string", "description": "이벤트 설명"},
                        "location": {"type": "string", "description": "위치"}
                    },
                    "required": ["summary"]
                }
            ),
            Tool(
                name="update_event",
                description="구글 캘린더 이벤트 수정",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {"type": "string", "description": "캘린더 ID (기본값: primary)"},
                        "event_id": {"type": "string", "description": "이벤트 ID"},
                        "summary": {"type": "string", "description": "새로운 제목"},
                        "start": {"type": "string", "description": "새로운 시작 시간"},
                        "end": {"type": "string", "description": "새로운 종료 시간"},
                        "description": {"type": "string", "description": "새로운 설명"},
                        "location": {"type": "string", "description": "새로운 위치"}
                    },
                    "required": ["event_id"]
                }
            ),
            Tool(
                name="delete_event",
                description="구글 캘린더 이벤트 삭제",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {"type": "string", "description": "캘린더 ID (기본값: primary)"},
                        "event_id": {"type": "string", "description": "이벤트 ID"}
                    },
                    "required": ["event_id"]
                }
            )
        ]
    )

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """도구 실행"""
    try:
        if name == "get_calendars":
            return await get_calendars()
        elif name == "get_events":
            return await get_events(arguments)
        elif name == "create_event":
            return await create_event(arguments)
        elif name == "update_event":
            return await update_event(arguments)
        elif name == "delete_event":
            return await delete_event(arguments)
        else:
            return CallToolResult(
                content=[{"type": "text", "text": f"알 수 없는 도구: {name}"}]
            )
    except Exception as e:
        return CallToolResult(
            content=[{"type": "text", "text": f"오류 발생: {str(e)}"}]
        )

async def get_calendars() -> CallToolResult:
    """캘린더 목록 조회"""
    try:
        result = calendar_api.get_calendars()
        return CallToolResult(
            content=[{"type": "text", "text": f"캘린더 목록: {json.dumps(result, indent=2, ensure_ascii=False)}"}]
        )
    except Exception as e:
        return CallToolResult(
            content=[{"type": "text", "text": f"캘린더 목록 조회 실패: {str(e)}"}]
        )

async def get_events(args: Dict[str, Any]) -> CallToolResult:
    """이벤트 조회"""
    calendar_id = args.get("calendar_id", "primary")
    time_min = args.get("time_min", "")
    time_max = args.get("time_max", "")
    max_results = args.get("max_results", 10)
    
    try:
        result = calendar_api.get_events(calendar_id, time_min, time_max, max_results)
        return CallToolResult(
            content=[{"type": "text", "text": f"이벤트 목록: {json.dumps(result, indent=2, ensure_ascii=False)}"}]
        )
    except Exception as e:
        return CallToolResult(
            content=[{"type": "text", "text": f"이벤트 조회 실패: {str(e)}"}]
        )

async def create_event(args: Dict[str, Any]) -> CallToolResult:
    """이벤트 생성"""
    calendar_id = args.get("calendar_id", "primary")
    summary = args.get("summary", "")
    start = args.get("start", "")
    end = args.get("end", "")
    description = args.get("description", "")
    location = args.get("location", "")
    
    try:
        result = calendar_api.create_event(calendar_id, summary, start, end, description, location)
        return CallToolResult(
            content=[{"type": "text", "text": f"이벤트 생성 결과: {json.dumps(result, indent=2, ensure_ascii=False)}"}]
        )
    except Exception as e:
        return CallToolResult(
            content=[{"type": "text", "text": f"이벤트 생성 실패: {str(e)}"}]
        )

async def update_event(args: Dict[str, Any]) -> CallToolResult:
    """이벤트 수정"""
    calendar_id = args.get("calendar_id", "primary")
    event_id = args.get("event_id", "")
    summary = args.get("summary", "")
    start = args.get("start", "")
    end = args.get("end", "")
    description = args.get("description", "")
    location = args.get("location", "")
    
    try:
        result = calendar_api.update_event(calendar_id, event_id, summary, start, end, description, location)
        return CallToolResult(
            content=[{"type": "text", "text": f"이벤트 수정 결과: {json.dumps(result, indent=2, ensure_ascii=False)}"}]
        )
    except Exception as e:
        return CallToolResult(
            content=[{"type": "text", "text": f"이벤트 수정 실패: {str(e)}"}]
        )

async def delete_event(args: Dict[str, Any]) -> CallToolResult:
    """이벤트 삭제"""
    calendar_id = args.get("calendar_id", "primary")
    event_id = args.get("event_id", "")
    
    try:
        result = calendar_api.delete_event(calendar_id, event_id)
        return CallToolResult(
            content=[{"type": "text", "text": f"이벤트 삭제 결과: {json.dumps(result, indent=2, ensure_ascii=False)}"}]
        )
    except Exception as e:
        return CallToolResult(
            content=[{"type": "text", "text": f"이벤트 삭제 실패: {str(e)}"}]
        )

async def main():
    """메인 함수"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="google-calendar",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None,
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
