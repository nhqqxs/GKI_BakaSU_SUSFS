#!/system/bin/sh
# uid_guard 名单注入器
#
# 名单唯一来源：ksud module config --internal uid_guard（键 uids，逗号分隔）。
# 由 WebUI 维护，也可以手动改：
#   su -c '/data/adb/ksu/bin/ksud module config --internal uid_guard set uids "a.b,c.d"'
#
# 为什么不用配置文件：/data/adb/modules/<id>/ 的内容被 SELinux 标成
# system_file，WebUI 的命令跑在 u:r:ksu:s0 域，写不进模块目录，所以名单
# 只能落在 KernelSU 自己的配置接口里。
#
# 名单为空 / 解析失败时保持功能关闭（fail-open），不会退化成“全量隐藏”。

MODDIR=${0%/*}
LOG="$MODDIR/last_boot.log"
KO="$MODDIR/ko/uid_guard_cfg.ko"
PLIST=/data/system/packages.list
MODID=uid_guard

[ -f "$KO" ] || KO="$MODDIR/uid_guard_cfg.ko"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] uid_guard boot" > "$LOG"

if [ ! -f "$KO" ]; then
	echo "MISS ko: $KO" >> "$LOG"
	exit 0
fi

# ---------------------------------------------------------------- ksud
KSUD=""
for cand in /data/adb/ksu/bin/ksud /data/adb/ksud; do
	if [ -x "$cand" ]; then
		KSUD="$cand"
		break
	fi
done
if [ -z "$KSUD" ] && command -v ksud >/dev/null 2>&1; then
	KSUD=$(command -v ksud)
fi

if [ -z "$KSUD" ]; then
	echo "MISS ksud, 无法读取名单" >> "$LOG"
	exit 0
fi

# ---------------------------------------------------------------- 名单
cfg=$("$KSUD" module config --internal "$MODID" get uids 2>/dev/null)
cfg_rc=$?
cfg=$(printf '%s' "$cfg" | tr -d '\r')

if [ "$cfg_rc" -ne 0 ]; then
	# 键不存在 = 还没在页面里勾选过任何应用
	echo "no uids configured, uid_guard stays off" >> "$LOG"
	exit 0
fi

TOKENS=$(printf '%s' "$cfg" | tr ',' '\n')
echo "source=ksud-config" >> "$LOG"

if [ -z "$(printf '%s' "$TOKENS" | tr -d '[:space:]')" ]; then
	echo "empty uid list, uid_guard stays off" >> "$LOG"
	exit 0
fi

# 等 PackageManagerService 把 packages.list 写出来（最多约 60 秒）
i=0
while [ "$i" -lt 30 ]; do
	if [ -r "$PLIST" ] && [ -s "$PLIST" ]; then
		break
	fi
	i=$((i + 1))
	sleep 2
done

# 包名 -> base uid（user 0）
uid_of() {
	pkg="$1"

	if [ -r "$PLIST" ]; then
		u=$(awk -v p="$pkg" '$1 == p { print $2; exit }' "$PLIST" 2>/dev/null)
		if [ -n "$u" ]; then
			echo "$u"
			return 0
		fi
	fi

	if command -v pm >/dev/null 2>&1; then
		esc=$(echo "$pkg" | sed 's/[.]/\\./g')
		u=$(pm list packages -U --user 0 2>/dev/null |
			sed -n "s/^package:$esc uid:\\([0-9][0-9]*\\)\$/\\1/p" |
			head -n 1)
		if [ -n "$u" ]; then
			echo "$u"
			return 0
		fi
	fi

	return 1
}

LIST=""
while IFS= read -r line || [ -n "$line" ]; do
	line=$(echo "$line" | tr -d ' \t\r')
	[ -z "$line" ] && continue

	case "$line" in
	*[!0-9]*)
		u=$(uid_of "$line") || {
			echo "MISS pkg: $line" >> "$LOG"
			continue
		}
		;;
	*)
		u="$line"
		;;
	esac

	case ",$LIST," in
	*",$u,"*) ;;
	*) LIST="${LIST:+$LIST,}$u" ;;
	esac
done <<TOKENS_EOF
$TOKENS
TOKENS_EOF

if [ -z "$LIST" ]; then
	echo "empty uid list, uid_guard stays off" >> "$LOG"
	exit 0
fi

echo "uids=$LIST" >> "$LOG"

# 允许重复执行：先卸载旧实例
if lsmod 2>/dev/null | grep -q '^uid_guard_cfg'; then
	rmmod uid_guard_cfg 2>/dev/null
fi

# 加载顺序：先 ksud 再 insmod。
#
# 5.10 GKI 开了 CONFIG_TRIM_UNUSED_KSYMS，uid_guard_set 只被本模块引用，
# 而裁剪表在模块编译前就生成，导致它的 __ksymtab 条目被裁掉。toybox 的
# insmod 因此在加载时报：
#   insmod: can't insert '...': unknown symbol in module, or unknown parameter
#   uid_guard_cfg: Unknown symbol uid_guard_set (err -2)
# 而 ksud insmod 同一条命令能成功，所以把 ksud 放在前面，避免每次开机都
# 先留一条误导性的错误。
loaded=0

if "$KSUD" insmod "$KO" uids="$LIST" 2>>"$LOG"; then
	loaded=1
	echo "loaded via ksud: $KSUD" >> "$LOG"
else
	echo "ksud insmod failed: $KSUD" >> "$LOG"
fi

if [ "$loaded" -eq 0 ]; then
	if insmod "$KO" uids="$LIST" 2>>"$LOG"; then
		loaded=1
		echo "loaded via insmod" >> "$LOG"
	else
		echo "insmod failed (both ksud and insmod)" >> "$LOG"
	fi
fi

# 把模块自己的日志落到文件里，便于确认名单是否真的进了内核。
# 内核在 syslog 模式下会把非 ASCII 字节转义成 \xNN，所以模块里的 pr_*
# 字符串一律用英文；出现中文说明是旧版 .ko。
# 成功时应看到 "injected N base uids, ret=0"，名单为空时是
# "list is empty, staying disabled"。
dmesg 2>/dev/null | grep "uid_guard_cfg" | tail -2 >> "$LOG"

# 注入完成后可以选择卸载配置模块，进一步减少常驻痕迹。
# 注意：卸载后名单仍在（已经写进内核），下次改名单需要重新加载本模块。
# rmmod uid_guard_cfg 2>/dev/null

exit 0
