#!/usr/bin/env bash
set -euo pipefail

# command: 재부팅 이후에도 one-command git flow를 바로 실행 가능하도록 준비
REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
LOCAL_BIN_DIR="${HOME}/.local/bin"
OCG_BIN="${LOCAL_BIN_DIR}/ocg"
BASHRC_FILE="${HOME}/.bashrc"
SNIPPET_BEGIN="# >>> new-mcp-ocg >>>"
SNIPPET_END="# <<< new-mcp-ocg <<<"

mkdir -p "$LOCAL_BIN_DIR"

cat > "$OCG_BIN" <<EOF
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="${REPO_ROOT}"
exec bash "\$REPO_ROOT/EXE/one_command_git_flow.sh" "\$@"
EOF
chmod +x "$OCG_BIN"

touch "$BASHRC_FILE"
if ! rg -F "$SNIPPET_BEGIN" "$BASHRC_FILE" >/dev/null 2>&1; then
  cat >> "$BASHRC_FILE" <<'EOF'
# >>> new-mcp-ocg >>>
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
  export PATH="$HOME/.local/bin:$PATH"
fi
# <<< new-mcp-ocg <<<
EOF
fi

git config --global --add safe.directory "$REPO_ROOT" >/dev/null 2>&1 || true

echo "[setup_reboot_ready] 완료"
echo "[setup_reboot_ready] 재부팅 후 사용: ocg 또는 ocg <commit message>"
