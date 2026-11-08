#!/usr/bin/env bash
set -euo pipefail
catan_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
catan_python="${catan_root}/.venv-container/bin/python"
if [[ ! -x "${catan_python}" ]]; then
    printf 'Container environment missing. Run: bash "%s/../.devcontainer/setup.sh"\n' "${catan_root}" >&2
    exit 1
fi
export DISPLAY="${DISPLAY:-:1}"
export SDL_AUDIODRIVER="${SDL_AUDIODRIVER:-dummy}"
# Tests use dummy video; a game launch must target the real virtual desktop.
export SDL_VIDEODRIVER=x11
if ! command -v xdpyinfo >/dev/null 2>&1 || ! xdpyinfo -display "${DISPLAY}" >/dev/null 2>&1; then
    printf 'No desktop is available on DISPLAY=%s. Rebuild using the repository devcontainer configuration.\n' "${DISPLAY}" >&2
    printf 'If you use a parent workspace container, add the desktop-lite feature there; see Catan-AI/CONTAINER.md.\n' >&2
    exit 1
fi
printf 'Open forwarded port 6080 in your browser and connect (password: vscode).\n'
exec "${catan_python}" "${catan_root}/code/catanGame.py" "$@"
