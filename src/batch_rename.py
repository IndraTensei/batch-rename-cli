#!/usr/bin/env python3
"""
batch-rename — A powerful, safe, and intuitive batch renaming CLI tool.

Rename files in bulk with preview, undo, regex, numbering,
case conversion, find-and-replace, date insertion, and more.
"""

import argparse
import json
import os
import re
import sys
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

__version__ = "1.0.0"

# ── Color helpers ──────────────────────────────────────────────────────────

class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"

    @classmethod
    def disable(cls):
        """Disable all colors (for non-tty output)."""
        cls.RESET = cls.BOLD = cls.DIM = ""
        cls.RED = cls.GREEN = cls.YELLOW = ""
        cls.BLUE = cls.MAGENTA = cls.CYAN = cls.GRAY = ""


if not sys.stdout.isatty():
    Colors.disable()


def colorize(text: str, *codes: str) -> str:
    return "".join(codes) + text + Colors.RESET


# ── Undo journal ───────────────────────────────────────────────────────────

JOURNAL_DIR = Path.home() / ".batch-rename-journals"


def save_journal(operations: list[dict]) -> Path:
    """Save rename operations to a timestamped journal file for undo."""
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    journal_path = JOURNAL_DIR / f"rename_{timestamp}.json"
    data = {
        "timestamp": timestamp,
        "operations": operations,
    }
    journal_path.write_text(json.dumps(data, indent=2))
    return journal_path


def load_latest_journal() -> Optional[dict]:
    """Load the most recent journal file."""
    if not JOURNAL_DIR.exists():
        return None
    journals = sorted(JOURNAL_DIR.glob("rename_*.json"), reverse=True)
    if not journals:
        return None
    return json.loads(journals[0].read_text())


def list_journals() -> list[Path]:
    """List all journal files, newest first."""
    if not JOURNAL_DIR.exists():
        return []
    return sorted(JOURNAL_DIR.glob("rename_*.json"), reverse=True)


# ── Renaming engine ────────────────────────────────────────────────────────

def apply_case(name: str, case: str) -> str:
    """Apply case transformation to a filename (without extension)."""
    if case == "lower":
        return name.lower()
    elif case == "upper":
        return name.upper()
    elif case == "title":
        return name.title()
    elif case == "snake":
        return re.sub(r"[\s\-]+", "_", name).lower()
    elif case == "kebab":
        return re.sub(r"[\s_]+", "-", name).lower()
    elif case == "camel":
        parts = re.split(r"[\s_\-]+", name)
        return parts[0].lower() + "".join(p.title() for p in parts[1:])
    elif case == "pascal":
        parts = re.split(r"[\s_\-]+", name)
        return "".join(p.title() for p in parts)
    return name


def generate_new_name(
    original: str,
    find: Optional[str] = None,
    replace: Optional[str] = None,
    regex_find: Optional[str] = None,
    regex_replace: Optional[str] = None,
    prefix: str = "",
    suffix: str = "",
    case: Optional[str] = None,
    numbering: bool = False,
    number_start: int = 1,
    number_pad: int = 2,
    index: int = 0,
    date_fmt: Optional[str] = None,
    trim_ext: bool = False,
    new_ext: Optional[str] = None,
    strip_chars: Optional[str] = None,
    replace_spaces: Optional[str] = None,
) -> str:
    """Generate a new filename based on the given transformation rules."""
    stem = Path(original).stem
    ext = Path(original).suffix

    # 1. Find & replace (literal)
    if find is not None and replace is not None:
        stem = stem.replace(find, replace)

    # 2. Regex find & replace
    if regex_find is not None and regex_replace is not None:
        stem = re.sub(regex_find, regex_replace, stem)

    # 3. Case transformation
    if case:
        stem = apply_case(stem, case)

    # 4. Numbering
    if numbering:
        num_str = str(number_start + index).zfill(number_pad)
        stem = f"{stem}_{num_str}"

    # 5. Date insertion
    if date_fmt:
        date_str = datetime.now().strftime(date_fmt)
        stem = f"{stem}_{date_str}"

    # 6. Strip characters
    if strip_chars:
        for ch in strip_chars:
            stem = stem.replace(ch, "")

    # 7. Replace spaces
    if replace_spaces is not None:
        stem = stem.replace(" ", replace_spaces)

    # 8. Prefix / Suffix
    stem = prefix + stem + suffix

    # 9. Extension handling
    if trim_ext:
        ext = ""
    elif new_ext is not None:
        ext = new_ext if new_ext.startswith(".") else f".{new_ext}"

    return stem + ext


