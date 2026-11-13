# ASUS Fan Control

> 在 macOS 上通过 AsusSMC 读写 ASUS 笔记本风扇档位，并在菜单栏常驻显示实时转速。

开发者：zsz　　版本：v1.2.0

## 许可证

本程序基于 **GNU General Public License v3.0 (GPLv3)** 开源协议发布。

Copyright (C) 2026 zsz

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

本程序分发时附带希望其有用的保证，但不提供任何担保；甚至不提供适销性或特定用途适用性的默示担保。详见 [LICENSE](LICENSE)。

---

## 系统要求

| 项 | 要求 |
|---|---|
| 操作系统 | macOS 11.0 及以上（实测 macOS 15.8） |
| 硬件 | ASUS 笔记本（实测机：i5-13500H + Iris Xe），x86_64 |
| 黑苹果组件 | OpenCore + `AsusSMC` 1.4.2、`VirtualSMC`、`SMCProcessor`、`SMCSuperIO` |
| 运行时 | python.org Python 3.13（`/usr/local/bin/python3.13`）+ `pyobjc-framework-Cocoa` |
| 权限 | `sudo -n /usr/local/bin/asus-fan` 免密（`sudoers.d` 中配置 NOPASSWD） |

> 系统自带 `/usr/bin/python3`（Tk 8.5）在 macOS 15 上无法创建窗口，本项目改用 PyObjC/AppKit，不依赖 Tk。

## 适用条件

| 项 | 条件 |
|---|---|
| 机型 | ASUS 笔记本，且其 EC 风扇模式能被 `AsusSMC` 映射为 `F0Md`（实测：i5-13500H + Iris Xe 的 ROG / TUF 类机型） |
| 系统 | macOS 11.0 及以上，x86_64（实测 macOS 15.8 Sequoia） |
| 引导 | OpenCore + `VirtualSMC`、`SMCProcessor`、`SMCSuperIO` |
| 驱动 | `AsusSMC` 1.4.2 **并已打亮度派发补丁**（见下节），否则可能触发 Caps Lock 降亮度 |
| 权限 | 需 root 写 `F0Md`；安装包会写入 `sudoers.d` 免密规则 |

不满足上述硬件条件的机器只能显示菜单栏界面，读取不到转速与档位。非 ASUS 笔记本、Apple Silicon、以及 EC 未暴露风扇模式的 ASUS 机型不在支持范围。

## 驱动补丁（必须）

`AsusSMC` 的 `handleMessage()` 会把 ATK 通知码与 `0xF0` 相与，结果等于 `0x20` 就派发「亮度减」、等于 `0x10` 就派发「亮度加」。部分 ASUS 机型在切换大写锁定时发出 `0x2C`，因此每次按 Caps Lock 都会降一档亮度。

本仓库不附带修改后的二进制（`AsusSMC` 为 GPL-3.0，分发衍生物需同时提供源码），只提供单字节补丁脚本 [tools/patch_asussmc.py](tools/patch_asussmc.py)，请对自己下载的 `AsusSMC.kext` 1.4.2 执行：

```sh
python3 tools/patch_asussmc.py /path/to/AsusSMC.kext -o /tmp/AsusSMC-patched.kext
```

脚本会把 `andl $-0x10, %eax`（`83 E0 F0`）改为 `andl $0x0, %eax`（`83 E0 00`），使亮度派发分支不再命中；`F0Md` / `F0Ac` 风扇键不受影响。把输出目录替换到 `EFI/OC/Kexts/AsusSMC.kext` 后重启即可。打完补丁后按 Caps Lock 不再改亮度，Fn 亮度键仍由系统原生路径处理。

## 下载安装

