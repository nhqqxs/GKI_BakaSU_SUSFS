#!/bin/sh
# 把 module.prop / customize.sh / service.sh / pkgs.conf 和编译好的 .ko
# 打成可以直接刷入 KernelSU / Magisk 的模块 zip。
#
# 用法：
#   sh build_module_zip.sh [path/to/uid_guard_cfg.ko]
set -eu

cd "$(dirname "$0")"

KO="${1:-src/uid_guard_cfg.ko}"
if [ ! -f "$KO" ]; then
	echo "缺少 .ko: $KO" >&2
	echo "先用打了 0014 补丁的内核树编译：cd src && make -C <KDIR> M=\$PWD modules" >&2
	exit 1
fi

VER=$(sed -n 's/^version=//p' module.prop)
OUT="uid_guard_${VER}.zip"

mkdir -p ko
cp -f "$KO" ko/uid_guard_cfg.ko

rm -f "$OUT"
zip -r "$OUT" module.prop customize.sh service.sh pkgs.conf ko/uid_guard_cfg.ko

echo "打包完成: $(pwd)/$OUT"
