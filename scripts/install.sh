#!/usr/bin/env bash
# InspireSkill installer — no local clone, no symlinks.
#
# Reads: none (self-contained tarball + uv/pipx download)
# Writes:
#   - ~/.local/bin/inspire       (uv tool / pipx shim; installer-managed)
#   - ~/.{claude,codex,gemini}/skills/inspire/{SKILL.md, references/, ...}
#   - ~/Library/LaunchAgents/sh.inspire-skill.update-check.plist  (macOS only)
#   - ~/.inspire/update-status.json  (via post-install `inspire update --check`)
#
# Usage (typical, no clone required):
#   curl -fsSL https://raw.githubusercontent.com/realZillionX/InspireSkill/main/scripts/install.sh | bash
#   curl -fsSL .../install.sh | bash -s -- --harness claude,codex
#   curl -fsSL .../install.sh | bash -s -- --no-schedule
#
# Flags:
#   --harness claude[,codex,gemini]   explicit harness list (default: auto-detect)
#   --no-cli                          skip installing the Python package (skill-only)
#   --no-schedule                     skip the macOS launchd update-check agent
#   --ref <git-ref>                   pin install/refresh to a branch/tag/SHA (default: main)
#
set -euo pipefail

REPO_SLUG="realZillionX/InspireSkill"
PACKAGE="inspire-skill"
DEFAULT_REF="main"
LAUNCH_LABEL="sh.inspire-skill.update-check"

HARNESSES=""
INSTALL_CLI=1
INSTALL_SCHEDULE=1
REF="$DEFAULT_REF"

color()  { local c="$1"; shift; printf '\033[%sm%s\033[0m' "$c" "$*"; }
bold()   { color "1"  "$@"; }
dim()    { color "2"  "$@"; }
red()    { color "31" "$@"; }
green()  { color "32" "$@"; }
yellow() { color "33" "$@"; }
blue()   { color "34" "$@"; }
log()    { printf '%s %s\n' "$(blue '›')" "$*"; }
ok()     { printf '%s %s\n' "$(green '✓')" "$*"; }
warn()   { printf '%s %s\n' "$(yellow '!')" "$*"; }
die()    { printf '%s %s\n' "$(red '✗')" "$*" >&2; exit 1; }

usage() { sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 0; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --harness)       HARNESSES="$2";       shift 2 ;;
    --harness=*)     HARNESSES="${1#*=}";  shift ;;
    --no-cli)        INSTALL_CLI=0;        shift ;;
    --no-schedule)   INSTALL_SCHEDULE=0;   shift ;;
    --ref)           REF="$2";             shift 2 ;;
    --ref=*)         REF="${1#*=}";        shift ;;
    -h|--help)       usage ;;
    *)               die "unknown argument: $1" ;;
  esac
done

# ---- harness detection -----------------------------------------------------
detect_harnesses() {
  local found=()
  [[ -d "$HOME/.claude"                                      ]] && found+=("claude")
  [[ -d "$HOME/.codex"                                       ]] && found+=("codex")
  [[ -d "$HOME/.gemini"                                      ]] && found+=("gemini")
  [[ -d "$HOME/.openclaw"                                    ]] && found+=("openclaw")
  [[ -d "${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"     ]] && found+=("opencode")
  (IFS=,; echo "${found[*]:-}")
}

if [[ -z "$HARNESSES" ]]; then
  HARNESSES="$(detect_harnesses)"
  [[ -n "$HARNESSES" ]] \
    || die "no agent harness detected (checked \$HOME/.claude, .codex, .gemini, .openclaw, and \$OPENCODE_CONFIG_DIR or \$HOME/.config/opencode). Pass --harness explicitly."
  log "auto-detected harnesses: $(bold "$HARNESSES")"
fi

IFS=',' read -r -a HARNESS_LIST <<<"$HARNESSES"
for h in "${HARNESS_LIST[@]}"; do
  case "$h" in
    claude|codex|gemini|openclaw|opencode) ;;
    *) die "unknown harness: $h (pick from claude,codex,gemini,openclaw,opencode)" ;;
  esac
done

# ---- prerequisites ---------------------------------------------------------
need() { command -v "$1" >/dev/null 2>&1 || die "need '$1' on PATH."; }
need curl
need tar
need mktemp

# ---- install CLI via uv tool / pipx ----------------------------------------
# Default: install from PyPI (fast, cacheable, works behind Tsinghua / Aliyun
# mirrors that a lot of users here rely on). If the caller passed --ref to
# pin to a branch / tag / SHA, fall back to the git spec — that path exists
# for bisecting or trying un-released changes.
if [[ "$REF" == "$DEFAULT_REF" ]]; then
  SPEC="$PACKAGE"
  SPEC_LABEL="$(bold "$PACKAGE") (PyPI)"
