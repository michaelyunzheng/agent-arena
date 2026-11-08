#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
catan_env="${repo_root}/Catan-AI/.venv-container"
# Prefer the repository image's interpreter, not an activated parent-workspace venv.
catan_python="${CATAN_PYTHON:-}"
if [[ -z "${catan_python}" ]]; then
    for candidate in python3.12 python3.11 python3.10 python3.9 python3; do
        if command -v "${candidate}" >/dev/null 2>&1; then
            catan_python="${candidate}"
            break
        fi
    done
fi
if [[ -z "${catan_python}" ]] || ! "${catan_python}" -c 'import sys; sys.exit(not ((3, 9) <= sys.version_info[:2] <= (3, 12)))'; then
    printf 'Catan setup requires Python 3.9–3.12; Python 3.12 is recommended.\nRebuild the repository container, or set CATAN_PYTHON to a compatible interpreter.\n' >&2
    exit 1
fi
catan_version="$("${catan_python}" -c 'import sys; print(sys.version_info[:2])')"
if [[ -e "${catan_env}" ]]; then
    existing_version="$("${catan_env}/bin/python" -c 'import sys; print(sys.version_info[:2])' 2>/dev/null || true)"
    if [[ "${existing_version}" != "${catan_version}" ]]; then
        printf 'Existing environment has a different or broken Python. Move %s aside and rerun setup. See Catan-AI/CONTAINER.md.\n' "${catan_env}" >&2
        exit 1
    fi
else
    "${catan_python}" -m venv "${catan_env}"
fi
"${catan_env}/bin/python" -m pip install --only-binary=numpy,pygame -r "${repo_root}/Catan-AI/requirements-dev.txt"
"${catan_env}/bin/python" -c 'import numpy, pygame'
printf '\nCatan dependencies are ready. With desktop-lite running, forward port 6080 and connect with password: vscode\n'
printf 'Launch from the repository root: bash Catan-AI/scripts/play-container.sh --name Michael\n'
