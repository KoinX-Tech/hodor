#!/bin/sh
set -eu

add_safe_dir() {
  dir="${1}"
  if [ -n "${dir}" ] && [ -d "${dir}" ]; then
    # Prevent Git "dubious ownership" errors for bind-mounted workspaces.
    git config --global --add safe.directory "${dir}" >/dev/null 2>&1 || true
  fi
}

add_safe_dir "${GITHUB_WORKSPACE:-}"
add_safe_dir "${HODOR_WORKSPACE:-}"
add_safe_dir "/workspace"

exec bun run /app/dist/cli.js "$@"

