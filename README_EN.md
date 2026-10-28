<div align="center">

# GKI BakaSU SUSFS

Build Android GKI kernels with BakaSU and SUSFS through GitHub Actions.

[简体中文](README.md) / English

[![Release](https://img.shields.io/github/v/release/coolzyd9107/GKI_BakaSU_SUSFS?label=Release&style=flat-square&logo=github&logoColor=white&color=2ea44f)](https://github.com/zhuzhuzihan/GKI_BakaSU_SUSFS/releases)
[![Build GKI Kernels](https://github.com/zhuzhuzihan/GKI_BakaSU_SUSFS/actions/workflows/main.yml/badge.svg)](https://github.com/zhuzhuzihan/GKI_BakaSU_SUSFS/actions/workflows/main.yml)
[![Telegram](https://img.shields.io/static/v1?label=Telegram&message=Channel&color=0088cc)](https://t.me/BakaSUKernelBuilds)
[![BakaSU](https://img.shields.io/badge/KernelSU-BakaSU-5AA300?style=flat-square)](https://github.com/Baka-SU/BakaSU)
[![SUSFS](https://img.shields.io/badge/Filesystem-SUSFS-E67E22?style=flat-square)](https://gitlab.com/simonpunk/susfs4ksu)

</div>

## Overview

This repository provides GitHub Actions workflows that generate AnyKernel3 installation packages for Android GKI kernel module interfaces (KMIs) and security patch levels. Regular builds use BakaSU and can include other optional features configured in the workflow. You can also select a clean build to produce a kernel without KernelSU, SUSFS, or optional feature patches.

Kernel versions and release revisions are read from the JSON matrices under `data/android*/` and updated periodically by the data synchronization workflow.

## Important Notice

To limit prolonged use of shared GitHub Actions resources, maintainers no longer run and publish every KMI regularly or rebuild all versions after each major BakaSU update. Fork this repository and build only the KMI or kernel version your device needs. The instructions below walk through choosing a workflow, filling in its inputs, and downloading the result.

## Supported KMIs

| Android KMI | Kernel Series | `build_target` in **Build GKI Kernels** |
|---|---|---|
| Android 12 | 5.10 | `android12-5.10` |
| Android 13 | 5.10 | `android13-5.10` |
| Android 13 | 5.15 | `android13-5.15` |
| Android 14 | 5.15 | `android14-5.15` |
| Android 14 | 6.1 | `android14-6.1` |
| Android 15 | 6.6 | `android15-6.6` |
| Android 16 | 6.12 | `android16-6.12` |
| Android 17 | 6.18 | `android17-6.18` |

Both 5.10 and 5.15 correspond to multiple Android KMIs. In particular, Android 13 and Android 14 on 5.15 can have identical kernel version numbers, so the KMI cannot be determined from `5.15.xxx` alone. Confirm both the device's Android KMI and kernel series instead of choosing based only on the Android OS version. Android 17 / 6.18 supports basic builds; some auxiliary components are skipped automatically according to upstream support.

## Confirm Your Device KMI First

The build target must match the Android KMI and kernel series actually used by your device. Confirm it from the device kernel version, ROM/device maintainer information, or the KMI identifier in the current kernel. The `build_target` values in the table above can be selected directly in the main workflow.

## Choose a Workflow

For most users, start with **Build GKI Kernels**. It can build a KMI version matrix or filter that matrix by kernel sublevel.

| Workflow in Actions | Purpose and behavior |
|---|---|
| **Build GKI Kernels** | Recommended entry point. Selecting one KMI builds the full set of security-patch versions in that KMI's data matrix, including LTS; it does not build just one kernel. `all` expands to every KMI and can start a very large number of jobs, so do not use it for a single device. |
| **Build Custom Android Kernel** | Manually enter Android/KMI, sublevel, OS patch level, and optional revision to build one specified combination. Use it when you need to select an exact patch level or revision. |
| **Build Kernel - Android 12 (5.10)** | Directly builds the full Android 12 / 5.10 version matrix. |
| **Build Kernel - 5.15 (Android 13/14)** | When manually dispatched from Actions, this uses its default Android 13 / 5.15 setting and builds the full matrix. `android_version` is only passed when another workflow calls it, so a manual run cannot select Android 14. Use the main or custom workflow for Android 14 / 5.15. |
| **Build Kernel - Android 14 (6.1)**, **Android 15 (6.6)**, **Android 16 (6.12)**, **Android 17 (6.18)** | Each builds the full version matrix for its KMI. |

These fixed-KMI workflows build multiple patch versions per run. Android 13 / 5.10 has no separate manually-triggerable workflow; run it through **Build GKI Kernels**. **Build Custom Android Kernel** is the manual single-version entry point. **Prepare GKI Build Matrix** and the kernel compilation workflow are reusable internal workflows and do not need to be run directly.

Matrices come from the matching JSON file under `data/`. For 5.10, separate monthly entries are retained; for 5.15 and 6.x, duplicate kernel sublevels are reduced to the first monthly entry in the data. An LTS entry is also included when present. As a result, selecting one KMI can still produce many jobs and Artifacts.

## Run the Main Workflow Step by Step

1. **Fork the repository.** Click **Fork** on GitHub and build in your fork instead of running versions you do not need. Open **Actions** in your fork and enable Actions if GitHub prompts you to do so.
2. **Open the workflow.** Select **Build GKI Kernels** from the left side and click **Run workflow**. The workflow file must exist on the default branch to appear; choose the branch you want to run, usually `main`, from the branch selector.
3. **Choose the build scope.** For one device, do not leave the default `build_target: all`. Select one target from the table above; this still builds that KMI's full patch-version matrix. To build only a selected sublevel, use the version-filter mode below.
4. **Set optional features.** For the first run, keep the feature defaults and change only the target and options you actually need. See the parameter tables below.
5. **Start and monitor.** Click **Run workflow** at the bottom of the form. On the run page, each version in the matrix appears as a separate job. Other matrix jobs continue if one job fails.
6. **Download the output.** After the run completes, download the appropriate target from **Artifacts** on the run summary page. If a job fails, open it and inspect the failed step and logs.

### Build a Selected Kernel Sublevel

In the **Build GKI Kernels** form:

1. Set `build_kernel_version` to `true`.
2. Enter a full kernel version in `kernel_version_filter`, such as `6.6.92`. Enter `6.6.X` or `6.6.x` to select the 6.6 version matrix for that KMI.
3. For 5.10, `kernel_android_version` must be `android12` or `android13`. For 5.15, it must be `android13` or `android14`. Versions 6.1, 6.6, 6.12, and 6.18 map automatically to Android 14, 15, 16, and 17 respectively.
4. This mode uses the version filter and ignores `build_target`. Do not leave `kernel_version_filter` empty.

A full-version filter matches by kernel sublevel and uses the first matching monthly record in the data matrix; it is not a field for choosing any security-patch month. If the same sublevel appears in multiple months, this filter cannot select a later month. Patch level, revision, and LTS information come from the corresponding JSON file under [data](data/). `X` expands to multiple matrix jobs and may still take considerable build time. This filtered mode does not create a Release.

## Form Parameters

### Target, Release, and BakaSU

| Parameter | How to use it |
|---|---|
| `build_target` | Defaults to `all`. Usually change it to the one KMI used by your device. The choice is single-select; run the workflow separately for additional KMIs. One target still expands to multiple patch versions. |
| `release_type` | Defaults to `Actions`, which keeps this run's Artifacts. `Pre-Release` and `Release` only publish from `zhuzhuzihan/GKI_BakaSU_SUSFS` when version filtering is off. Forks and filtered builds do not create Releases. Fixed-KMI and custom workflows do not have this option. |
| `kernelsu_branch` | A BakaSU branch name or full 40-character commit SHA. Blank uses `main`; the main workflow form is prefilled with `main`. The main workflow resolves and pins the commit at the start of the run. |
| `clean_build` | When checked, skips BakaSU, SUSFS, and optional feature patches; other patch switches no longer apply. `build_bypass` is independent and still triggers a second build. |
| `version` | Optional kernel local-version suffix. It does not select Android/KMI or the kernel sublevel. Leave blank unless you need a custom `uname -r` identifier. |
| `build_time` | Build timestamp. The form is prefilled with `Sun Dec 01 08:10:00 UTC 2024`; leaving that value unchanged uses this fixed timestamp. To use the current UTC time at run time, enter `N` or clear the field. You may also enter a timestamp such as `Sun Dec 01 08:10:00 UTC 2024`. |
| `change_log` | Used only in upstream release notifications; it is not needed to build a kernel. |

### Feature Switches

| Parameter | Default and behavior |
|---|---|
| `cancel_susfs` | Defaults to `false`, which means SUSFS is included; check it to disable SUSFS. Clean builds skip SUSFS, and Android 17 / 6.18 skips it automatically. |
| `use_zram` | Off by default. The main workflow currently forces it off for Android 16 / 6.12; Android 17 / 6.18 skips it automatically. |
| `use_bbg` | Off by default; check to apply the BBG anti-brick patch. |
| `use_rekernel` | Off by default; check to apply the experimental Re-Kernel driver. Android 17 / 6.18 skips it automatically. |
| `cve_2026_43499_patch` | On by default. Android 17 / 6.18 skips this patch series. |
| `droidspaces` | Defaults to `off`. For 5.10, 5.15, 6.1, and 6.6, choose slot `678`, `123`, or `345`. Kernel 6.12 and later use the same universal patch, so any non-`off` value enables it. Different devices may require trying different slots. |
| `droidspaces_ntsync` | Off by default and only applies when Droidspaces is enabled. Supported combinations are Android 12 / 5.10, Android 13 / 5.15, Android 14 / 6.1, Android 15 / 6.6, and Android 16 / 6.12. Android 13 / 5.10 and Android 17 / 6.18 skip it; Android 14 / 5.15 fails because no compatibility patch is available, so do not enable it there. |
| `build_bypass` | Off by default. Enabling it runs a second full compilation and puts both the standard `Image` and `Bypass-Image` in the package, significantly increasing run time. It is for diagnosing kernel-module compatibility, not bypassing root detection. |
| `use_nomount` | Off by default. NoMount kernel support also requires installing the companion [NoMount module](https://github.com/maxsteeel/nomount). Clean builds skip it. |

The main workflow does not expose the OnePlus 8E option. To use it, open **Build Custom Android Kernel** and enable `supp_op`, or choose a fixed-KMI workflow that exposes this input; Android 17 / 6.18 skips the OnePlus 8E patch.

## Manually Specify One Build: Build Custom Android Kernel

This workflow does not infer settings from the version matrix. It builds one combination from the values entered in the form. First open the matching [data](data/) JSON file: each object under `entries` has a full kernel version in `kernel`, an OS patch level in `date`, and a release `revision` when applicable. The top-level `lts` and `lts_revision` fields describe the separate LTS target. Then open **Build Custom Android Kernel** and fill in:

1. `android_version` and `kernel_version` must be a supported pair from the table above, such as `android15` + `6.6`.
2. Set `sub_level` to the last component of the full kernel version. For `6.6.92`, enter `92`.
3. Set `os_patch_level` to the entry's `date` in the JSON data, such as `2025-07`; use `lts` for an LTS target.
4. If the selected JSON entry has a `revision`, enter that exact value, such as `r14`. The form is prefilled with `r11`; clear it when the selected entry has no revision. A mismatched revision makes the workflow look for the wrong upstream tag and will usually fail. For LTS, check `lts_revision` if present.
5. Set any needed features and click **Run workflow**. Download the result from that run's **Artifacts**; this workflow does not create a Release.

For example, the current [Android 15 / 6.6 data](data/android15/6.6.json) has an entry for `6.6.92` with patch level `2025-07` and no revision. Enter `android15`, `6.6`, `92`, and `2025-07`, and clear the prefilled `r11`. Prefer a numeric sublevel so the artifact name identifies the selected version; `X` follows the current source branch and cannot identify the built sublevel as precisely as a number.

## After the Build: Download and Verify

An Actions artifact is usually named like `BakaSU_kernel-android15-6.6.92-2025-07`. Download and extract GitHub's Artifact ZIP first; the `...AnyKernel3.zip` inside it is the package to flash. If Bypass was enabled, that package contains both `Image` and `Bypass-Image`. `AIO-REJ` is a patch-conflict diagnostic artifact, not a kernel package.

Before flashing, verify that the Android KMI, kernel series, and device requirements match. Back up the stock Boot image and have a working recovery method. A version number such as `6.6.xxx` alone does not prove compatibility.

### Troubleshooting

- **The workflow is missing from Actions:** Enable Actions in your fork and make sure the default branch contains the workflow files under `.github/workflows/`; then choose the target branch from the run form.
- **A build fails:** Open the failed job and expand the red step to view its logs. For a custom build, verify the Android/KMI pair and `revision`; when enabling NTSync, do not select Android 14 / 5.15.
- **The main workflow is marked failed, but some versions succeeded:** Matrix jobs run independently. Review each job on the run summary and download Artifacts from successful jobs; use the failed job logs to identify the affected version.
- **The downloaded file does not look flashable:** Extract GitHub's Artifact ZIP first, then locate `AnyKernel3.zip` inside the extracted directory.

## Other Workflows

- **Send Telegram Bot Notification**: Sends a manual notification and is not used for kernel builds.
- **Emergency Release Cleanup**: Reserved for repository owners to handle release cleanup; it is not a regular build entry point.

## Stock Config

If `config/stock_defconfig` exists in the repository, the build automatically uses it to spoof the `/proc/config.gz` configuration. This step is skipped when the file does not exist. You can obtain `/proc/config.gz` from the device's current stock kernel, decompress it, place it in this directory, and name it `stock_defconfig`.

## GKI Data Synchronization

The [Update GKI Version Data](.github/workflows/update-gki-data.yml) workflow runs automatically every Monday at 08:00 UTC and can also be triggered manually. It runs synchronization tests, updates the JSON files, validates the build matrix, and commits the data changes.

## Acknowledgements

- [zzh20188](https://github.com/zzh20188): Author of the former upstream GKI build repository. This repository is no longer part of that fork network, and `zzh20188/GKI_KernelSU_SUSFS` is no longer its upstream repository.
- [coolzyd9107](https://github.com/coolzyd9107): Maintainer of this repository.
- [zhuzhuzihan](https://github.com/zhuzhuzihan): Workflow fixes and Telegram bot development and maintenance.
- [TanakaLun](https://github.com/TanakaLun): Workflow fixes and feature improvements.
- [YC酱luyancib](https://github.com/luyanci): Telegram bot and build workflow suggestions.
- [AlexLiuDev233](https://github.com/AlexLiuDev233): Workflow fixes.
- [cctv18](https://github.com/cctv18): Workflow, kernel 6.12 support, and SUSFS troubleshooting suggestions.

See the [Telegram channel](https://t.me/BakaSUKernelBuilds) for new builds and important updates. The official BakaSU channel is [BakaSU_Grp](https://t.me/BakaSU_Grp).