else
  SPEC="git+https://github.com/${REPO_SLUG}.git@${REF}#subdirectory=cli"
  SPEC_LABEL="$(dim "$SPEC")"
fi

if (( INSTALL_CLI )); then
  if command -v uv >/dev/null 2>&1; then
    INSTALLER="uv"
    log "installing $SPEC_LABEL via $(bold 'uv tool')"
    uv tool install --force "$SPEC" || die "uv tool install failed — check the spec '$SPEC' and try again."
    # If a previous run installed the same package via pipx, leaving it around
    # would create two `inspire` shims competing for ~/.local/bin/inspire.
    if command -v pipx >/dev/null 2>&1 && pipx list --short 2>/dev/null | grep -q "^${PACKAGE} "; then
      log "removing earlier pipx install of $(bold "$PACKAGE") (uv tool now owns it)"
      pipx uninstall "$PACKAGE" >/dev/null 2>&1 || true
    fi
  elif command -v pipx >/dev/null 2>&1; then
    INSTALLER="pipx"
    log "installing $SPEC_LABEL via $(bold pipx)"
    pipx install --force "$SPEC" || die "pipx install failed — check the spec '$SPEC' and try again."
  else
    die "need uv or pipx. Install uv:  curl -LsSf https://astral.sh/uv/install.sh | sh"
  fi

  # Clean up stale shims from earlier installer paths.
  [[ -L "$HOME/.local/bin/inspire-update" ]] && rm -f "$HOME/.local/bin/inspire-update" \
    && ok "removed legacy shim $(dim "$HOME/.local/bin/inspire-update")"

  # Make sure ~/.local/bin is on PATH so the user can run `inspire` immediately
  # in the *next* shell. Both uv and pipx put binaries there but neither edits
  # the user's shell rc by default, so a fresh-machine install would leave the
  # user staring at "inspire: command not found".
  if ! command -v inspire >/dev/null 2>&1; then
    case "$INSTALLER" in
      uv)
        if uv tool update-shell >/dev/null 2>&1; then
          ok "added ~/.local/bin to your shell rc via $(bold 'uv tool update-shell')"
        else
          warn "couldn't run $(bold 'uv tool update-shell'); add ~/.local/bin to PATH manually."
        fi
        ;;
      pipx)
        if pipx ensurepath --force >/dev/null 2>&1; then
          ok "added ~/.local/bin to your shell rc via $(bold 'pipx ensurepath')"
        else
          warn "couldn't run $(bold 'pipx ensurepath'); add ~/.local/bin to PATH manually."
        fi
        ;;
    esac
    warn "open a new terminal or run $(bold 'exec \$SHELL') for $(bold inspire) to be on PATH."
  fi

  # Print the version we just landed on, regardless of PATH state. We invoke
  # the binary directly via INSTALLER's known location so the message is
  # accurate even if the user hasn't reloaded their shell yet.
  INSPIRE_BIN=""
  if command -v inspire >/dev/null 2>&1; then
    INSPIRE_BIN="$(command -v inspire)"
  elif [[ -x "$HOME/.local/bin/inspire" ]]; then
    INSPIRE_BIN="$HOME/.local/bin/inspire"
  fi
  if [[ -n "$INSPIRE_BIN" ]]; then
    ok "$(INSPIRE_SKIP_UPDATE_CHECK=1 "$INSPIRE_BIN" --version 2>/dev/null || echo "$PACKAGE installed")"
  fi
fi

# ---- fetch SKILL.md + references/ ------------------------------------------
TMP="$(mktemp -d -t inspire-skill.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

# codeload accepts the short form `tar.gz/<ref>` for branches, tags AND
# commit SHAs. The previous form `tar.gz/refs/heads/<ref>` 404'd for tags
# (e.g. `--ref v3.0.0`) and SHAs — see release notes for v3.0.3.
TAR_URL="https://codeload.github.com/${REPO_SLUG}/tar.gz/${REF}"
log "fetching skill bundle $(dim "$TAR_URL")"
if ! curl -fsSL "$TAR_URL" | tar -xzf - -C "$TMP"; then
  die "tarball fetch failed — check network / proxy, and that ref '$REF' exists in the repo (try $(bold 'git ls-remote https://github.com/'"$REPO_SLUG"'.git') to confirm)."
fi

TOP="$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -n1)"
[[ -n "$TOP" && -f "$TOP/SKILL.md" ]] \
  || die "tarball layout unexpected (no SKILL.md under $TOP)."

