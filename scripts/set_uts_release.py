#!/usr/bin/env python3
"""把内核的 UTS_RELEASE 强制伪装成指定字符串。

原理
----
kernel 的 `uname -r` 来自 UTS_RELEASE，而 Makefile 里：

    filechk_kernel.release = \\
        echo "$(KERNELVERSION)$$(...scripts/setlocalversion...)"

    UTS_RELEASE=$(KERNELRELEASE)

即 KERNELRELEASE = KERNELVERSION（如 5.10.272）+ setlocalversion 输出（如 -android12-9-xxx），
UTS_RELEASE 再原样继承 KERNELRELEASE。所以只改 localversion 改不掉版本号部分。

本脚本把 filechk_kernel.release 整段替换成固定 echo，使 KERNELRELEASE
完全等于给定字符串。

为什么不动 SUBLEVEL
------------------
改 Makefile 的 SUBLEVEL 会让 LINUX_VERSION_CODE 一起变（5.10.272 -> 5.10.209），
可能有代码按 LINUX_VERSION_CODE 做分支判断。这里只覆盖 release 字符串，
LINUX_VERSION_CODE 保持真实值，副作用最小。

用法
----
    set_uts_release.py <kernel-common/Makefile> <full-release-string>

    full-release-string 例：5.10.209-android12-9-00019-g4ea09a298bb4-ab12292661

注意
----
UTS_RELEASE 在 Makefile 里有 64 字符上限（uts_len := 64），超长会直接编译失败。
"""
import io
import re
import sys

UTS_LEN = 64
ANCHOR = 'filechk_kernel.release'


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    path, release = sys.argv[1], sys.argv[2].strip()

    if not release:
        sys.exit('[uts-release] 空字符串，拒绝')
    if len(release) > UTS_LEN:
        sys.exit('[uts-release] 长度 %d 超过 UTS_LEN=%d，Makefile 会直接报错'
                 % (len(release), UTS_LEN))
    if not re.match(r'^\d+\.\d+\.\d+', release):
        sys.exit('[uts-release] 需要以 X.Y.Z 开头（完整版本串），收到: %s' % release)

    lines = io.open(path, encoding='utf-8', errors='replace').read().split('\n')

    # 定位 filechk_kernel.release = \ 这一行
    start = None
    for i, l in enumerate(lines):
        if ANCHOR in l and l.strip().startswith(ANCHOR):
            start = i
            break
    if start is None:
        sys.exit('[uts-release] 未在 %s 找到 %s 定义' % (path, ANCHOR))

    # 吃掉后续以 tab 开头的续行
    end = start + 1
    while end < len(lines) and lines[end].startswith('\t'):
        end += 1

    old_block = lines[start:end]
    new_block = ['filechk_kernel.release = \\',
                 '\techo "%s"' % release]
    lines[start:end] = new_block

    io.open(path, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))

    print('[uts-release] 已接管 %s（原 %d 行 -> 新 2 行）' % (ANCHOR, len(old_block)))
    for l in old_block:
        print('[uts-release]   - %s' % l.replace('\t', '  ')[:110])
    for l in new_block:
        print('[uts-release]   + %s' % l.replace('\t', '  ')[:110])
    print('[uts-release] UTS_RELEASE = %s  (%d/%d 字符)'
          % (release, len(release), UTS_LEN))
    print('[uts-release] LINUX_VERSION_CODE 不受影响'
          '（仍由 VERSION/PATCHLEVEL/SUBLEVEL 决定）')


if __name__ == '__main__':
    main()
