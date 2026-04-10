#!/usr/bin/env bash
set -euo pipefail

# command: 맥에서 Cloud bridge 에이전트 설치/실행
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$LAUNCH_AGENTS_DIR/com.newmcp.bridge.agent.plist"
LOG_PATH="/tmp/newmcp-bridge-agent.log"
ERR_PATH="/tmp/newmcp-bridge-agent.err"

BRIDGE_BASE_URL="${BRIDGE_BASE_URL:-${BRIDGE_CLOUD_RUN_URL:-${CLOUD_RUN_URL:-${REMOTE_MCP_GATEWAY_URL:-}}}}"
BRIDGE_AUTH_TOKEN="${BRIDGE_AUTH_TOKEN:-${BRIDGE_SHARED_TOKEN:-${REMOTE_API_BEARER_TOKEN:-}}}"
DEVICE_ID="${DEVICE_ID:-${BRIDGE_DEVICE_ID:-$(hostname)}}"
WORKSPACE_DIR="${WORKSPACE_DIR:-$REPO_DIR}"
POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-${BRIDGE_POLL_SECONDS:-5}}"

if [[ -z "$BRIDGE_BASE_URL" || -z "$BRIDGE_AUTH_TOKEN" ]]; then
  echo "BRIDGE_BASE_URL(or CLOUD_RUN_URL), BRIDGE_AUTH_TOKEN(or REMOTE_API_BEARER_TOKEN) 환경변수가 필요합니다." >&2
  exit 1
fi

mkdir -p "$LAUNCH_AGENTS_DIR"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.newmcp.bridge.agent</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/env</string>
    <string>python3</string>
    <string>$REPO_DIR/EXE/mac_automation/bridge_agent.py</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>BRIDGE_BASE_URL</key><string>$BRIDGE_BASE_URL</string>
    <key>BRIDGE_AUTH_TOKEN</key><string>$BRIDGE_AUTH_TOKEN</string>
    <key>DEVICE_ID</key><string>$DEVICE_ID</string>
    <key>WORKSPACE_DIR</key><string>$WORKSPACE_DIR</string>
    <key>POLL_INTERVAL_SECONDS</key><string>$POLL_INTERVAL_SECONDS</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$LOG_PATH</string>
  <key>StandardErrorPath</key><string>$ERR_PATH</string>
</dict>
</plist>
PLIST

launchctl unload "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl load "$PLIST_PATH"

echo "[install_bridge_agent] installed: $PLIST_PATH"
echo "[install_bridge_agent] logs: $LOG_PATH / $ERR_PATH"
