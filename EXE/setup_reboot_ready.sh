#!/usr/bin/env bash
set -euo pipefail

# command: 재부팅 이후에도 one-command git flow를 바로 실행 가능하도록 준비
REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SILENT_MODE="${1:-}"
LOCAL_BIN_DIR="${HOME}/.local/bin"
OCG_BIN="${LOCAL_BIN_DIR}/ocg"
ONEPUSH_BIN="${LOCAL_BIN_DIR}/onepush"
CONFIG_DIR="${HOME}/.config/newmcp"
REBOOT_INIT_FILE="${CONFIG_DIR}/reboot_init.sh"
BASHRC_FILE="${HOME}/.bashrc"
BASH_PROFILE_FILE="${HOME}/.bash_profile"
PROFILE_FILE="${HOME}/.profile"
SNIPPET_BEGIN="# >>> new-mcp-ocg >>>"
SNIPPET_END="# <<< new-mcp-ocg <<<"
REBOOT_HOOK_CMD="@reboot /bin/bash ${REPO_ROOT}/EXE/setup_reboot_ready.sh --silent >/tmp/newmcp-reboot-ready.log 2>&1"

mkdir -p "$LOCAL_BIN_DIR"
mkdir -p "$CONFIG_DIR"

cat > "$OCG_BIN" <<EOF
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="${REPO_ROOT}"
exec bash "\$REPO_ROOT/EXE/one_command_git_flow.sh" "\$@"
EOF
chmod +x "$OCG_BIN"
ln -sf "$OCG_BIN" "$ONEPUSH_BIN"

cat > "$REBOOT_INIT_FILE" <<'EOF'
#!/usr/bin/env bash
if [[ -d /workspace ]]; then
  export REPO_ROOT="/workspace"
fi
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
  export PATH="$HOME/.local/bin:$PATH"
fi
EOF
chmod +x "$REBOOT_INIT_FILE"

upsert_shell_snippet() {
  local target_file="$1"
  local temp_file
  touch "$target_file"
  temp_file="$(mktemp)"
  awk -v begin="$SNIPPET_BEGIN" -v end="$SNIPPET_END" '
    $0 == begin { skip=1; next }
    $0 == end { skip=0; next }
    !skip { print }
  ' "$target_file" > "$temp_file"
  cat "$temp_file" > "$target_file"
  rm -f "$temp_file"
  cat >> "$target_file" <<EOF
# >>> new-mcp-ocg >>>
if [[ -f "$REBOOT_INIT_FILE" ]]; then
  source "$REBOOT_INIT_FILE"
fi
# <<< new-mcp-ocg <<<
EOF
}

upsert_shell_snippet "$BASHRC_FILE"
upsert_shell_snippet "$BASH_PROFILE_FILE"
upsert_shell_snippet "$PROFILE_FILE"

git config --global --add safe.directory "$REPO_ROOT" >/dev/null 2>&1 || true

if [[ -z "$(git config --global user.name || true)" ]]; then
  git config --global user.name "newmcp-vm-user"
fi

if [[ -z "$(git config --global user.email || true)" ]]; then
  git config --global user.email "newmcp-vm-user@local"
fi

if command -v crontab >/dev/null 2>&1; then
  current_crontab="$(crontab -l 2>/dev/null || true)"
  if ! printf "%s\n" "$current_crontab" | rg -F "$REBOOT_HOOK_CMD" >/dev/null 2>&1; then
    if [[ -n "$current_crontab" ]]; then
      printf "%s\n%s\n" "$current_crontab" "$REBOOT_HOOK_CMD" | crontab -
    else
      printf "%s\n" "$REBOOT_HOOK_CMD" | crontab -
    fi
  fi
fi

if [[ "$SILENT_MODE" != "--silent" ]]; then
  echo "[setup_reboot_ready] 완료"
  echo "[setup_reboot_ready] 재부팅 후 사용: ocg / onepush / ocg <commit message>"
fi
