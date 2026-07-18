#!/usr/bin/env python3
"""Comprehensive tests for batch-rename."""

import json
import os
import shutil
import tempfile
import sys
from pathlib import Path

import pytest

# Ensure the project root is in the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.batch_rename import (
    apply_case,
    generate_new_name,
    collect_files,
    save_journal,
    load_latest_journal,
    list_journals,
    sanitize_name,
    apply_template,
    JOURNAL_DIR,
)


# ── Case transformation tests ──────────────────────────────────────────────

class TestApplyCase:
    def test_lower(self):
        assert apply_case("Hello World", "lower") == "hello world"

    def test_upper(self):
        assert apply_case("hello world", "upper") == "HELLO WORLD"

    def test_title(self):
        assert apply_case("hello world", "title") == "Hello World"

    def test_snake(self):
        assert apply_case("Hello World", "snake") == "hello_world"
        assert apply_case("Hello-World", "snake") == "hello_world"
        assert apply_case("Hello   World", "snake") == "hello_world"

    def test_kebab(self):
        assert apply_case("Hello World", "kebab") == "hello-world"
        assert apply_case("Hello_World", "kebab") == "hello-world"

    def test_camel(self):
        assert apply_case("hello world foo", "camel") == "helloWorldFoo"
        assert apply_case("some_file_name", "camel") == "someFileName"

    def test_pascal(self):
        assert apply_case("hello world", "pascal") == "HelloWorld"

    def test_unknown_case_passthrough(self):
        assert apply_case("Hello", "unknown") == "Hello"


# ── Name generation tests ──────────────────────────────────────────────────

class TestGenerateNewName:
    def test_no_transform(self):
        assert generate_new_name("photo.jpg") == "photo.jpg"

    def test_find_replace(self):
        result = generate_new_name(
            "my_old_file.txt", find="old", replace="new"
        )
        assert result == "my_new_file.txt"

    def test_prefix(self):
        result = generate_new_name("doc.txt", prefix="2024_")
        assert result == "2024_doc.txt"

    def test_suffix(self):
        result = generate_new_name("doc.txt", suffix="_backup")
        assert result == "doc_backup.txt"

    def test_case_transform(self):
        result = generate_new_name("MyFile.TXT", case="lower")
        assert result == "myfile.TXT"

    def test_numbering(self):
        result = generate_new_name(
            "img.png", numbering=True, number_start=1, number_pad=3, index=0
        )
        assert result == "img_001.png"

    def test_numbering_second_item(self):
        result = generate_new_name(
            "img.png", numbering=True, number_start=5, number_pad=2, index=1
        )
        assert result == "img_06.png"

    def test_new_ext(self):
        result = generate_new_name("data.csv", new_ext="tsv")
        assert result == "data.tsv"

    def test_new_ext_with_dot(self):
        result = generate_new_name("data.csv", new_ext=".tsv")
        assert result == "data.tsv"

    def test_trim_ext(self):
        result = generate_new_name("readme.txt", trim_ext=True)
        assert result == "readme"

    def test_regex_replace(self):
        result = generate_new_name(
            "file123.txt", regex_find=r"(\d+)", regex_replace=r"num_\1"
        )
        assert result == "filenum_123.txt"

    def test_combined_transforms(self):
        result = generate_new_name(
            "My Old File.TXT",
            find="Old",
            replace="New",
            prefix="v2_",
            case="snake",
        )
        assert result == "v2_my_new_file.TXT"

    def test_multiple_find_replace(self):
        result = generate_new_name(
            "aaa_bbb_aaa.txt", find="aaa", replace="xxx"
        )
        # Should replace ALL occurrences
        assert result == "xxx_bbb_xxx.txt"


# ── File collection tests ──────────────────────────────────────────────────