def collect_files(
    paths: list[str],
    recursive: bool = False,
    include_dirs: bool = False,
    extensions: Optional[list[str]] = None,
    exclude: Optional[list[str]] = None,
    sort_by: str = "name",
) -> list[Path]:
    """Collect and filter files from the given paths."""
    files: list[Path] = []

    for p_str in paths:
        p = Path(p_str)
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            if recursive:
                for item in sorted(p.rglob("*")):
                    if item.is_file() or (include_dirs and item.is_dir()):
                        files.append(item)
            else:
                for item in sorted(p.iterdir()):
                    if item.is_file() or (include_dirs and item.is_dir()):
                        files.append(item)

    # Filter by extension
    if extensions:
        ext_set = {e if e.startswith(".") else f".{e}" for e in extensions}
        files = [f for f in files if f.suffix in ext_set or f.is_dir()]

    # Exclude patterns
    if exclude:
        import fnmatch
        filtered = []
        for f in files:
            if not any(fnmatch.fnmatch(f.name, pat) for pat in exclude):
                filtered.append(f)
        files = filtered

    # Sort
    if sort_by == "name":
        files.sort(key=lambda f: f.name.lower())
    elif sort_by == "date":
        files.sort(key=lambda f: f.stat().st_mtime)
    elif sort_by == "size":
        files.sort(key=lambda f: f.stat().st_size)
    elif sort_by == "none":
        pass  # keep as-is

    return files


# ── Preview rendering ──────────────────────────────────────────────────────

def render_preview(operations: list[tuple[Path, Path]], max_width: int = 80) -> str:
    """Render a colored preview of rename operations."""
    if not operations:
        return colorize("  No files to rename.", Colors.GRAY)

    lines = []
    max_src = max(len(str(op[0].name)) for op in operations)
    max_src = min(max_src, 40)

    for src, dst in operations:
        src_name = src.name
        dst_name = dst.name
        if src_name == dst_name:
            lines.append(
                colorize(f"  {src_name:<{max_src}}  →  ", Colors.GRAY)
                + colorize(dst_name, Colors.DIM)
                + colorize(" (unchanged)", Colors.GRAY)
            )
        else:
            lines.append(
                colorize(f"  {src_name:<{max_src}}  →  ", Colors.YELLOW)
                + colorize(dst_name, Colors.GREEN)
            )

    return "\n".join(lines)


# ── Main rename logic ─────────────────────────────────────────────────────

def perform_rename(
    files: list[Path],
    args: argparse.Namespace,
    dry_run: bool = False,
) -> list[tuple[Path, Path]]:
    """Perform (or simulate) rename operations. Returns list of (src, dst) tuples."""
    operations: list[tuple[Path, Path]] = []
    journal_ops: list[dict] = []

    for i, f in enumerate(files):
        new_name = generate_new_name(
            original=f.name,
            find=args.find,
            replace=args.replace,
            regex_find=args.regex_find,
            regex_replace=args.regex_replace,
            prefix=args.prefix,
            suffix=args.suffix,
            case=args.case,
            numbering=args.numbering,
            number_start=args.number_start,
            number_pad=args.number_pad,
            index=i,
            date_fmt=args.date,
            trim_ext=args.trim_ext,
            new_ext=args.new_ext,
            strip_chars=args.strip_chars,
            replace_spaces=args.replace_spaces,
        )
        dst = f.parent / new_name
        operations.append((f, dst))

    if dry_run:
        return operations

    # Check for conflicts
    dst_paths = [dst for _, dst in operations]
    if len(dst_paths) != len(set(dst_paths)):
        # Check if it's just files staying the same
        conflicts = [p for p in dst_paths if dst_paths.count(p) > 1]
        if any(
            src != dst
            for src, dst in operations
            if dst in conflicts
        ):
            print(
                colorize("Warning: Destination conflicts detected!", Colors.RED)
            )
            print(colorize("  Use --force to override.", Colors.GRAY))

    # Interactive mode: prompt for each rename
    if getattr(args, 'interactive', False):
        for src, dst in operations:
            if src == dst:
                continue
            prompt = f"  Rename {colorize(src.name, Colors.YELLOW)} -> {colorize(dst.name, Colors.GREEN)}? [y/N/a(ll)] "
            try:
                answer = input(prompt).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print(colorize("\n  Aborted.", Colors.RED))
                return operations
            if answer == 'a':
                # Continue with all remaining without prompting
                for s, d in operations[operations.index((src, dst)) + 1:]:
                    if s == d:
                        continue
                    if d.exists() and not args.force:
                        print(colorize(f"  Skipping {s.name}: destination exists", Colors.YELLOW))
                        continue
                    try:
                        shutil.move(str(s), str(d))
                        journal_ops.append({"src": str(s), "dst": str(d)})
                    except OSError as e:
                        print(colorize(f"  Error renaming {s.name}: {e}", Colors.RED))
                break
            elif answer == 'y':
                if dst.exists() and not args.force:
                    print(colorize(f"  Skipping {src.name}: destination exists", Colors.YELLOW))
                    continue
                try:
                    shutil.move(str(src), str(dst))
                    journal_ops.append({"src": str(src), "dst": str(dst)})
                except OSError as e:
                    print(colorize(f"  Error renaming {src.name}: {e}", Colors.RED))
            else:
                print(colorize(f"  Skipped: {src.name}", Colors.GRAY))

        if journal_ops:
            journal_path = save_journal(journal_ops)
            print(
                colorize(f"\n  Undo journal saved: ", Colors.DIM)
                + colorize(str(journal_path), Colors.GRAY)
            )
        return operations

    # Execute renames (non-interactive)
    for src, dst in operations:
        if src == dst:
            continue
        if dst.exists() and not args.force:
            print(
                colorize(f"  Skipping {src.name}: destination exists", Colors.YELLOW)
            )
            continue
        try:
            shutil.move(str(src), str(dst))
            journal_ops.append({"src": str(src), "dst": str(dst)})
        except OSError as e:
            print(colorize(f"  Error renaming {src.name}: {e}", Colors.RED))

    if journal_ops:
        journal_path = save_journal(journal_ops)
        print(
            colorize(f"\n  Undo journal saved: ", Colors.DIM)
            + colorize(str(journal_path), Colors.GRAY)
        )

    return operations


