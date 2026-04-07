#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/Users/Windows/Documents/MCP_ Sort/NewMCP}"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$LAUNCH_AGENTS_DIR"

IDLE_SCRIPT="$REPO_DIR/EXE/mac_automation/auto_commit_on_idle.sh"
WAKE_SCRIPT="$REPO_DIR/EXE/mac_automation/git_pull_on_wake.sh"

cat > "$LAUNCH_AGENTS_DIR/com.newmcp.autocommit.idle.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.newmcp.autocommit.idle</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$IDLE_SCRIPT</string>
  </array>
  <key>StartInterval</key><integer>60</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>/tmp/newmcp-autocommit.log</string>
  <key>StandardErrorPath</key><string>/tmp/newmcp-autocommit.err</string>
</dict>
</plist>
PLIST

chmod +x "$IDLE_SCRIPT" "$WAKE_SCRIPT"

launchctl unload "$LAUNCH_AGENTS_DIR/com.newmcp.autocommit.idle.plist" >/dev/null 2>&1 || true
launchctl load "$LAUNCH_AGENTS_DIR/com.newmcp.autocommit.idle.plist"
