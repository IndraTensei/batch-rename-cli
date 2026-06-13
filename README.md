<div align="center">

# 📦 batch-rename

**Powerful batch file renaming made simple.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![PyPI](https://img.shields.io/badge/pypi-batch--rename-orange.svg)](#installation)

Rename hundreds of files with a single command — safely, beautifully, and with full undo support.

[Features](#-features) • [Installation](#-installation) • [Quick Start](#-quick-start) • [Usage](#-usage) • [Examples](#-examples)

</div>

---

## ✨ Why batch-rename?

You've been there: 300 vacation photos named `IMG_20240115_123456.jpg`, a folder of documents with inconsistent naming, or a music collection that needs a uniform format. Writing shell scripts or renaming by hand is tedious and error-prone.

**batch-rename** gives you a single, safe, and intuitive tool for all your file renaming needs:

- 🛡️ **Dry-run first** — preview every change before it happens
- ↩️ **Full undo** — every rename is journaled; undo with one command
- 🎨 **Beautiful terminal UI** — colored previews, progress, and clear feedback
- 🔍 **Regex support** — powerful pattern matching with capture groups
- 📋 **Numbering, dates, prefix/suffix** — all the common transforms built in
- 🐍 **Zero dependencies** — pure Python, no pip install needed to run

---

## 🚀 Quick Start

```bash
# Clone and run
git clone https://github.com/IndraTensei/batch-rename-cli.git
cd batch-rename-cli
python src/batch_rename.py *.txt --find "old" --replace "new"

# That's it. Preview, rename, undo. Done.
```

---

## 📦 Installation

### From source (recommended)
```bash
git clone https://github.com/IndraTensei/batch-rename-cli.git
cd batch-rename-cli
pip install -e .
```

### Standalone (no install)
```bash
# Just copy src/batch_rename.py anywhere and run it directly
python batch_rename.py --help
```

### Via pip (once published)
```bash
pip install batch-rename
batch-rename *.jpg --prefix "vacation_" --numbering
```

**Requirements:** Python 3.10+ (no external dependencies)

---

## 🎯 Features

| Feature | Description |
|---------|-------------|
| 🔍 **Find & Replace** | Literal text replacement in filenames |
| 🔬 **Regex** | Full regex with capture group support (`\1`, `\2`, etc.) |
| 📝 **Prefix / Suffix** | Add text before or after the filename stem |
| 🔢 **Sequential Numbering** | Add zero-padded numbers with configurable start/padding |
| 📅 **Date Insertion** | Append dates in any `strftime` format |
| 🔠 **Case Transforms** | `lower`, `upper`, `title`, `snake_case`, `kebab-case`, `camelCase`, `PascalCase` |
| 📎 **Extension Control** | Change extensions or strip them entirely |
| 🛡️ **Dry Run** | Preview all changes before applying |
| ↩️ **Undo** | Full undo via journal files |
| 📂 **Recursive** | Process entire directory trees |
| 🎯 **Filter** | By extension, exclude patterns |
| 📊 **Sort** | By name, date, size, or preserve original order |
| 🎨 **Colored Output** | Beautiful terminal UI with color-coded previews |

---

## 📖 Usage

```
batch-rename [OPTIONS] [PATHS...]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `paths` | Files or directories to process |

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--find TEXT` | `-f` | Text to find in filenames |
| `--replace TEXT` | `-r` | Replacement text |
| `--regex-find PATTERN` | | Regex pattern to find |
| `--regex-replace PATTERN` | | Regex replacement (supports `\1`, `\2`) |
| `--prefix TEXT` | `-p` | Add prefix to filenames |
| `--suffix TEXT` | `-s` | Add suffix (before extension) |
| `--case CASE` | `-c` | Case: `lower`, `upper`, `title`, `snake`, `kebab`, `camel`, `pascal` |
| `--numbering` | `-n` | Add sequential numbering |
| `--number-start N` | | Starting number (default: 1) |
| `--number-pad N` | | Number padding width (default: 2) |
| `--date FORMAT` | `-d` | Append date (strftime format) |
| `--new-ext EXT` | | Change file extension |
| `--trim-ext` | | Remove file extensions |
| `--recursive` | `-R` | Process directories recursively |
| `--include-dirs` | | Also rename directories |
| `--extensions EXT [EXT...]` | `-e` | Only process these extensions |
| `--exclude PAT [PAT...]` | `-x` | Exclude matching patterns |
| `--sort ORDER` | | Sort: `name`, `date`, `size`, `none` |
| `--dry-run` | | Preview without renaming |
| `--force` | | Overwrite existing files |
| `--undo` | | Undo the last rename operation |
| `--journals` | | List all undo journals |
| `--no-color` | | Disable colored output |
| `--version` | `-v` | Show version |
| `--help` | `-h` | Show help message |

---

## 💡 Examples

### Basic find & replace
```bash
# Replace "old" with "new" in all .txt files
batch-rename *.txt --find "old" --replace "new"

# Before: report_old_draft.txt → After: report_new_draft.txt
```

### Add prefix and sequential numbering
```bash
# Rename all photos with a prefix and zero-padded numbers
batch-rename photos/ --prefix "vacation_" --numbering --number-pad 3

# Before: DSC_001.jpg → After: vacation_DSC_001_001.jpg
# Before: DSC_002.jpg → After: vacation_DSC_002_002.jpg
```

### Case conversion
```bash
# Convert all filenames to snake_case
batch-rename docs/ --case snake

# Before: My Document File.txt → After: my_document_file.txt
```

### Regex with capture groups
```bash
# Extract date from photo filenames
batch-rename *.jpg --regex-find "IMG_(\d{4})(\d{2})(\d{2})_.*" --regex-replace "\1-\2-\3"

# Before: IMG_20240115_123456.jpg → After: 2024-01-15.jpg
```

### Change extensions
```bash
# Convert all .jpeg to .jpg
batch-rename photos/ --recursive --extensions jpeg --new-ext jpg
```

### Add date stamp
```bash
# Append today's date to all files
batch-rename reports/ --date "%Y-%m-%d"

# Before: sales.csv → After: sales_2024-06-13.csv
```

### Recursive with filters
```bash
# Rename all .py files in a project, excluding __pycache__
batch-rename src/ --recursive --extensions py --exclude "__pycache__*" --case snake
```

### Dry run (always try first!)
```bash
# Preview changes before applying
batch-rename *.txt --find "draft" --replace "final" --dry-run
```

### Undo
```bash
# Made a mistake? Undo the last rename operation
batch-rename --undo

# See all available undo journals
batch-rename --journals
```

### Complex example
```bash
# Combine multiple transforms
batch-rename photos/ \
  --prefix "trip_" \
  --numbering \
  --number-start 1 \
  --number-pad 4 \
  --case lower \
  --date "%Y%m%d" \
  --sort date

# Before: Beach Photo (3).JPG
# After:  trip_beach photo (3)_0001_20240613.jpg
```

---

## 🛡️ Safety Features

### Dry Run Mode
Always preview your changes first:
```bash
batch-rename * --case lower --dry-run
```
Shows exactly what will change — no files are touched.

### Undo Journal
Every rename operation is automatically saved to a journal file at `~/.batch-rename-journals/`. One command to undo:
```bash
batch-rename --undo
```

### Conflict Detection
batch-rename detects when two files would end up with the same name and warns you before proceeding.

---

## 🧪 Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. Fork the repository
2. Create a feature branch: `git checkout -b my-feature`
3. Make your changes and add tests
4. Run the test suite: `python -m pytest tests/ -v`
5. Commit and push: `git commit -m "Add my feature" && git push`
6. Open a Pull Request

Please ensure:
- All tests pass
- New features include tests
- Code follows the existing style (PEP 8)

---

## 📄 License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).

---

<div align="center">

Made with ❤️ by [IndraTensei](https://github.com/IndraTensei)

⭐ Star this repo if you find it useful!

</div>
