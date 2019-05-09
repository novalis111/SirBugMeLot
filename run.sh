#!/usr/bin/env bash
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
[[ -f "${DIR}/.venv/bin/activate" ]] && source ${DIR}/.venv/bin/activate
nohup python sirbugmelot.py > /dev/null &
deactivate
