"""Validate GKI version data and generate a GitHub Actions matrix."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ANDROID_VERSION_RE = re.compile(r"^android\d+$")
KERNEL_VERSION_RE = re.compile(r"^\d+\.\d+$")
FULL_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
PATCH_LEVEL_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
REVISION_RE = re.compile(r"^r\d+$")

# kernel_filter 的 "lts" 后缀写法（X.Y.lts）：只取跟随分支的最新 LTS 行，
# 具体子版本号由构建时从 Makefile 读出，不用 JSON 里的快照号。
# 必须带 KMI 前缀，单独一个 "lts" 不表示任何范围，直接报错。
LTS_FILTER = "lts"


class DataError(ValueError):
    """Raised when a GKI version data file has an invalid schema."""


def _require_string(value: Any, field: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise DataError(f"{field} has an invalid value: {value!r}")
    return value


def _sublevel(version: Any, kernel_version: str, field: str) -> str:
    value = _require_string(version, field, FULL_VERSION_RE)
    match = FULL_VERSION_RE.fullmatch(value)
    assert match is not None
    if f"{match.group(1)}.{match.group(2)}" != kernel_version:
        raise DataError(
            f"{field} ({value}) does not match kernel_version ({kernel_version})"
        )
    return match.group(3)


def validate_data(
    data: Any,
    source: str = "data",
    expected_android_version: str | None = None,
    expected_kernel_version: str | None = None,
) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise DataError(f"{source} must contain a JSON object")

    android_version = _require_string(
        data.get("android_version"), "android_version", ANDROID_VERSION_RE
    )
    kernel_version = _require_string(
        data.get("kernel_version"), "kernel_version", KERNEL_VERSION_RE
    )
    if expected_android_version and android_version != expected_android_version:
        raise DataError(
            f"android_version ({android_version}) does not match {expected_android_version}"
        )
    if expected_kernel_version and kernel_version != expected_kernel_version:
        raise DataError(
            f"kernel_version ({kernel_version}) does not match {expected_kernel_version}"
        )
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        raise DataError("entries must be a non-empty array")

    seen_patch_levels: set[str] = set()
    legacy_lts = False
    for index, entry in enumerate(entries):
        field = f"entries[{index}]"
        if not isinstance(entry, dict):
            raise DataError(f"{field} must be an object")

        patch_level = entry.get("date")
        if patch_level == "lts":
            if legacy_lts:
                raise DataError("entries contains more than one lts target")
            legacy_lts = True
        else:
            _require_string(patch_level, f"{field}.date", PATCH_LEVEL_RE)

        if patch_level in seen_patch_levels:
            raise DataError(f"duplicate patch level: {patch_level}")
        seen_patch_levels.add(patch_level)
        _sublevel(entry.get("kernel"), kernel_version, f"{field}.kernel")

        revision = entry.get("revision")
        if revision is not None:
            _require_string(revision, f"{field}.revision", REVISION_RE)

    root_lts = data.get("lts")
    if root_lts is not None:
        if legacy_lts:
            raise DataError("lts must be stored either at the root or in entries, not both")
        _sublevel(root_lts, kernel_version, "lts")
        lts_revision = data.get("lts_revision")
        if lts_revision is not None:
            _require_string(lts_revision, "lts_revision", REVISION_RE)
    elif not legacy_lts:
        raise DataError("an lts target is required")

    return {
        "android_version": android_version,
        "kernel_version": kernel_version,
        "entries": entries,
        "lts": root_lts,
        "lts_revision": data.get("lts_revision"),
    }


def build_matrix(
    data: Any, deduplicate_sublevels: bool, kernel_filter: str = ""
) -> list[dict[str, str]]:
    """按 kernel_filter 生成构建矩阵。

    filter 语法（都带 KMI 前缀，前缀是数据文件自己的 kernel_version）：
      ""            整份名单（批量构建用）
      X.Y.X         整份名单（显式通配，同上）
      X.Y.Z         名单里该 kernel 的那一条（同一 kernel 有多条时必须带 revision）
      X.Y.Z-rN      名单里该 kernel + revision 的那一条，精确锁定到发布 tag
      X.Y.lts       LTS 行；实际子版本由构建时读 Makefile 决定

    X.Y.Z 不在名单里时不做报错，而是返回一行 os_patch_level=version：名单只是批量
    名单，单版本构建按上游的版本发布 tag（android<KMI>-<kernel>.<sub>[_rN]）走。
    """
    validated = validate_data(data)
    android_version = validated["android_version"]
    kernel_version = validated["kernel_version"]

    lts_only = False
    wildcard = False
    selected_sublevel = ""
    selected_revision = ""
    if kernel_filter:
        if kernel_filter == LTS_FILTER:
            raise DataError(
                f"kernel filter 需要带 KMI 前缀，例如 {kernel_version}.lts；"
                f"单独一个 lts 不表示任何范围"
            )
        if kernel_filter.endswith("." + LTS_FILTER):
            # 只接受带 KMI 前缀的写法（X.Y.lts），前缀必须与数据文件一致
            prefix = kernel_filter[: -len(LTS_FILTER) - 1]
            if prefix != kernel_version:
                raise DataError(
                    f"kernel filter does not match {kernel_version}: {kernel_filter!r}"
                )
            lts_only = True
        else:
            match = re.fullmatch(
                r"(\d+\.\d+)\.(\d+|[xX])(?:-([rR]\d+))?", kernel_filter
            )
            if not match or match.group(1) != kernel_version:
                raise DataError(
                    f"kernel filter does not match {kernel_version}: {kernel_filter!r}"
                )
            selected_sublevel = match.group(2)
            wildcard = selected_sublevel.lower() == "x"
            selected_revision = (match.group(3) or "").lower()
            if wildcard and selected_revision:
                raise DataError(f"通配写法不能带 revision: {kernel_filter!r}")

    matrix: list[dict[str, str]] = []
    seen_sublevels: set[str] = set()
    revision_choices: dict[str, set[str]] = {}

    for index, entry in enumerate(validated["entries"]):
        sublevel = _sublevel(
            entry["kernel"], kernel_version, f"entries[{index}].kernel"
        )
        patch_level = entry["date"]
        revision = str(entry.get("revision", ""))
        is_lts = patch_level == "lts"
        if not is_lts:
            revision_choices.setdefault(sublevel, set()).add(revision)

        if lts_only:
            if not is_lts:
                continue
        elif kernel_filter and not wildcard:
            # 带具体版本号时只认月度条目。lts 行的数字只是数据更新时的快照，
            # 分支仍在前进，用它选出来的是「最新」而不是那个固定版本。
            if is_lts or sublevel != selected_sublevel:
                continue
            if selected_revision and revision.lower() != selected_revision:
                continue
        # 精确到单个版本时不做去重，否则同一 kernel 的多个 revision 会被吞掉
        if (
            deduplicate_sublevels
            and not is_lts
            and not (kernel_filter and not wildcard)
            and sublevel in seen_sublevels
        ):
            continue
        if not is_lts:
            seen_sublevels.add(sublevel)

        matrix.append(
            {
                "android_version": android_version,
                "kernel_version": kernel_version,
                "sub_level": sublevel,
                "os_patch_level": patch_level,
                "revision": revision,
            }
        )

    if selected_sublevel and not selected_revision and not wildcard and len(matrix) > 1:
        choices = "、".join(
            f"{kernel_version}.{row['sub_level']}-{row['revision'] or '无 revision'}"
            f"（{row['os_patch_level']}）"
            for row in matrix
        )
        raise DataError(
            f"{kernel_filter} 在名单里对应多个条目：{choices}；"
            f"请带上 revision，例如 {kernel_version}.{selected_sublevel}-r10"
        )

    if validated["lts"] is not None:
        lts_sublevel = _sublevel(validated["lts"], kernel_version, "lts")
        if lts_only or not kernel_filter or wildcard:
            matrix.append(
                {
                    "android_version": android_version,
                    "kernel_version": kernel_version,
                    "sub_level": lts_sublevel,
                    "os_patch_level": "lts",
                    "revision": validated["lts_revision"] or "",
                }
            )

    if kernel_filter and not matrix:
        if selected_revision and selected_sublevel in revision_choices:
            # 名单里有这个 kernel，只是没有这个 revision：列出可用值
            choices = "、".join(
                f"{kernel_version}.{selected_sublevel}-{revision or '无 revision'}"
                for revision in sorted(revision_choices[selected_sublevel])
            )
            raise DataError(
                f"名单里没有 {kernel_version}.{selected_sublevel}-{selected_revision}；"
                f"该版本现有：{choices}"
            )
        # 名单里没有这个版本：回一行「按版本 tag 构建」，交给 build.yml 去上游找
        # android<KMI>-<kernel>.<sub>[_rN] 发布 tag。名单只是批量名单，单版本构建
        # 不需要它——例如 android12-5.10.272 直接对应 android12-5.10.272_r00。
        return [
            {
                "android_version": android_version,
                "kernel_version": kernel_version,
                "sub_level": selected_sublevel,
                "os_patch_level": "version",
                "revision": selected_revision,
            }
        ]
    if kernel_filter and not wildcard:
        return matrix[:1]

    return matrix


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_file", type=Path)
    parser.add_argument(
        "--kernel-filter",
        default="",
        help=(
            "select X.Y.Z (optionally -rN), major.minor.X for the whole roster, "
            "or major.minor.lts for the dynamic LTS target"
        ),
    )
    parser.add_argument(
        "--deduplicate-sublevels",
        action="store_true",
        help="keep the first monthly target for each kernel sublevel",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        with args.data_file.open("r", encoding="utf-8") as file:
            data = json.load(file)
        validated = validate_data(
            data,
            str(args.data_file),
            args.data_file.parent.name,
            args.data_file.stem,
        )
        matrix = build_matrix(validated, args.deduplicate_sublevels, args.kernel_filter)
    except (OSError, json.JSONDecodeError, DataError) as error:
        print(f"{args.data_file}: {error}", file=sys.stderr)
        return 1

    print(json.dumps(matrix, separators=(",", ":"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