def undo_last():
    """Undo the most recent rename operation."""
    journal = load_latest_journal()
    if not journal:
        print(colorize("  No undo journal found.", Colors.YELLOW))
        return

    ops = journal["operations"]
    undone = 0
    errors = 0

    for op in reversed(ops):
        src = Path(op["src"])
        dst = Path(op["dst"])
        if dst.exists() and not src.exists():
            try:
                shutil.move(str(dst), str(src))
                undone += 1
            except OSError as e:
                print(colorize(f"  Error: {e}", Colors.RED))
                errors += 1
        else:
            print(
                colorize(f"  Skipped: {dst.name} (source doesn't exist or dest already present)", Colors.GRAY)
            )

    print(
        colorize(f"\n  ✅ Undone: {undone} operation(s)", Colors.GREEN)
        + (colorize(f"  ❌ Errors: {errors}", Colors.RED) if errors else "")
    )


def show_journals():
    """List all available undo journals."""
    journals = list_journals()
    if not journals:
        print(colorize("  No undo journals found.", Colors.GRAY))
        return

    print(colorize(f"\n  📚 Undo Journals ({len(journals)} total):\n", Colors.BOLD))
    for j in journals:
        data = json.loads(j.read_text())
        ts = data["timestamp"]
        ops = len(data["operations"])
        print(
            colorize(f"    {ts}", Colors.CYAN)
            + colorize(f"  —  {ops} operation(s)", Colors.GRAY)
        )
    print()