从 [Releases](https://github.com/zsz-of/ASUS-Fan-Control/releases) 下载 `ASUS-Fan-Control-1.2.0.dmg` 或 `ASUS-Fan-Control-1.2.0.pkg`。

推荐用 PKG 安装，它会一次装好应用、`asus-fan` 命令行与 `sudoers` 免密规则：

```sh
sudo installer -pkg ASUS-Fan-Control-1.2.0.pkg -target /
```

DMG 内含同一份 PKG 与应用本体；也可只把 `ASUS 风扇控制.app` 拖进「应用程序」，但需自行安装 CLI 与配置免密规则。应用未做开发者签名，首次打开若被拦截，请在访达中右键 →「打开」。安装后启动一次，菜单栏出现风扇图标，勾选窗口内「登录时自动启动」即可常驻。

从源码安装：

```sh
git clone https://github.com/zsz-of/ASUS-Fan-Control.git
cd ASUS-Fan-Control
./build.sh
```

`build.sh` 会完成四件事：组装 `/Applications/ASUS 风扇控制.app`、安装 `/usr/local/bin/asus-fan`、注册登录项 `~/Library/LaunchAgents/com.zsz.asusfan.plist`、启动菜单栏应用。`./package.sh` 则把 PKG 与 DMG 输出到仓库外的 `dist/`。

卸载：

```sh
launchctl bootout gui/$(id -u)/com.zsz.asusfan
rm -f ~/Library/LaunchAgents/com.zsz.asusfan.plist
rm -rf "/Applications/ASUS 风扇控制.app"
sudo rm -f /usr/local/bin/asus-fan /etc/sudoers.d/asusfan
```

## 项目简介

数据通路：`AsusSMC.kext` 把 EC 风扇寄存器映射为 SMC 键 `F0Md`（模式）与 `F0Ac`（转速）。`bin/asus-fan` 是读写这两个键的命令行工具，菜单栏应用只做图形外壳，通过 `subprocess` 调用该 CLI，不直接访问 IOKit/SMC。

| 层 | 技术 |
|---|---|
| CLI | `bin/asus-fan`（Mach-O x86_64 预编译） |
| GUI | Python 3.13 + PyObjC/AppKit，`LSUIElement=true`，无 Dock 图标 |
| 自启 | LaunchAgent `com.zsz.asusfan`，`open -a` 拉起 .app |
| 构建 | `build.sh`（sh + sudo） |

> 注意：`bin/asus-fan` 为随仓库分发的二进制文件，其源码不在本仓库中，也不建议反编译或替换。

## 功能特性

| 功能 | 说明 | 依赖 |
|---|---|---|
| 菜单栏常驻 | SF Symbol `fanblades` 图标，左键显示/隐藏窗口，右键弹快捷菜单 | AppKit |
| 四档风扇模式 | 自动（0，默认）、强力 Overboost（1）、静音 Silent（2）、智能（3，按负载与热压力自动切换） | SMC `F0Md` |
| 智能调速 | 每 15 秒采样 1 分钟平均负载与 `machdep.xcpm.cpu_thermal_level`，连续两次判定一致才换档 | sysctl / launchd |
| 实时转速 | 每 2 秒刷新一次真实 RPM | SMC `F0Ac` |
| 登录自启 | 窗口内开关，写入/删除 LaunchAgent | launchd |
| 命令行控制 | `asus-fan status`、`sudo asus-fan set <0\|1\|2>` | CLI 二进制 |

## 目录结构

```
ASUS-Fan-Control/                 # GitHub 仓库根
├── README.md
├── CHANGELOG.md
├── LICENSE                       # GPL-3.0 官方全文
├── .gitignore
├── build.sh                      # 组装 .app、安装 CLI、注册登录项
├── package.sh                    # 生成 dist/ 下的 PKG 与 DMG
├── src/
│   ├── asusfan_app.py            # 菜单栏应用源码（PyObjC/AppKit）
│   ├── Info.plist                # .app 的 Info.plist
│   ├── AppIcon.icns              # 应用图标（SF Symbol fanblades + 圆角渐变底）
│   └── launcher.sh               # .app 可执行入口
├── bin/
│   └── asus-fan                  # 风扇读写 CLI（Mach-O x86_64）
├── tools/
│   └── patch_asussmc.py          # 给 AsusSMC 1.4.2 打亮度派发补丁
└── launchd/
    └── com.zsz.asusfan.plist     # 登录自启定义
```

### 从源码恢复开发环境

1. 安装 python.org Python 3.13，确认 `/usr/local/bin/python3.13` 存在。
2. 安装 PyObjC：`sudo /usr/local/bin/python3.13 -m pip install pyobjc-framework-Cocoa`（国内可加 `-i https://pypi.tuna.tsinghua.edu.cn/simple`）。
3. 确认 AsusSMC 已加载且 `asus-fan status` 能读到转速。
4. 在 `sudoers.d` 中为 `asus-fan` 配置 NOPASSWD，保证 App 免密切档。
5. 运行 `./build.sh`；改动 `src/asusfan_app.py` 后重新执行即可热替换并重启。

## 运行方式

```sh
# 菜单栏应用（无需常驻前台，安装后自动运行）
open -a "/Applications/ASUS 风扇控制.app"

# 命令行
asus-fan status
sudo asus-fan set 1
```

首次运行：`./build.sh` 完成后菜单栏即出现风扇图标；点击图标在「自动 / 强力 / 静音 / 智能」间切换。

## 配置位置

| 内容 | 路径 |
|---|---|
| 应用本体 | `/Applications/ASUS 风扇控制.app` |
| CLI | `/usr/local/bin/asus-fan` |
| 登录自启 | `~/Library/LaunchAgents/com.zsz.asusfan.plist` |

程序不写任何额外配置文件；风扇档位不持久化，重启后回到 EC 默认策略。

## 已知限制

- 必须使用打过补丁的 `AsusSMC` 1.4.2，否则 Caps Lock 会触发亮度下降（见「驱动补丁」）。
- 风扇档位不写入磁盘持久化，重启失效属正常。
- 温度/风扇不走标准 SMC 键，`powermetrics --samplers smc` 读到的是无效数据，请以 `asus-fan status` 为准。
- 应用未做代码签名，系统大版本升级后需重新验证 PyObjC 兼容性。
- `bin/asus-fan` 仅含 x86_64 架构，Apple Silicon 原生运行未验证。
- 本机的 SMC 未暴露任何 `TC*` 温度键，智能档只能依据负载与 XCPM 热压力判断。

## 实测数据

| 场景 | 转速 |
|---|---|
| 空闲（默认档） | ~831–903 RPM |
| 12 线程满载 · 静音 | ~900–903 RPM |
| 12 线程满载 · 强力 | 峰值 1021–1049 RPM |
| 12 线程满载 · 默认 | ~830 RPM |

转速来自 EC 实时回读，随负载与档位连续变化（同一档位下也会有小幅波动），不是固定占位值。结论：风扇由 EC 按温度闭环控制，档位只改变曲线偏移，短时负载差距较小，持续负载才会明显拉开。

## 开源引用

| 项目 | 用途 | 仓库 |
|---|---|---|
| AsusSMC | 把 ASUS EC 风扇寄存器映射为 SMC 键 | https://github.com/hieplpvip/AsusSMC |
| VirtualSMC | 提供 SMC 模拟环境 | https://github.com/acidanthera/VirtualSMC |
| PyObjC | Python 调用 AppKit | https://github.com/ronaldoussoren/pyobjc |
