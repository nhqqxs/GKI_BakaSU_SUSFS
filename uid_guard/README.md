# uid_guard

配套 `custom_patches/0014-all-all-uid-guard.patch` 的**名单注入器**。

内核补丁负责逻辑（在 `find_user()` 上过滤），本目录只负责一件事：
把用户维护的**包名列表**解析成 **base uid**，通过 `uid_guard_set()` 注入内核。

```
pkgs.conf（包名，与 HMA 隐藏列表一致）
      │  service.sh：包名 → base uid
      ▼
uid_guard_cfg.ko（module_param uids="10234,10456"，权限 0，不生成 sysfs 参数）
      │  调用 built-in 的 uid_guard_set()
      ▼
Image 内的 uid_guard（find_user() 门控，名单为空时不生效）
```

## 为什么 hook 在内核里、注入在模块里

| 职责 | 位置 | 原因 |
|---|---|---|
| 门控逻辑 | built-in 补丁 | 避免 text patch / kprobe 的 BL ±128MB 限制与回滚风险 |
| 名单注入 | `.ko`（只写数据） | AK3 保持通用可分发；名单不编进 `Image` |

`.ko` 在 `insmod` 时把参数交给内核，本身不改内核 text、不注册 kprobe、不做任何 hook。
名单变更不需要重编 `.ko`，改 `pkgs.conf` 后重新执行一次 `service.sh` 即可。

## 编译

必须使用**已打 `0014` 补丁**的内核树（需要 `uid_guard_set` 符号）：

```sh
cd src
make -C /path/to/kernel/common \
     M="$PWD" \
     ARCH=arm64 LLVM=1 LLVM_IAS=1 \
     modules
```

内核树必须**已经完整构建过**（`Module.symvers` 存在），否则外部模块编译会报
`module_layout` 之类的符号错误；只跑 `make modules_prepare` 不够。

如果内核树里没有 `include/linux/uid_guard.h`（即未打补丁），源码会自动退回到
本地 `extern` 声明；此时链接阶段可能报 `undefined`，可加
`KBUILD_MODPOST_WARN=1`，但**运行时内核必须打过补丁**，否则 `insmod` 会失败。

产物：`src/uid_guard_cfg.ko`，放进本目录或 `ko/`。

## 打包与安装

```sh
sh build_module_zip.sh src/uid_guard_cfg.ko     # 产出 uid_guard_v*.zip
```

1. 先刷内核（AK3 zip，内含 `0014` 补丁）；
2. 再刷本模块 zip（KernelSU / Magisk）；
3. 编辑 `/data/adb/modules/uid_guard/pkgs.conf`；
4. 重启，或手动 `su -c sh /data/adb/modules/uid_guard/service.sh`。

## pkgs.conf 格式

```text
# 每行一个包名，与 HMA 的隐藏列表保持一致
com.example.target_a
com.example.target_b

# 纯数字视为 base uid，用于“包只装在 work profile”等查不到 uid 的场景
1010234
```

- 名单按 **base uid**（user 0 的 app uid）存储，内核判定时对 uid 取模，
  因此**同一个包在所有用户/工作资料里的副本会一起生效**。
- 只应放第三方 app。系统组件（`AID_SYSTEMUI` 10139 等）不要放进来，
  否则会制造“系统组件报告未运行”的不可能事件。

## 生效与失败

- 名单为空、`insmod` 失败、包名查不到 → **功能保持关闭**（fail-open），
  不会退回“全量隐藏”，因此不会出现“全机没有任何第三方 app 在运行”的异常。
- 每次启动的结果写在 `last_boot.log`，包括 `MISS pkg: …` 与最终 uid 列表。

## 卸载

删除 `/data/adb/modules/uid_guard/` 后重启即可（内核补丁本身在名单为空时
不生效，无需回刷内核）。
