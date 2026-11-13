#!/usr/bin/env python3
"""给 AsusSMC 1.4.2 打补丁：让 ATK 通知不再被当成亮度键。

背景：AsusSMC 的 handleMessage() 在 default 分支里把通知码与 0xF0 相与，
结果等于 0x20 就派发「亮度减」、等于 0x10 就派发「亮度加」。部分 ASUS 机型
（如 i5-13500H 的 ROG / TUF）在切换大写锁定时会发出 0x2C，于是每次按 Caps
Lock 都降一档亮度。本脚本把该处的 `andl $-0x10, %eax`（83 E0 F0）改成
`andl $0x0, %eax`（83 E0 00），使亮度派发分支永不命中；F0Md / F0Ac 风扇键
不受影响。

用法：
    python3 tools/patch_asussmc.py /path/to/AsusSMC.kext
    python3 tools/patch_asussmc.py /path/to/AsusSMC.kext -o /tmp/AsusSMC-patched.kext

注意：修改后的 kext 属 AsusSMC 的衍生物，受 GPL-3.0 约束；分发时须同时
提供相应源码，因此本仓库只提供本脚本，不附带二进制。
"""

import argparse
import plistlib
import shutil
import sys
from pathlib import Path

PATTERN = bytes.fromhex("83e0f083f810")  # andl $-0x10,%eax ; cmpl $0x10,%eax
PATCHED = bytes.fromhex("83e00083f810")  # andl $0x0,%eax  ; cmpl $0x10,%eax
EXPECTED_VERSION = "1.4.2"


def patch_binary(data: bytes) -> tuple[bytes, int]:
    if data.count(PATCHED):
        return data, 0
    hits = []
    start = 0
    while True:
        i = data.find(PATTERN, start)
        if i < 0:
            break
        hits.append(i)
        start = i + 1
    if len(hits) != 1:
        raise SystemExit(
            f"找到 {len(hits)} 处匹配，预期 1 处；版本可能不符，已中止"
        )
    i = hits[0]
    return data[:i] + PATCHED + data[i + len(PATTERN):], i


def main() -> int:
    ap = argparse.ArgumentParser(description="给 AsusSMC 1.4.2 打亮度派发补丁")
    ap.add_argument("kext", type=Path, help="未打补丁的 AsusSMC.kext 路径")
    ap.add_argument("-o", "--output", type=Path, help="输出路径，默认原地修改")
    args = ap.parse_args()

    info_plist = args.kext / "Contents" / "Info.plist"
    binary = args.kext / "Contents" / "MacOS" / "AsusSMC"
    for p in (info_plist, binary):
        if not p.exists():
            raise SystemExit(f"缺少 {p}")

    with info_plist.open("rb") as f:
        version = plistlib.load(f).get("CFBundleVersion", "")
    if version != EXPECTED_VERSION:
        raise SystemExit(f"CFBundleVersion 为 {version}，本脚本只支持 {EXPECTED_VERSION}")

    out_kext = args.output or args.kext
    if args.output and args.output != args.kext:
        if out_kext.exists():
            shutil.rmtree(out_kext)
        shutil.copytree(args.kext, out_kext)
        info_plist = out_kext / "Contents" / "Info.plist"
        binary = out_kext / "Contents" / "MacOS" / "AsusSMC"

    data = binary.read_bytes()
    patched, offset = patch_binary(data)
    if offset == 0:
        print("已打过补丁，无需修改")
        return 0

    binary.write_bytes(patched)
    print(f"补丁完成：偏移 0x{offset:x}，83 E0 F0 -> 83 E0 00")
    print(f"输出：{out_kext}")
    print("部署：替换 EFI/OC/Kexts/AsusSMC.kext 后重启")
    return 0


if __name__ == "__main__":
    sys.exit(main())
