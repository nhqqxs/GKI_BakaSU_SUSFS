# uid_guard 模块

内核侧补丁是 `custom_patches/0014-5.10.0-5.10.999-uid-guard.patch`，它把
`drivers/misc/uid_guard_cfg.c` 放进内核树（`obj-m`），构建内核时一并产出
`uid_guard_cfg.ko`。

本目录就是「可刷入模块」的内容，`build.yml` 打包 artifact 时直接从这里取，
不再依赖外部仓库：

| 文件 | 作用 |
|---|---|
| `module.prop` | 模块信息（v1.1.0） |
| `customize.sh` | 安装脚本（权限、提示） |
| `service.sh` | 开机读取名单并 insmod |
| `webroot/` | KernelSU WebUI：勾选要隐藏的应用，改动实时生效 |
| `src/` | `uid_guard_cfg.ko` 源码（排错 / 独立编译用） |
| `build_module_zip.sh` | 本地打 zip：`sh build_module_zip.sh [ko 路径]` |

名单存在 KernelSU 的 `ksud module config --internal uid_guard` 的 `uids` 键里，
不再用 `pkgs.conf`：模块目录被 SELinux 标成 `system_file`，WebUI 跑在
`u:r:ksu:s0` 写不进去，所以只能存 KernelSU 自己的配置接口。

## 用法

1. 构建内核时勾 `build_uid_guard`，从 artifact 里取 `*_uid_guard` 直接刷入；
2. 打开模块界面勾选要被隐藏的应用；
3. 重启，或 `su -c sh /data/adb/modules/uid_guard/service.sh` 立即生效。

名单为空时功能保持关闭（fail-open），不会退化成全量隐藏。