install_skill() {
  local harness="$1"
  local target
  case "$harness" in
    claude)   target="$HOME/.claude/skills/inspire"                                    ;;
    codex)    target="$HOME/.codex/skills/inspire"                                     ;;
    gemini)   target="$HOME/.gemini/skills/inspire"                                    ;;
    openclaw) target="$HOME/.openclaw/skills/inspire"                                  ;;
    opencode) target="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}/skills/inspire"   ;;
  esac

  # Wipe prior install (handles real dirs and stale symlink layouts).
  if [[ -L "$target" || -e "$target" ]]; then
    rm -rf "$target"
  fi
  mkdir -p "$target"

  cp "$TOP/SKILL.md" "$target/SKILL.md"
  if [[ -d "$TOP/references" ]]; then
    cp -R "$TOP/references" "$target/references"
  fi

  if [[ "$harness" == "codex" ]]; then
    mkdir -p "$target/agents"
    cat >"$target/agents/openai.yaml" <<'YAML'
interface:
  display_name: "Inspire"
  short_description: "Execution-first Inspire operations via the inspire CLI, including auth, proxy routing, notebook/image workflows, and job/HPC execution."
YAML
  fi

  ok "skill → $(dim "$target")"
}

for h in "${HARNESS_LIST[@]}"; do
  install_skill "$h"
done

# ---- schedule background update check (macOS launchd) ----------------------
install_launch_agent() {
  local inspire_path
  inspire_path="$(command -v inspire || true)"
  if [[ -z "$inspire_path" ]]; then
    warn "skipping launchd agent: $(bold inspire) not on PATH."
    return 0
  fi

  local plist="$HOME/Library/LaunchAgents/${LAUNCH_LABEL}.plist"
  local log_file="$HOME/Library/Logs/inspire-skill-update-check.log"
  mkdir -p "$(dirname "$plist")" "$(dirname "$log_file")"

  # launchd doesn't inherit the user's shell env on macOS, so the daily
  # version check needs proxy vars baked in IF the user has them set right
  # now. Read what's in the current env (which `curl | bash` inherits from
  # the user's shell). If nothing's set, we leave the EnvironmentVariables
  # block minimal — the previous version of this script hardcoded
  # 127.0.0.1:7897 (Clash Verge default) which silently broke for everyone
  # who didn't run that exact proxy.
  local user_http="${http_proxy:-${HTTP_PROXY:-}}"
  local user_https="${https_proxy:-${HTTPS_PROXY:-${user_http:-}}}"
  local proxy_block=""
  if [[ -n "$user_http" || -n "$user_https" ]]; then
    proxy_block=$(printf '    <key>http_proxy</key>                <string>%s</string>\n    <key>https_proxy</key>               <string>%s</string>\n    <key>HTTP_PROXY</key>                <string>%s</string>\n    <key>HTTPS_PROXY</key>               <string>%s</string>\n' \
      "$user_http" "$user_https" "$user_http" "$user_https")
  fi

  cat >"$plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>                 <string>${LAUNCH_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${inspire_path}</string>
    <string>update</string>
    <string>--check</string>
    <string>--silent</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>INSPIRE_SKIP_UPDATE_CHECK</key> <string>1</string>
${proxy_block}  </dict>
  <key>StartInterval</key>         <integer>86400</integer>
  <key>RunAtLoad</key>             <true/>
  <key>StandardOutPath</key>       <string>${log_file}</string>
  <key>StandardErrorPath</key>     <string>${log_file}</string>
</dict>
</plist>
PLIST

  launchctl unload "$plist" >/dev/null 2>&1 || true
  if launchctl load "$plist" 2>/dev/null; then
    ok "update-check agent loaded $(dim "$plist")"
  else
    warn "couldn't load launchd agent (plist written at $plist — run \`launchctl load\` manually)."
  fi
}

if (( INSTALL_SCHEDULE )); then
  case "$(uname -s)" in
    Darwin) install_launch_agent ;;
    *)      warn "automatic update-check scheduling only implemented on macOS; CLI still spawns an opportunistic background check on each use." ;;
  esac
fi

# ---- seed cache so the first invocation prints accurate status -------------
if command -v inspire >/dev/null 2>&1; then
  log "priming update-status cache"
  INSPIRE_SKIP_UPDATE_CHECK=1 inspire update --check --silent || true
fi

echo
bold "InspireSkill installed."
cat <<EOF
  1) Configure accounts & proxy:
        inspire init
  2) Verify auth and resource visibility:
        inspire config show --compact
        inspire resources list --all --include-cpu
  3) Check / apply upgrades anytime:
        inspire update --check     # report only
        inspire update             # CLI + SKILL in one shot
EOF
