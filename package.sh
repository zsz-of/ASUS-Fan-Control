#!/bin/sh
# 打发行包：dist/ASUS-Fan-Control-<版本>.pkg 与 .dmg
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
PY="/usr/local/bin/python3.13"
APP_NAME="ASUS 风扇控制.app"
VERSION="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$ROOT/src/Info.plist")"
DIST="$ROOT/../dist"
BUILD="$DIST/build"
STAGE="$BUILD/stage"

[ -x "$PY" ] || { echo "缺少 $PY，请先安装 python.org Python 3.13"; exit 1; }
"$PY" -c "import AppKit" 2>/dev/null || { echo "缺少 pyobjc-framework-Cocoa"; exit 1; }

rm -rf "$BUILD"
mkdir -p "$STAGE/Applications/$APP_NAME/Contents/MacOS" \
         "$STAGE/Applications/$APP_NAME/Contents/Resources" \
         "$STAGE/usr/local/bin" "$STAGE/etc/sudoers.d"

echo "== 组装 app =="
cp "$ROOT/src/Info.plist" "$STAGE/Applications/$APP_NAME/Contents/Info.plist"
cp "$ROOT/src/AppIcon.icns" "$STAGE/Applications/$APP_NAME/Contents/Resources/AppIcon.icns"
cp "$ROOT/src/asusfan_app.py" "$STAGE/Applications/$APP_NAME/Contents/Resources/asusfan_app.py"
cp "$ROOT/src/launcher.sh" "$STAGE/Applications/$APP_NAME/Contents/MacOS/asusfan"
chmod 755 "$STAGE/Applications/$APP_NAME/Contents/MacOS/asusfan"
# 目录属 root，编译缓存也必须以 root 身份写入，故先编译再改属主
"$PY" -m py_compile "$STAGE/Applications/$APP_NAME/Contents/Resources/asusfan_app.py"
codesign --force --deep -s - "$STAGE/Applications/$APP_NAME"

echo "== CLI 与免密规则 =="
install -m 755 "$ROOT/bin/asus-fan" "$STAGE/usr/local/bin/asus-fan"
cat > "$STAGE/etc/sudoers.d/asusfan" <<'SUDO'
# ASUS Fan Control：允许免密切换风扇档位（仅限 set 0/1/2）
ALL ALL = (root) NOPASSWD: /usr/local/bin/asus-fan set 0, /usr/local/bin/asus-fan set 1, /usr/local/bin/asus-fan set 2
SUDO
chmod 440 "$STAGE/etc/sudoers.d/asusfan"

echo "== 生成 pkg =="
pkgbuild --root "$STAGE" --identifier com.zsz.asusfan --version "$VERSION" \
         --install-location / --ownership recommended \
         "$DIST/ASUS-Fan-Control-$VERSION.pkg"

echo "== 生成 dmg =="
mkdir -p "$BUILD/dmg"
cp -R "$STAGE/Applications/$APP_NAME" "$BUILD/dmg/"
cp "$DIST/ASUS-Fan-Control-$VERSION.pkg" "$BUILD/dmg/"
mkdir -p "$BUILD/dmg/.background"
ln -s /Applications "$BUILD/dmg/Applications"
cat > "$BUILD/dmg/安装说明.txt" <<'TXT'
ASUS 风扇控制

方式一（推荐）：双击 ASUS-Fan-Control-*.pkg，按提示安装。
  会安装：应用程序、/usr/local/bin/asus-fan、sudoers 免密规则。

方式二：把「ASUS 风扇控制.app」拖到 Applications。
  此方式需自行安装 asus-fan 并配置 sudoers，详见 README。

首次打开若提示"无法验证开发者"，请在访达中右键 → 打开。
安装后在「应用程序」中启动一次，点菜单栏风扇图标即可切换档位。
TXT
hdiutil create -volname "ASUS Fan Control $VERSION" -srcfolder "$BUILD/dmg" \
        -ov -format UDZO "$DIST/ASUS-Fan-Control-$VERSION.dmg" >/dev/null

echo "完成："
ls -lh "$DIST"/ASUS-Fan-Control-$VERSION.pkg "$DIST"/ASUS-Fan-Control-$VERSION.dmg
