#!/bin/bash
set -e

FUBON_WHL="$HOME/Downloads/fubon_neo-2.2.8-cp37-abi3-macosx_11_0_arm64.whl"

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

if [ -f "$FUBON_WHL" ]; then
    pip install "$FUBON_WHL"
else
    echo "找不到 fubon_neo .whl：$FUBON_WHL"
    echo "請手動執行：pip install /path/to/fubon_neo.whl"
    exit 1
fi

echo "完成。執行 'source .venv/bin/activate && python app.py' 啟動"
