#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
catan_env="${repo_root}/Catan-AI/.venv-container"
# Keep this separate from a host or older-container virtual environment.
python3 -m venv "${catan_env}"
"${catan_env}/bin/python" -m pip install -r "${repo_root}/Catan-AI/requirements-dev.txt"
printf '\nCatan is ready. Forward port 6080 and open it in your browser.\n'
printf 'Connect with password: vscode\n'
printf 'Launch from the repository root: bash Catan-AI/scripts/play-container.sh --name Michael\n'