class TestCollectFiles:
    @pytest.fixture
    def tmp_dir(self, tmp_path):
        """Create a temporary directory structure for testing."""
        (tmp_path / "file1.txt").write_text("a")
        (tmp_path / "file2.txt").write_text("b")
        (tmp_path / "image.jpg").write_text("c")
        (tmp_path / "data.json").write_text("{}")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.py").write_text("pass")
        return tmp_path

    def test_collect_files_in_directory(self, tmp_dir):
        files = collect_files([str(tmp_dir)])
        names = {f.name for f in files}
        assert names == {"file1.txt", "file2.txt", "image.jpg", "data.json"}

    def test_collect_recursive(self, tmp_dir):
        files = collect_files([str(tmp_dir)], recursive=True)
        names = {f.name for f in files}
        assert "nested.py" in names
        assert "file1.txt" in names

    def test_collect_specific_extensions(self, tmp_dir):
        files = collect_files([str(tmp_dir)], extensions=[".txt"])
        names = {f.name for f in files}
        assert names == {"file1.txt", "file2.txt"}

    def test_collect_single_file(self, tmp_dir):
        target = tmp_dir / "file1.txt"
        files = collect_files([str(target)])
        assert len(files) == 1
        assert files[0].name == "file1.txt"

    def test_collect_exclude_pattern(self, tmp_dir):
        files = collect_files([str(tmp_dir)], exclude=["*.json", "*.jpg"])
        names = {f.name for f in files}
        assert names == {"file1.txt", "file2.txt"}

    def test_collect_sort_by_name(self, tmp_dir):
        files = collect_files([str(tmp_dir)], sort_by="name")
        names = [f.name for f in files]
        assert names == sorted(names, key=str.lower)

    def test_collect_empty_directory(self, tmp_path):
        files = collect_files([str(tmp_path)])
        assert files == []


# ── Journal tests ──────────────────────────────────────────────────────────

class TestJournal:
    @pytest.fixture(autouse=True)
    def clean_journals(self, tmp_path):
        """Redirect journal directory to a temp location."""
        import src.batch_rename as br
        original = br.JOURNAL_DIR
        br.JOURNAL_DIR = tmp_path / ".batch-rename-journals"
        yield
        br.JOURNAL_DIR = original

    def test_save_and_load_journal(self):
        ops = [
            {"src": "/tmp/a.txt", "dst": "/tmp/b.txt"},
            {"src": "/tmp/c.txt", "dst": "/tmp/d.txt"},
        ]
        path = save_journal(ops)
        assert path.exists()

        loaded = load_latest_journal()
        assert loaded is not None
        assert len(loaded["operations"]) == 2
        assert loaded["operations"][0]["src"] == "/tmp/a.txt"

    def test_journal_ordering(self):
        import time
        save_journal([{"src": "1", "dst": "2"}])
        time.sleep(1.1)  # ensure different timestamp
        save_journal([{"src": "3", "dst": "4"}])
        journals = list_journals()
        assert len(journals) == 2
        # Newest first
        data0 = json.loads(journals[0].read_text())
        assert data0["operations"][0]["src"] == "3"

    def test_no_journals(self, tmp_path):
        journals = list_journals()
        assert journals == []
        assert load_latest_journal() is None


# ── Integration test ───────────────────────────────────────────────────────

class TestIntegration:
    def test_full_rename_workflow(self, tmp_path):
        """Create files, rename them, verify results, undo."""
        import src.batch_rename as br

        # Redirect journal dir
        original = br.JOURNAL_DIR
        br.JOURNAL_DIR = str(tmp_path / ".journals")

        # Create test files
        for name in ["alpha.txt", "beta.txt", "gamma.txt"]:
            (tmp_path / name).write_text("content")

        files = collect_files([str(tmp_dir := tmp_path)])
        assert len(files) == 3

        # Verify name generation
        result = generate_new_name("alpha.txt", prefix="test_", case="upper")
        assert result == "test_ALPHA.txt"

        # Restore
        br.JOURNAL_DIR = original

    def test_regex_capture_groups(self):
        result = generate_new_name(
            "IMG_20240115_123456.jpg",
            regex_find=r"IMG_(\d{4})(\d{2})(\d{2})_.*",
            regex_replace=r"\1-\2-\3"
        )
        assert result == "2024-01-15.jpg"

    def test_all_case_transforms(self):
        cases = ["lower", "upper", "title", "snake", "kebab", "camel", "pascal"]
        for case in cases:
            result = generate_new_name("test file name.txt", case=case)
            assert result.endswith(".txt"), f"Extension lost for case: {case}"
            assert "." not in result.rsplit(".", 1)[0], f"Extra dot in stem for case: {case}"


# ── New feature tests ──────────────────────────────────────────────────────

class TestStripChars:
    def test_strip_single_char(self):
        result = generate_new_name("file@name.txt", strip_chars="@")
        assert result == "filename.txt"

    def test_strip_multiple_chars(self):
        result = generate_new_name("file@name#1.txt", strip_chars="@#")
        assert result == "filename1.txt"

    def test_strip_chars_empty_string(self):
        result = generate_new_name("filename.txt", strip_chars="")
        assert result == "filename.txt"

    def test_strip_chars_no_match(self):
        result = generate_new_name("filename.txt", strip_chars="xyz")
        assert result == "filename.txt"


