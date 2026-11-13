#!/bin/sh
# 重新组装 ASUS 风扇控制.app，安装 CLI 与登录项
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
APP="/Applications/ASUS 风扇控制.app"
PY="/usr/local/bin/python3.13"

[ -x "$PY" ] || { echo "缺少 $PY，请先安装 python.org Python 3.13"; exit 1; }
"$PY" -c "import AppKit" 2>/dev/null || { echo "缺少 pyobjc-framework-Cocoa"; exit 1; }

echo "== 组装 app =="
sudo rm -rf "$APP"
sudo mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
sudo cp "$ROOT/src/Info.plist" "$APP/Contents/Info.plist"
sudo cp "$ROOT/src/asusfan_app.py" "$APP/Contents/Resources/asusfan_app.py"
sudo cp "$ROOT/src/launcher.sh" "$APP/Contents/MacOS/asusfan"
sudo chmod 755 "$APP/Contents/MacOS/asusfan"
sudo chown -R root:wheel "$APP"
"$PY" -m py_compile "$APP/Contents/Resources/asusfan_app.py"

echo "== 安装 CLI =="
sudo install -m 755 "$ROOT/bin/asus-fan" /usr/local/bin/asus-fan

echo "== 注册登录项 =="
mkdir -p ~/Library/LaunchAgents
cp "$ROOT/launchd/com.zsz.asusfan.plist" ~/Library/LaunchAgents/
launchctl bootout gui/$(id -u)/com.zsz.asusfan 2>/dev/null || true
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.zsz.asusfan.plist
sleep 1

echo "== 启动 =="
open -a "$APP"
/usr/local/bin/asus-fan status
echo "完成"
