#!/usr/bin/env python3
"""为 BakaSU 的 selinux_hide.c 补充 fsck_untrusted 策略特判。

背景
----
BakaSU/KernelSU 的「隐藏 SELinux 修改」通过 ksu_patch_text() 改写
selinux_write_op[] 函数指针来接管 sel_write_access，因此内核源码补丁
（custom_patches 里改 sel_write_access 的那些）在开关打开后不会执行。

它用 backup_sepolicy（KernelSU 加载策略前的副本）做查询，所以能隐藏
KernelSU 自己注入的类型与规则；但 backup 就是 ROM 策略本身，ROM 自己
放宽的规则它无能为力。

HyperOS 的 fsck_untrusted.te 里有：

    allow fsck_untrusted self:capability sys_admin;

AOSP 直到 Android 15 才用 neverallow 约束这一项，所以这条并不违反当时的
基线，但检测方（com.maple.detect 的 DP= 位掩码）会把它算作「策略被改动」
的证据。这里在 my_write_access 返回前把这对组合的 allowed 清零。

用法
----
    python3 scripts/patch_selinux_hide.py <KernelSU/kernel/feature/selinux_hide.c>

脚本是幂等的：已打过补丁会直接退出。
"""

import sys

MARKER = "zn_fsck_untrusted_guard"
ANCHOR = "    avd.seqno = 1;"

GUARD = (
    "    /*\n"
    "     * ROM 策略自身放开了 fsck_untrusted 的 sys_admin（AOSP 直到 15 才用\n"
    "     * neverallow 约束这一项），检测方会把它当成\"策略被改动\"的证据。\n"
    "     * %s\n"
    "     */\n"
    "    if (!strncmp(scon, \"u:r:fsck_untrusted\", 18) &&\n"
    "        !strncmp(tcon, \"u:r:fsck_untrusted\", 18))\n"
    "        avd.allowed = 0;\n"
    "\n"
) % MARKER


def main(argv):
    if len(argv) != 2:
        sys.exit("usage: patch_selinux_hide.py <path-to-selinux_hide.c>")

    path = argv[1]
    with open(path, encoding="utf-8") as fh:
        src = fh.read()

    if MARKER in src:
        print("already patched, skip: %s" % path)
        return 0

    if ANCHOR not in src:
        sys.exit("anchor not found in %s: %r" % (path, ANCHOR))

    if '"u:r:fsck_untrusted"' not in src:
        pass  # 首次打补丁，字符串还没进文件

    src = src.replace(ANCHOR, GUARD + ANCHOR, 1)

    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(src)

    print("patched fsck_untrusted guard -> %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
