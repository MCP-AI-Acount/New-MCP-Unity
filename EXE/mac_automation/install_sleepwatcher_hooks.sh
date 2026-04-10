#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

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
