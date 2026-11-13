#!/usr/local/bin/python3.13
# ASUS 风扇控制 — 菜单栏常驻程序
# 左键点菜单栏图标：显示/隐藏控制窗口；右键：快捷菜单
# 数据来源：/usr/local/bin/asus-fan（AsusSMC: SMC 键 F0Md / F0Ac）

import os
import re
import subprocess

from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSBackingStoreBuffered,
    NSButton,
    NSButtonTypeRadio,
    NSButtonTypeSwitch,
    NSControlStateValueOff,
    NSControlStateValueOn,
    NSFont,
    NSImage,
    NSMakeRect,
    NSMenu,
    NSMenuItem,
    NSSound,
    NSStatusBar,
    NSTextField,
    NSVariableStatusItemLength,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskTitled,
    NSApp,
    NSEventMaskLeftMouseUp,
    NSEventMaskRightMouseUp,
    NSEventTypeRightMouseUp,
)
from Foundation import NSObject, NSTimer
from objc import python_method

FAN_CLI = "/usr/local/bin/asus-fan"
APP_PATH = "/Applications/ASUS 风扇控制.app"
LABEL = "com.zsz.asusfan"
PLIST_PATH = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % LABEL)

MODES = [(0, "自动 / 默认"), (1, "强力 (Overboost)"), (2, "静音 (Silent)")]
MODE_NAMES = {0: "自动", 1: "强力", 2: "静音"}

PLIST_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/open</string>
        <string>-a</string>
        <string>{app}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>LimitLoadToSessionType</key>
    <string>Aqua</string>