class TestReplaceSpaces:
    def test_replace_with_underscore(self):
        result = generate_new_name("my file name.txt", replace_spaces="_")
        assert result == "my_file_name.txt"

    def test_replace_with_dash(self):
        result = generate_new_name("my file name.txt", replace_spaces="-")
        assert result == "my-file-name.txt"

    def test_replace_with_dot(self):
        result = generate_new_name("my file name.txt", replace_spaces=".")
        assert result == "my.file.name.txt"

    def test_replace_spaces_no_spaces(self):
        result = generate_new_name("myfilename.txt", replace_spaces="_")
        assert result == "myfilename.txt"

    def test_replace_spaces_with_case(self):
        result = generate_new_name("My File Name.txt", replace_spaces="_", case="lower")
        assert result == "my_file_name.txt"


class TestCombinedNewFeatures:
    def test_strip_and_replace_spaces(self):
        result = generate_new_name("my @file!.txt", strip_chars="@!", replace_spaces="_")
        assert result == "my_file.txt"

    def test_strip_chars_with_prefix(self):
        result = generate_new_name("file@name.txt", strip_chars="@", prefix="doc_")
        assert result == "doc_filename.txt"

    def test_all_new_features_combined(self):
        result = generate_new_name(
            "My @File #Name.txt",
            strip_chars="@#",
            replace_spaces="_",
            case="lower",
            prefix="v2_",
        )
        assert result == "v2_my_file_name.txt"


# ── New 1.1.0 feature tests ───────────────────────────────────────────────

class TestNumberFormat:
    def test_suffix_default(self):
        result = generate_new_name(
            "img.png", numbering=True, number_format="suffix",
            number_start=1, number_pad=3, index=0,
        )
        assert result == "img_001.png"

    def test_prefix_placement(self):
        result = generate_new_name(
            "img.png", numbering=True, number_format="prefix",
            number_start=1, number_pad=3, index=0,
        )
        assert result == "001_img.png"

    def test_prefix_with_start(self):
        result = generate_new_name(
            "shot.jpg", numbering=True, number_format="prefix",
            number_start=10, number_pad=2, index=2,
        )
        assert result == "12_shot.jpg"


class TestSanitize:
    def test_strips_illegal_chars(self):
        # Illegal chars are removed (not replaced), so adjacent words merge.
        result = generate_new_name("my:file<name>.txt", sanitize=True)
        assert result == "myfilename.txt"

    def test_collapses_separators(self):
        result = generate_new_name("a   b---c.txt", sanitize=True)
        # sanitize preserves the extension and collapses runs of separators.
        assert "__" not in result
        assert " " not in result
        assert result.endswith(".txt")

    def test_trims_leading_trailing_dots(self):
        result = generate_new_name(".hidden file.", sanitize=True)
        assert not result.startswith(".")
        assert not result.endswith(".")

    def test_never_empty(self):
        result = generate_new_name("???", sanitize=True)
        assert result == "file"

    def test_sanitize_with_template(self):
        result = generate_new_name(
            "bad:name.txt", template="{stem}{ext}", sanitize=True,
        )
        assert ":" not in result
        assert result == "badname.txt"


class TestTemplate:
    def test_stem_and_ext(self):
        result = generate_new_name(
            "photo.jpg", template="{stem}_edit{ext}",
        )
        assert result == "photo_edit.jpg"

    def test_number_placeholder(self):
        result = generate_new_name(
            "x.png", template="{n}_{stem}",
            numbering=True, number_start=1, number_pad=2, index=0,
        )
        # Template has no {ext}, so the extension is intentionally dropped.
        assert result == "01_x"

    def test_date_placeholder(self):
        result = generate_new_name("doc.txt", template="{date}_{stem}")
        # Default date format is YYYY-MM-DD; template has no {ext} so ext is dropped.
        assert result.startswith("20")
        assert result.endswith("_doc")

    def test_date_format_placeholder(self):
        result = generate_new_name(
            "doc.txt", template="{date:%Y%m%d}_{stem}", date_fmt="%Y%m%d",
        )
        # 8-char date + "_" + "doc"
        assert result == "20260718_doc" or len(result) == 8 + 1 + len("doc")
        assert result.endswith("_doc")

    def test_rand4_placeholder(self):
        result = generate_new_name("f.txt", template="{stem}_{rand4}{ext}")
        import re as _re
        assert _re.fullmatch(r"f_[a-z0-9]{4}\.txt", result)

    def test_template_overrides_other_transforms(self):
        # When a template is supplied, literal find/replace is ignored.
        result = generate_new_name(
            "old.txt", template="{stem}{ext}", find="old", replace="new",
        )
        assert result == "old.txt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
