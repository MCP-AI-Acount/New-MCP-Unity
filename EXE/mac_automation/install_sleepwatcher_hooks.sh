#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/Users/Windows/Documents/MCP_ Sort/NewMCP}"

cat > "$HOME/.sleep" <<SCRIPT
#!/usr/bin/env bash
/bin/bash "$REPO_DIR/EXE/mac_automation/auto_commit_on_idle.sh"
SCRIPT

cat > "$HOME/.wakeup" <<SCRIPT
#!/usr/bin/env bash
/bin/bash "$REPO_DIR/EXE/mac_automation/git_pull_on_wake.sh"
SCRIPT

chmod +x "$HOME/.sleep" "$HOME/.wakeup"

if command -v brew >/dev/null 2>&1; then
  brew list sleepwatcher >/dev/null 2>&1 || brew install sleepwatcher
  brew services restart sleepwatcher
fi