</dict>
</plist>
"""


def read_status():
    try:
        out = subprocess.run(
            [FAN_CLI, "status"], capture_output=True, text=True, timeout=5
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None, None
    rpm = mode = None
    m = re.search(r"fan rpm\s*:\s*(\d+)", out)
    if m:
        rpm = int(m.group(1))
    m = re.search(r"fan mode:\s*(\d+)", out)
    if m:
        mode = int(m.group(1))
    return rpm, mode


def write_mode(mode):
    try:
        p = subprocess.run(
            ["/usr/bin/sudo", "-n", FAN_CLI, "set", str(mode)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return p.returncode == 0, (p.stderr or p.stdout or "").strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)


class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, _note):
        self.mode = None
        self.radios = []
        self.menu_mode_items = {}
        self._build_status_item()
        self._build_window()
        self._build_menu()
        self.refresh_(None)
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            2.0, self, "refresh:", None, True
        )

    # ---------- 菜单栏 ----------
    @python_method
    def _build_status_item(self):
        self.statusItem = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength
        )
        button = self.statusItem.button()
        img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
            "fanblades", "风扇"
        )
        if img is not None:
            img.setTemplate_(True)
            button.setImage_(img)
        else:
            button.setTitle_("风扇")
        button.setToolTip_("ASUS 风扇控制")
        button.setTarget_(self)
        button.setAction_("statusClicked:")
        # 左键 + 右键都交给 action 处理
        button.sendActionOn_(NSEventMaskLeftMouseUp | NSEventMaskRightMouseUp)

    def statusClicked_(self, _sender):
        event = NSApp.currentEvent()
        if event is not None and event.type() == NSEventTypeRightMouseUp:
            NSMenu.popUpContextMenu_withEvent_forView_(
                self.menu, event, self.statusItem.button()
            )
            return
        win = self.window
        if win is not None and win.isVisible():
            win.orderOut_(None)
        else:
            NSApp.activateIgnoringOtherApps_(True)
            win.makeKeyAndOrderFront_(None)

    # ---------- 控制窗口 ----------
    @python_method
    def _label(self, rect, text, size=12, bold=False):
        lbl = NSTextField.alloc().initWithFrame_(rect)
        lbl.setStringValue_(text)
        lbl.setBezeled_(False)
        lbl.setDrawsBackground_(False)
        lbl.setEditable_(False)
        lbl.setSelectable_(False)
        lbl.setFont_(
            NSFont.boldSystemFontOfSize_(size)
            if bold
            else NSFont.systemFontOfSize_(size)
        )
        return lbl

    @python_method
    def _build_window(self):
        style = (
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskMiniaturizable
        )
        win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, 340, 300), style, NSBackingStoreBuffered, False
        )
        win.setTitle_("ASUS 风扇控制")
        win.setReleasedWhenClosed_(False)
        win.center()
        self.window = win
        view = win.contentView()

        view.addSubview_(self._label(NSMakeRect(20, 258, 200, 20), "当前转速", 13, True))
        self.rpmLabel = self._label(NSMakeRect(20, 218, 180, 34), "-- RPM", 26, True)
        view.addSubview_(self.rpmLabel)
        self.stateLabel = self._label(NSMakeRect(20, 196, 300, 18), "正在读取…", 11)
        view.addSubview_(self.stateLabel)

        y = 150
        for value, text in MODES:
            btn = NSButton.alloc().initWithFrame_(NSMakeRect(20, y, 300, 22))
            btn.setButtonType_(NSButtonTypeRadio)
            btn.setTitle_(text)
            btn.setTarget_(self)
            btn.setAction_("radioChanged:")
            btn.setTag_(value)
            btn.setState_(NSControlStateValueOff)
            view.addSubview_(btn)
            self.radios.append((value, btn))
            y -= 28

        self.autoBtn = NSButton.alloc().initWithFrame_(NSMakeRect(20, 40, 300, 22))
        self.autoBtn.setButtonType_(NSButtonTypeSwitch)
        self.autoBtn.setTitle_("登录时自动启动（后台常驻）")
        self.autoBtn.setTarget_(self)
        self.autoBtn.setAction_("toggleAutostart:")
        self.autoBtn.setState_(
            NSControlStateValueOn
            if os.path.exists(PLIST_PATH)
            else NSControlStateValueOff
        )
        view.addSubview_(self.autoBtn)

        view.addSubview_(
            self._label(
                NSMakeRect(20, 14, 300, 16),
                "重启后风扇回到自动模式；这里写入的档位立即生效。",
                10,
            )
        )

    @python_method
    def _build_menu(self):
        menu = NSMenu.alloc().init()
        self.menu_rpm = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "转速 — RPM", None, ""
        )
        self.menu_rpm.setEnabled_(False)
        menu.addItem_(self.menu_rpm)
        menu.addItem_(NSMenuItem.separatorItem())
        for value, text in MODES:
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                text, "menuMode:", ""
            )
            item.setTarget_(self)
            item.setTag_(value)
            menu.addItem_(item)
            self.menu_mode_items[value] = item
        menu.addItem_(NSMenuItem.separatorItem())
        show = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "显示控制窗口", "showWindow:", "o"
        )
        show.setTarget_(self)
        menu.addItem_(show)
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "退出", "quitApp:", "q"
        )
        quit_item.setTarget_(self)
        menu.addItem_(quit_item)
        self.menu = menu

    # ---------- 行为 ----------
    def refresh_(self, _timer):
        rpm, mode = read_status()
        if rpm is None and mode is None:
            self.rpmLabel.setStringValue_("-- RPM")
            self.stateLabel.setStringValue_("无法读取：AsusSMC 未加载或 asus-fan 缺失")
            self.menu_rpm.setTitle_("风扇状态不可读")
            return
        self.rpmLabel.setStringValue_("%s RPM" % (rpm if rpm is not None else "--"))
        self.stateLabel.setStringValue_(
            "当前模式：%s" % MODE_NAMES.get(mode, "未知")
        )
        self.menu_rpm.setTitle_("转速 %s RPM" % (rpm if rpm is not None else "--"))
        if mode != self.mode:
            self.mode = mode
            for value, btn in self.radios:
                btn.setState_(
                    NSControlStateValueOn if value == mode else NSControlStateValueOff
                )
            for value, item in self.menu_mode_items.items():
                item.setState_(
                    NSControlStateValueOn if value == mode else NSControlStateValueOff
                )

    @python_method
    def _apply(self, mode):
        ok, err = write_mode(mode)
        if ok:
            self.mode = None  # 触发下一次刷新同步 UI
            self.refresh_(None)
        else:
            self.stateLabel.setStringValue_("切换失败：%s" % (err or "检查 sudo 免密"))
            NSSound.beep()

    def radioChanged_(self, sender):
        self._apply(sender.tag())

    def menuMode_(self, sender):
        self._apply(sender.tag())

    def showWindow_(self, _sender):
        NSApp.activateIgnoringOtherApps_(True)
        self.window.makeKeyAndOrderFront_(None)

    def quitApp_(self, _sender):
        NSApp.terminate_(None)

    def toggleAutostart_(self, sender):
        if sender.state() == NSControlStateValueOn:
            try:
                os.makedirs(os.path.dirname(PLIST_PATH), exist_ok=True)
                with open(PLIST_PATH, "w") as fh:
                    fh.write(PLIST_XML.format(label=LABEL, app=APP_PATH))
                subprocess.run(
                    [
                        "/bin/launchctl",
                        "bootstrap",
                        "gui/%d" % os.getuid(),
                        PLIST_PATH,
                    ],
                    capture_output=True,
                )
            except OSError:
                sender.setState_(NSControlStateValueOff)
                NSSound.beep()
        else:
            # 只移除登录项，不 bootout：当前进程本身就是该 job，bootout 会把自己杀掉
            try:
                os.remove(PLIST_PATH)
            except OSError:
                pass


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()


if __name__ == "__main__":
    main()
