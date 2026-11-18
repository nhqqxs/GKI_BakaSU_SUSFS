"""build_target / kernel_filter 语义的回归测试。

重点：带具体版本号时只匹配带月度日期的条目；LTS 行必须用 `X.Y.lts`
选中，否则「数据快照号」会被误当成固定版本，构建出更新的分支头。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import prepare_matrix  # noqa: E402


def data_510() -> dict:
    """5.10 风格：LTS 行放在 entries 里（date=lts）。"""
    return {
        "android_version": "android12",
        "kernel_version": "5.10",
        "entries": [
            {"kernel": "5.10.198", "date": "2025-01", "revision": "r17"},
            {"kernel": "5.10.269", "date": "2026-10"},
            {"kernel": "5.10.272", "date": "lts"},
        ],
    }


def data_66() -> dict:
    """6.x 风格：LTS 在根节点，entries 只有月度条目。"""
    return {
        "android_version": "android15",
        "kernel_version": "6.6",
        "entries": [
            {"kernel": "6.6.120", "date": "2025-01", "revision": "r3"},
        ],
        "lts": "6.6.144",
        "lts_revision": "r2",
    }


def matrix(data: dict, kernel_filter: str = "", deduplicate: bool = True) -> list[dict]:
    validated = prepare_matrix.validate_data(data)
    return prepare_matrix.build_matrix(validated, deduplicate, kernel_filter)


class LtsFilterTests(unittest.TestCase):
    def test_xy_lts_selects_only_lts_row(self) -> None:
        rows = matrix(data_510(), "5.10.lts")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["os_patch_level"], "lts")
        self.assertEqual(rows[0]["sub_level"], "lts")

    def test_bare_lts_is_rejected(self) -> None:
        # 单独一个 lts 不表示任何范围：必须带 KMI 前缀，否则会误以为只编一个 KMI
        with self.assertRaises(prepare_matrix.DataError) as ctx:
            matrix(data_510(), "lts")
        self.assertIn("5.10.lts", str(ctx.exception))

    def test_xy_lts_works_for_root_style_data(self) -> None:
        root = matrix(data_66(), "6.6.lts")
        self.assertEqual(len(root), 1)
        self.assertEqual(root[0]["sub_level"], "lts")
        self.assertEqual(root[0]["os_patch_level"], "lts")
        self.assertEqual(root[0]["revision"], "r2")

    def test_prefix_must_match_kernel_version(self) -> None:
        with self.assertRaises(prepare_matrix.DataError):
            matrix(data_510(), "5.15.lts")


class PinnedVersionTests(unittest.TestCase):
    def test_monthly_version_is_selected(self) -> None:
        rows = matrix(data_510(), "5.10.269")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["sub_level"], "269")
        self.assertEqual(rows[0]["os_patch_level"], "2026-10")

    def test_version_missing_from_roster_falls_back_to_version_tag(self) -> None:
        # 5.10.272 只以 LTS 行的快照号出现；名单里没有月度条目时不再报错，
        # 而是回一行 os_patch_level=version，让 build.yml 去上游找版本 tag。
        rows = matrix(data_510(), "5.10.272")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["sub_level"], "272")
        self.assertEqual(rows[0]["os_patch_level"], "version")
        self.assertEqual(rows[0]["revision"], "")

    def test_version_tag_mode_keeps_explicit_revision(self) -> None:
        rows = matrix(data_510(), "5.10.272-r00")
        self.assertEqual(rows[0]["os_patch_level"], "version")
        self.assertEqual(rows[0]["revision"], "r00")

    def test_unknown_version_also_falls_back(self) -> None:
        rows = matrix(data_510(), "5.10.999")
        self.assertEqual(rows[0]["os_patch_level"], "version")
        self.assertEqual(rows[0]["sub_level"], "999")

    def test_root_lts_style_missing_version_falls_back(self) -> None:
        rows = matrix(data_66(), "6.6.144")
        self.assertEqual(rows[0]["os_patch_level"], "version")

    def test_version_without_revision_uses_roster_entry(self) -> None:
        rows = matrix(data_510(), "5.10.198")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["revision"], "r17")
        self.assertEqual(rows[0]["os_patch_level"], "2025-01")

    def test_version_with_revision_is_selected(self) -> None:
        rows = matrix(data_510(), "5.10.198-r17")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["sub_level"], "198")
        self.assertEqual(rows[0]["revision"], "r17")
        self.assertEqual(rows[0]["os_patch_level"], "2025-01")
        # 大小写不敏感，R17 也认
        self.assertEqual(matrix(data_510(), "5.10.198-R17")[0]["revision"], "r17")

    def test_unknown_revision_lists_available_choices(self) -> None:
        with self.assertRaises(prepare_matrix.DataError) as ctx:
            matrix(data_510(), "5.10.198-r99")
        message = str(ctx.exception)
        self.assertIn("5.10.198-r17", message)

    def test_ambiguous_version_requires_revision(self) -> None:
        data = data_510()
        data["entries"].insert(1, {"kernel": "5.10.101", "date": "2022-04", "revision": "r20"})
        data["entries"].insert(1, {"kernel": "5.10.101", "date": "2022-05", "revision": "r12"})
        with self.assertRaises(prepare_matrix.DataError) as ctx:
            matrix(data, "5.10.101")
        message = str(ctx.exception)
        self.assertIn("多个条目", message)
        self.assertIn("5.10.101-r20", message)
        self.assertIn("5.10.101-r12", message)

    def test_monthly_row_wins_when_lts_row_has_same_sublevel(self) -> None:
        data = data_510()
        data["entries"].insert(2, {"kernel": "5.10.272", "date": "2026-11", "revision": "r1"})
        rows = matrix(data, "5.10.272")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["os_patch_level"], "2026-11")
        self.assertEqual(rows[0]["revision"], "r1")


class MatrixShapeTests(unittest.TestCase):
    def test_wildcard_keeps_every_entry_plus_lts(self) -> None:
        rows = matrix(data_510(), "5.10.X")
        self.assertEqual([row["sub_level"] for row in rows], ["198", "269", "lts"])
        self.assertEqual(rows[-1]["os_patch_level"], "lts")

    def test_no_filter_keeps_every_entry_plus_lts(self) -> None:
        self.assertEqual(len(matrix(data_510())), 3)
        self.assertEqual(len(matrix(data_66())), 2)

    def test_deduplicate_skips_repeated_sublevels(self) -> None:
        data = data_510()
        data["entries"].append({"kernel": "5.10.198", "date": "2025-02", "revision": "r19"})
        rows = matrix(data, deduplicate=True)
        self.assertEqual([row["sub_level"] for row in rows], ["198", "269", "lts"])
        rows_all = matrix(data, deduplicate=False)
        self.assertEqual(len(rows_all), 4)


if __name__ == "__main__":
    unittest.main()
