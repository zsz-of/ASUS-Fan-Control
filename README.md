# ASUS Fan Control

> 在 macOS 上通过 AsusSMC 读写 ASUS 笔记本风扇档位，并在菜单栏常驻显示实时转速。

开发者：zsz　　版本：v1.0.0

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

## 下载安装

目前以源码方式分发，暂未提供预编译安装包；发布页见 [Releases](https://github.com/zsz-of/ASUS-Fan-Control/releases)。

```sh
git clone https://github.com/zsz-of/ASUS-Fan-Control.git
cd ASUS-Fan-Control
./build.sh
```

`build.sh` 会完成四件事：组装 `/Applications/ASUS 风扇控制.app`、安装 `/usr/local/bin/asus-fan`、注册登录项 `~/Library/LaunchAgents/com.zsz.asusfan.plist`、启动菜单栏应用。

卸载：

```sh
launchctl bootout gui/$(id -u)/com.zsz.asusfan
rm -f ~/Library/LaunchAgents/com.zsz.asusfan.plist
rm -rf "/Applications/ASUS 风扇控制.app"
sudo rm -f /usr/local/bin/asus-fan
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
| 三档风扇模式 | 自动（0，默认）、强力 Overboost（1）、静音 Silent（2） | SMC `F0Md` |
| 实时转速 | 每 2 秒刷新一次真实 RPM | SMC `F0Ac` |
| 登录自启 | 窗口内开关，写入/删除 LaunchAgent | launchd |
| 命令行控制 | `asus-fan status`、`sudo asus-fan set <0\|1\|2>` | CLI 二进制 |

## 目录结构

```
ASUS-Fan-Control/                 # GitHub 仓库根
├── README.md
├── LICENSE                       # GPL-3.0 官方全文
├── .gitignore
├── build.sh                      # 组装 .app、安装 CLI、注册登录项
├── src/
│   ├── asusfan_app.py            # 菜单栏应用源码（PyObjC/AppKit）
│   ├── Info.plist                # .app 的 Info.plist
│   └── launcher.sh               # .app 可执行入口
├── bin/
│   └── asus-fan                  # 风扇读写 CLI（Mach-O x86_64）
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

首次运行：`./build.sh` 完成后菜单栏即出现风扇图标；点击图标在「自动 / 强力 / 静音」间切换。

## 配置位置

| 内容 | 路径 |
|---|---|
| 应用本体 | `/Applications/ASUS 风扇控制.app` |
| CLI | `/usr/local/bin/asus-fan` |
| 登录自启 | `~/Library/LaunchAgents/com.zsz.asusfan.plist` |

程序不写任何额外配置文件；风扇档位不持久化，重启后回到 EC 默认策略。

## 实测数据

| 场景 | 转速 |
|---|---|
| 空闲（默认档） | ~831–848 RPM |
| 12 线程满载 · 静音 | ~900–903 RPM |
| 12 线程满载 · 强力 | 峰值 1021–1049 RPM |
| 12 线程满载 · 默认 | ~830 RPM |

结论：风扇由 EC 按温度闭环控制，档位只改变曲线偏移，短时负载差距较小，持续负载才会明显拉开。

## 开源引用

| 项目 | 用途 | 仓库 |
|---|---|---|
| AsusSMC | 把 ASUS EC 风扇寄存器映射为 SMC 键 | https://github.com/hieplpvip/AsusSMC |
| VirtualSMC | 提供 SMC 模拟环境 | https://github.com/acidanthera/VirtualSMC |
| PyObjC | Python 调用 AppKit | https://github.com/ronaldoussoren/pyobjc |
