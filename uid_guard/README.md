# 已迁移

> 本目录是早期版本，已迁移到独立仓库 **[nhqqxs/uid_guard](https://github.com/nhqqxs/uid_guard)**。
> 请以那边的 `patches/`、`module/`、`src/` 为准，这里的内容不再更新。

## 当前形态（摘要）

- **内核补丁**：本仓库 `custom_patches/0014-all-all-uid-guard.patch`
  （适用于 android12-5.10 ~ android17-6.18）。
- **注入器**：补丁已把 `drivers/misc/uid_guard_cfg.c` 放进内核树（`obj-m`），
  `.ko` 随内核构建产出，不需要单独准备内核树。
- **KernelSU / Magisk 模块**：在 [nhqqxs/uid_guard](https://github.com/nhqqxs/uid_guard) 的
  `module/` 目录。

## 快速开始

```sh
# 1. 打补丁（或直接用本仓库的 custom_patches 机制）
git apply custom_patches/0014-all-all-uid-guard.patch

# 2. 构建内核，取出注入器
find <内核构建目录> -name uid_guard_cfg.ko

# 3. 用 nhqqxs/uid_guard 的 build_module_zip.sh 打包模块并刷入
```