# ── CLI entry point ────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="batch-rename",
        description=(
            colorize("📦 batch-rename", Colors.BOLD + Colors.CYAN)
            + colorize(" — Powerful batch file renaming made simple", Colors.GRAY)
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  batch-rename *.txt --find "old" --replace "new"
  batch-rename photos/ --prefix "vacation_" --numbering --case lower
  batch-rename *.jpg --regex-find "(\\d+)" --regex-replace "img_\\1"
  batch-rename docs/ --case snake --new-ext md
  batch-rename . --recursive --exclude "*.git*" --case kebab
  batch-rename --undo
  batch-rename --journals
        """,
    )

    parser.add_argument(
        "paths",
        nargs="*",
        help="Files or directories to rename",
    )
    parser.add_argument(
        "--find", "-f",
        help="Text to find in filenames",
    )
    parser.add_argument(
        "--replace", "-r",
        help="Replacement text",
    )
    parser.add_argument(
        "--regex-find",
        help="Regex pattern to find",
    )
    parser.add_argument(
        "--regex-replace",
        help="Regex replacement (supports \\1, \\2, etc.)",
    )
    parser.add_argument(
        "--prefix", "-p",
        default="",
        help="Add prefix to filenames",
    )
    parser.add_argument(
        "--suffix", "-s",
        default="",
        help="Add suffix (before extension)",
    )
    parser.add_argument(
        "--case", "-c",
        choices=["lower", "upper", "title", "snake", "kebab", "camel", "pascal"],
        help="Case transformation",
    )
    parser.add_argument(
        "--numbering", "-n",
        action="store_true",
        help="Add sequential numbering",
    )
    parser.add_argument(
        "--number-start",
        type=int,
        default=1,
        help="Starting number (default: 1)",
    )
    parser.add_argument(
        "--number-pad",
        type=int,
        default=2,
        help="Number padding width (default: 2)",
    )
    parser.add_argument(
        "--date", "-d",
        help="Append date (strftime format, e.g. %%Y-%%m-%%d)",
    )
    parser.add_argument(
        "--new-ext",
        help="Change file extension",
    )
    parser.add_argument(
        "--trim-ext",
        action="store_true",
        help="Remove file extensions",
    )
    parser.add_argument(
        "--recursive", "-R",
        action="store_true",
        help="Process directories recursively",
    )
    parser.add_argument(
        "--include-dirs",
        action="store_true",
        help="Also rename directories (not just files)",
    )
    parser.add_argument(
        "--extensions", "-e",
        nargs="+",
        help="Only process files with these extensions",
    )
    parser.add_argument(
        "--exclude", "-x",
        nargs="+",
        help="Exclude files matching these glob patterns",
    )
    parser.add_argument(
        "--sort",
        choices=["name", "date", "size", "none"],
        default="name",
        help="Sort order (default: name)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without renaming",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files",
    )
    parser.add_argument(
        "--undo",
        action="store_true",
        help="Undo the last rename operation",
    )
    parser.add_argument(
        "--journals",
        action="store_true",
        help="List all undo journals",
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"batch-rename {__version__}",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    parser.add_argument(
        "--strip-chars",
        help="Remove specific characters from filenames (e.g. \"!@#\")",
    )
    parser.add_argument(
        "--replace-spaces",
        help="Replace spaces with the given character (e.g. \"_\" or \"-\")",
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Prompt before each rename",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.no_color:
        Colors.disable()

    # Handle undo
    if args.undo:
        print(colorize("\n  🔄 Undo last rename operation\n", Colors.BOLD + Colors.MAGENTA))
        undo_last()
        return

    # Handle journals listing
    if args.journals:
        show_journals()
        return

    # Validate: need paths
    if not args.paths:
        parser.print_help()
        print(colorize("\n  ❌ Error: No files or directories specified.\n", Colors.RED))
        sys.exit(1)

    # Validate: need at least one transformation
    transforms = [
        args.find, args.regex_find, args.prefix, args.suffix,
        args.case, args.numbering, args.date, args.new_ext, args.trim_ext,
        args.strip_chars, args.replace_spaces,
    ]
    if not any(t for t in transforms if t):
        print(
            colorize("\n  ❌ Error: No transformation specified.\n", Colors.RED)
        )
        print(
            colorize("  Use --find/--replace, --prefix, --case, --numbering, etc.\n", Colors.GRAY)
        )
        sys.exit(1)

    # Collect files
    files = collect_files(
        paths=args.paths,
        recursive=args.recursive,
        include_dirs=args.include_dirs,
        extensions=args.extensions,
        exclude=args.exclude,
        sort_by=args.sort,
    )

    if not files:
        print(colorize("\n  📂 No matching files found.\n", Colors.YELLOW))
        sys.exit(0)

    # Perform rename (or dry run)
    mode_label = colorize("DRY RUN", Colors.YELLOW) if args.dry_run else colorize("RENAMING", Colors.GREEN)
    print(
        colorize(f"\n  📦 batch-rename v{__version__} — ", Colors.BOLD)
        + mode_label
        + colorize(f"  {len(files)} file(s)\n", Colors.BOLD)
    )

    operations = perform_rename(files, args, dry_run=args.dry_run)

    # Show preview
    print(render_preview(operations))
    print()

    if args.dry_run:
        print(
            colorize("  💡 This was a dry run. ", Colors.DIM)
            + colorize("Remove --dry-run to apply.\n", Colors.DIM)
        )
    else:
        changed = sum(1 for s, d in operations if s != d)
        print(
            colorize(f"  ✅ Done! ", Colors.GREEN)
            + colorize(f"{changed} file(s) renamed.\n", Colors.BOLD)
        )


if __name__ == "__main__":
    main()
