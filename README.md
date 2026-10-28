<div align="center">

# GKI BakaSU SUSFS

基于 GitHub Actions 构建 Android GKI 内核，集成 BakaSU 与 SUSFS。

简体中文 / [English](README_EN.md)

[![Release](https://img.shields.io/github/v/release/coolzyd9107/GKI_BakaSU_SUSFS?label=Release&style=flat-square&logo=github&logoColor=white&color=2ea44f)](https://github.com/zhuzhuzihan/GKI_BakaSU_SUSFS/releases)
[![构建 GKI 内核](https://github.com/zhuzhuzihan/GKI_BakaSU_SUSFS/actions/workflows/main.yml/badge.svg)](https://github.com/zhuzhuzihan/GKI_BakaSU_SUSFS/actions/workflows/main.yml)
[![Telegram](https://img.shields.io/static/v1?label=Telegram&message=Channel&color=0088cc)](https://t.me/BakaSUKernelBuilds)
[![BakaSU](https://img.shields.io/badge/KernelSU-BakaSU-5AA300?style=flat-square)](https://github.com/Baka-SU/BakaSU)
[![SUSFS](https://img.shields.io/badge/Filesystem-SUSFS-E67E22?style=flat-square)](https://gitlab.com/simonpunk/susfs4ksu)

</div>

## 项目说明

本仓库提供 Actions 云端构建流程，按 Android GKI KMI 和安全补丁级别生成 AnyKernel3 安装包。常规构建使用 BakaSU 同时可以自行在工作流配置中启用其它可选功能；也可以选择 Clean build，生成不集成 KernelSU、SUSFS 与可选功能补丁的内核。

内核版本与发布修订从 `data/android*/` 下的 JSON 矩阵读取，并由数据同步工作流定期更新。

## 重要通知

为减少 GitHub Actions 公共资源的长时间占用，维护者不再定期构建并发布所有 KMI，也不会在每次 BakaSU 更新后重跑全部版本。建议 Fork 本仓库，只构建设备需要的 KMI 或内核版本。下方提供从选择工作流到下载产物的操作说明。

## 支持的 KMI

| Android KMI | 内核系列 | `Build GKI Kernels` 的 `build_target` |
|---|---|---|
| Android 12 | 5.10 | `android12-5.10` |
| Android 13 | 5.10 | `android13-5.10` |
| Android 13 | 5.15 | `android13-5.15` |
| Android 14 | 5.15 | `android14-5.15` |
| Android 14 | 6.1 | `android14-6.1` |
| Android 15 | 6.6 | `android15-6.6` |
| Android 16 | 6.12 | `android16-6.12` |
| Android 17 | 6.18 | `android17-6.18` |

5.10 和 5.15 都对应多个 Android KMI。尤其 5.15 的 Android 13 与 Android 14 存在相同的内核版本号，不能仅凭 `5.15.xxx` 自动判断 KMI；请确认设备的 Android KMI 和内核系列，不要只按 Android 系统版本选择。Android 17 / 6.18 支持基础构建，部分附属组件会按上游支持状态自动跳过。

## 先确认设备的 KMI

构建目标必须与设备实际使用的 Android KMI 和内核系列一致。请从设备内核版本、ROM/设备维护者提供的信息或当前内核的 KMI 标识确认目标；上表中的 `build_target` 值可直接用于主工作流。

## 选择工作流

新用户建议使用 **Build GKI Kernels**。它能按 KMI 构建版本矩阵，也能筛选指定内核子版本。

| Actions 中的工作流 | 用途与行为 |
|---|---|
| **Build GKI Kernels** | 推荐入口。选择一个 KMI 会构建该 KMI 数据文件中的整组安全补丁版本（含 LTS），不只是一个内核。也可启用版本筛选来减少为一个子版本构建。默认 `all` 会构建所有 KMI，任务很多，不要仅为一台设备选择它。 |
| **Build Custom Android Kernel** | 手动填写 Android/KMI、子版本、OS 补丁级别和可选 revision，构建一个指定组合。适合需要精确指定安全补丁级别或 revision 的情况。 |
| **Build Kernel - Android 12 (5.10)** | 直接运行时构建 Android 12 / 5.10 的完整版本矩阵。 |
| **Build Kernel - 5.15 (Android 13/14)** | 直接从 Actions 运行时使用默认的 Android 13 / 5.15，构建完整矩阵。它的 `android_version` 只在被其他工作流调用时传入，因此手动运行不能选择 Android 14；要构建 Android 14 / 5.15，请使用主工作流或自定义工作流。 |
| **Build Kernel - Android 14 (6.1)**、**Android 15 (6.6)**、**Android 16 (6.12)**、**Android 17 (6.18)** | 各自构建对应 KMI 的完整版本矩阵。 |

这些固定 KMI 工作流每次会构建多个补丁版本。Android 13 / 5.10 没有单独的手动触发工作流，请通过 **Build GKI Kernels** 运行。`Build Custom Android Kernel` 则是手动指定单个版本的入口。`Prepare GKI Build Matrix` 和内核编译工作流是被其他工作流调用的内部流程，不需要直接运行。

矩阵来自对应的 `data/` JSON。5.10 会保留各月记录；5.15 和 6.x 会对重复的内核子版本只保留数据中的首个月度记录。存在 LTS 条目时也会加入构建。因此，即使选择单个 KMI，也可能产生很多 jobs 和 Artifacts。

## 使用主工作流：逐步操作

1. **Fork 仓库。** 在 GitHub 仓库页面点击 **Fork**，在自己的 fork 中构建，避免运行不需要的全部版本。进入 fork 的 **Actions** 页面；如果 GitHub 提示尚未启用 Actions，先启用它。
2. **打开工作流。** 在左侧选择 **Build GKI Kernels**，点击 **Run workflow**。工作流文件必须存在于默认分支才能显示；在分支下拉框中选择实际要运行的分支，通常是 `main`。
3. **选择构建范围。** 只为一台设备构建时，不要保留 `build_target: all` 默认值。根据设备 KMI 选择上表中的一个目标；此模式会构建该 KMI 的整组补丁版本。若只想构建指定子版本，按下方“只构建指定内核版本”设置筛选开关。
4. **设置可选项。** 首次构建建议保留功能默认值，只修改目标和确实需要的选项。参数含义见下表。
5. **启动并查看进度。** 点击表单底部的 **Run workflow**。在 Actions 运行详情页查看各版本任务；矩阵中每个版本会显示为单独的 job。若其中一个 job 失败，其他矩阵 job 仍会继续运行。
6. **下载产物。** 等运行完成后，在运行摘要页的 **Artifacts** 区域下载对应目标。若某个 job 失败，点开该 job 查看失败步骤和日志。

### 只构建指定内核子版本

在 **Build GKI Kernels** 表单中：

1. 将 `build_kernel_version` 设为 `true`。
2. 在 `kernel_version_filter` 输入完整内核版本，例如 `6.6.92`；输入 `6.6.X` 或 `6.6.x` 则筛选该 KMI 数据中的 6.6 版本矩阵。
3. 对 5.10，`kernel_android_version` 必须选择 `android12` 或 `android13`；对 5.15，必须选择 `android13` 或 `android14`。6.1、6.6、6.12、6.18 分别自动对应 Android 14、15、16、17。
4. 此模式以版本筛选为准，`build_target` 会被忽略。请勿留空 `kernel_version_filter`。

完整版本筛选按子版本号匹配数据矩阵，并采用该子版本遇到的第一条月度记录；它不是“选择任意安全补丁月份”的字段。例如同一个子版本若在多个补丁月份重复出现，不能在这里指定后一个月份。`X` 会展开为多个矩阵任务，可能仍然消耗较多构建时间。补丁级别、revision 和 LTS 信息来自对应的 [data](data/) JSON 文件。此筛选模式不会创建 Release。

## 表单参数说明

### 构建目标、发布与 BakaSU

| 参数 | 怎么填 |
|---|---|
| `build_target` | 默认值是 `all`。通常改为设备对应的单个 KMI；单选框不能一次选择多个目标，需要多个 KMI 时分别运行。一个目标仍会展开为该 KMI 的多个补丁版本。 |
| `release_type` | 默认值是 `Actions`。Fork 中使用此项只保留本次运行的 Artifacts。`Pre-Release` 和 `Release` 只会在 `zhuzhuzihan/GKI_BakaSU_SUSFS` 且未启用版本筛选时创建发布；fork 和指定版本筛选都不会创建 Release。固定 KMI 工作流和自定义工作流没有此选项。 |
| `kernelsu_branch` | BakaSU 分支名或完整 40 位 commit SHA。留空使用 `main`；主工作流表单默认已填 `main`。一次主工作流运行会先解析并固定提交。 |
| `clean_build` | 勾选后不集成 BakaSU、SUSFS 和可选功能补丁；其他补丁开关不再起作用。`build_bypass` 独立运行，仍会触发第二次构建。 |
| `version` | 可选的内核本地版本后缀，不用于选择 Android/KMI 或内核子版本。不需要自定义 `uname -r` 标识时留空。 |
| `build_time` | 构建时间戳。注意表单预填了 `Sun Dec 01 08:10:00 UTC 2024`；保持原值就会使用这个固定时间。要使用运行时当前 UTC 时间，请改填 `N` 或清空输入框。也可填写类似 `Sun Dec 01 08:10:00 UTC 2024` 的时间字符串。 |
| `change_log` | 仅用于上游发布通知文本；构建内核无需填写。 |

### 功能开关

| 参数 | 默认值与行为 |
|---|---|
| `cancel_susfs` | 默认 `false`，表示集成 SUSFS；勾选才是禁用。Clean build 会跳过 SUSFS；Android 17 / 6.18 也会自动跳过。 |
| `use_zram` | 默认关闭。主工作流的 Android 16 / 6.12 构建当前强制关闭；Android 17 / 6.18 自动跳过。 |
| `use_bbg` | 默认关闭；勾选应用 BBG 防格机补丁。 |
| `use_rekernel` | 默认关闭；勾选应用实验性的 Re-Kernel 驱动。Android 17 / 6.18 自动跳过。 |
| `cve_2026_43499_patch` | 默认开启。Android 17 / 6.18 会跳过该补丁链。 |
| `droidspaces` | 默认 `off`。5.10、5.15、6.1、6.6 可选 `678`、`123`、`345` 槽位；6.12 及以上使用同一通用补丁，任一非 `off` 值都表示启用。不同设备可能需要尝试不同槽位。 |
| `droidspaces_ntsync` | 默认关闭；只有同时启用 Droidspaces 才会生效。支持 Android 12 / 5.10、Android 13 / 5.15、Android 14 / 6.1、Android 15 / 6.6、Android 16 / 6.12。Android 13 / 5.10 和 Android 17 / 6.18 会跳过；Android 14 / 5.15 会因缺少兼容补丁而失败，请勿启用。 |
| `build_bypass` | 默认关闭。启用后额外完整编译一次，并在安装包中同时放入普通 `Image` 和 `Bypass-Image`，会显著增加运行时间。此模式用于诊断内核模块兼容性，不是绕过 root 检测。 |
| `use_nomount` | 默认关闭。启用 NoMount 内核支持还需要单独安装配套的 [NoMount 模块](https://github.com/maxsteeel/nomount)。Clean build 会跳过。 |

主工作流没有 OnePlus 8E 开关。需要时打开 **Build Custom Android Kernel** 并勾选 `supp_op`，或使用提供此输入的固定 KMI 工作流；Android 17 / 6.18 会跳过 OnePlus 8E 补丁。

## 手动指定一个构建：Build Custom Android Kernel

这个工作流不从版本矩阵推导参数，而是按表单输入构建一个组合。先打开对应的 [data](data/) JSON 文件：`entries` 中每项的 `kernel` 是完整内核版本、`date` 是 OS 补丁级别、`revision`（若存在）是发布修订；文件顶部的 `lts` 和 `lts_revision` 是单独的 LTS 目标。然后打开 **Build Custom Android Kernel** 并填写：

1. `android_version` 与 `kernel_version` 必须使用支持表中的配对，例如 `android15` + `6.6`。
2. `sub_level` 填完整内核版本最后一段。例如版本 `6.6.92` 填 `92`。
3. `os_patch_level` 填数据文件中的 `date`，例如 `2025-07`；LTS 目标填 `lts`。
4. 若所选 JSON 条目有 `revision`，填写完全相同的值，例如 `r14`。表单默认预填 `r11`，若该条目没有 revision，务必清空它；不匹配的 revision 会让工作流查找错误的上游 tag，通常导致失败。LTS revision（如有）查看 JSON 的 `lts_revision`。
5. 按需设置其他功能，点击 **Run workflow**。完成后从该运行的 **Artifacts** 下载；此工作流不创建 Release。

例如，当前 [Android 15 / 6.6 数据](data/android15/6.6.json)包含 `6.6.92`、补丁级别 `2025-07` 且没有 revision 的条目，可填写 `android15`、`6.6`、`92`、`2025-07`，并清空预填的 `r11`。优先填写数字子版本以便产物名称与所选版本对应；`X` 表示跟随所选分支当前源码，不能像数字版本一样明确标识构建结果。

## 构建完成后：下载与确认

Actions 的 Artifact 名称通常类似 `BakaSU_kernel-android15-6.6.92-2025-07`。下载后先解压 GitHub 下载的 Artifact ZIP，里面的 `...AnyKernel3.zip` 才是刷入用的安装包。若启用了 Bypass，安装包内会同时包含普通 `Image` 和 `Bypass-Image`。`AIO-REJ` 是补丁冲突诊断文件，不是内核安装包。

刷入前确认 Android KMI、内核系列和设备要求都匹配，并备份原厂 Boot 镜像、准备可用的恢复方式。不能仅凭 `6.6.xxx` 等内核版本号判断设备与产物兼容。

### 常见问题

- **Actions 中看不到工作流：** 确认 fork 已启用 Actions，且默认分支包含 `.github/workflows/` 下的工作流文件；运行时再从分支下拉框选择目标分支。
- **构建结果为失败：** 打开失败的 job，展开红色步骤查看日志。自定义构建先核对 Android/KMI 配对及 `revision`；使用 NTSync 时确认没有选择 Android 14 / 5.15。
- **主工作流整体显示失败，但有些版本成功：** 矩阵 job 独立运行。回到运行摘要查看每个 job，并下载成功 job 已上传的 Artifacts；失败 job 的日志可定位具体版本。
- **下载后找不到可刷入文件：** 先解压 GitHub 的 Artifact ZIP，再从解压目录中找到 `AnyKernel3.zip`。

## 其他工作流

- **Send Telegram Bot Notification**：手动发送通知，不用于构建内核。
- **Emergency Release Cleanup**：仅供仓库所有者处理发布清理，不要作为常规构建入口。

## Stock Config

若仓库中存在 `config/stock_defconfig`，构建会自动将其用于 `/proc/config.gz` 配置伪装；文件不存在时跳过此步骤。可以从设备当前官方内核取得 `/proc/config.gz`，解压后放入该目录并命名为 `stock_defconfig`。

## GKI 数据同步

[Update GKI Version Data](.github/workflows/update-gki-data.yml) 工作流每周一 UTC 08:00 自动运行，也可以手动触发。工作流会运行同步测试、更新 JSON、验证构建矩阵，并提交数据变更。

## 致谢

- [zzh20188](https://github.com/zzh20188)：曾经的上游 GKI 构建仓库作者，目前此仓库已脱离分支网络，zzh20188/GKI_KernelSU_SUSFS 将不再是此仓库的上游仓库
- [coolzyd9107](https://github.com/coolzyd9107)：本仓库维护者。
- [zhuzhuzihan](https://github.com/zhuzhuzihan)：工作流修复及 Telegram Bot 开发与维护。
- [TanakaLun](https://github.com/TanakaLun)：工作流修复与功能改进。
- [YC酱luyancib](https://github.com/luyanci)：Telegram Bot 与构建流程建议。
- [AlexLiuDev233](https://github.com/AlexLiuDev233)：工作流问题修复。
- [cctv18](https://github.com/cctv18)：工作流、6.12 支持及 SUSFS 问题修复建议。

新构建和重要变更通知见 [Telegram 频道](https://t.me/BakaSUKernelBuilds)；BakaSU 官方频道见 [BakaSU_Grp](https://t.me/BakaSU_Grp)。
