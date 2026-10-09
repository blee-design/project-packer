# project-packer

**Pack an entire multi-file Python project into a single portable `.py` file — and unpack it anywhere.**

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Why?

Copying a whole project to share with someone (or an AI assistant) usually means
zipping folders, juggling `.gitignore` rules, and hoping nothing important is
missed. `project-packer` flattens the whole thing into **one self-describing
`.py` file** you can paste into a chat, email, or terminal.

- **Single file out** — no zip, no tar, no directory tree to reassemble.
- **Manifest-aware** — respects `MANIFEST.in` syntax, so it understands what's
  actually part of your Python package.
- **Setuptools-aware** — auto-detects project name and version from `setup.py`.
- **Zero dependencies** — stdlib only. Runs on any Python 3.8+.
- **Round-trippable** — `unpack` reconstructs the exact tree, folders and all.

---

## Installation

No install required. Just drop `packer.py` anywhere and run it.

```bash
curl -O https://raw.githubusercontent.com/blee-design/project-packer/main/packer.py
python packer.py --help
```

Or install as a console script:

```bash
pip install git+https://github.com/blee-design/project-packer.git
packer --help
```

---

## Quickstart

### Pack a project

```bash
cd my-project
python packer.py pack
```

Creates `my-project-1.2.0.py` containing every file the manifest declares.

### Unpack it

On any machine with Python 3.8+:

```bash
python packer.py unpack my-project-1.2.0.py
```

Recreates `my-project-1.2.0/` with the full original tree.

### Or skip packer.py entirely

The packed file is a valid Python file. Just paste its contents and the
recipient can unpack it with the same tool.

---

## CLI reference

### `pack`

```
python packer.py pack [root] [options]
```

| Arg | Default | Meaning |
|---|---|---|
| `root` | `.` | Project root. Must contain `setup.py` or `.git` (unless `--force`). |
| `-o, --output FILE` | `<name>-<version>.py` | Output filename. |
| `-v, --verbose` | off | Print every file decision with reasoning. |
| `-f, --force` | off | Pack even without `setup.py` / `.git`. |
| `--respect-gitignore` | off | Also apply `.gitignore` exclusions. |
| `--manifest FILE` | auto | Use a custom manifest file. |

### `unpack`

```
python packer.py unpack <packed_file> [target_dir] [options]
```

| Arg | Default | Meaning |
|---|---|---|
| `packed_file` | required | The `.py` file produced by `pack`. |
| `target_dir` | `<name>-<version>/` | Directory to recreate. Created if missing. |
| `-v, --verbose` | off | Print every file as it's written. |

---

## Manifest format

`project-packer` understands the standard `MANIFEST.in` directive set. It looks
for `packer.manifest` first, then falls back to `MANIFEST.in`. Override with
`--manifest FILE`.

### Supported directives

| Directive | Example | Meaning |
|---|---|---|
| `include` | `include README.md` | Add a specific file. |
| `exclude` | `exclude .env` | Remove a specific file. |
| `recursive-include` | `recursive-include templates *.html` | Add matching files under a directory. |
| `recursive-exclude` | `recursive-exclude tests *.py` | Remove matching files under a directory. |
| `graft` | `graft docs` | Add an entire directory. |
| `prune` | `prune build` | Remove an entire directory. |
| `global-include` | `global-include *.py` | Add matching files anywhere in the tree. |
| `global-exclude` | `global-exclude *.log` | Remove matching files anywhere. |

Lines starting with `#` are comments. See [`MANIFEST_Sample.in`](MANIFEST_Sample.in)
for a worked example.

### When there is no manifest

If neither `packer.manifest` nor `MANIFEST.in` exists, `packer` includes every
file that isn't matched by its [default ignore list](#default-ignores), plus a
handful of metadata files (`setup.py`, `README.md`, `LICENSE`, etc.) even if
they would normally be ignored.

---

## Default ignores

Some files are always skipped, even if a manifest says to include them:

```
__pycache__/  .git/  .venv/  venv/  .tox/  .eggs/
dist/  build/  *.egg-info/  *.egg/  *.cache/
.pytest_cache/  .mypy_cache/  .ruff_cache/
*.pyc  *.pyo  *.so  *.dll  *.exe  *.log  *.tmp
*.json  *.csv  *.txt.bak  *.pickle
cookies.txt  youtube_token.pickle  client_secrets.json  gallery-dl.conf
*.bak  *.backup  *~  .DS_Store  Thumbs.db
*.mp4  *.mkv  *.avi  *.mov  *.webm  *.tif  *.tiff
```

Rationale: keep secrets out, keep media out, keep build artifacts out.

To include a file that matches these patterns, rename it or remove the pattern
from `DEFAULT_IGNORE` in `packer.py`.

---

## `.gitignore` integration

By default `.gitignore` is **not** consulted — the manifest is the source of
truth. Pass `--respect-gitignore` to apply `.gitignore` exclusions on top of
whatever the manifest already included. Negated patterns (`!keep-me.txt`) are
honoured.

---

## Packed-file format

See [`docs/format.md`](docs/format.md) for the full specification. Short version:

```
# Project: my-project
# Version: 1.2.0
# Packed on: 2026-10-09 10:30:00
# Total files: 12
#======================================================================
# This file contains the complete source code.
# To unpack, use: python packer.py unpack <this_file>
#======================================================================

#---- FILE: setup.py ----
...contents...
#---- END FILE: setup.py ----

#---- FILE: my_pkg/core.py ----
...contents...
#---- END FILE: my_pkg/core.py ----
```

A third party could write a compatible unpacker in ~30 lines of any language.
See the spec for the exact rules.

---

## Use cases

- **Share code with an AI assistant** — one paste gives full context.
- **Ship a project to a machine with no git** — a USB stick and a Python
  interpreter is enough.
- **Code golf for file transfer** — smaller than the equivalent zip for
  text-heavy projects.
- **Self-contained releases** — commit the packed file alongside source.

---

## Limitations

- **Text only.** Binary files (`*.png`, `*.mp4`, `.so`, …) are recorded as a
  placeholder (`[Binary file: path - content not shown]`). They are *not*
  round-trippable.
- **No compression.** Files are concatenated as-is. For large projects, use
  `tar` + `xz`.
- **No integrity check.** A truncated packed file unpacks silently. If this
  matters, add your own hash.
- **`setup.py` parsing is AST-based, not executed.** Dynamic `version=` values
  (e.g., read from a file) are not resolved.

---

## License

MIT © Udaya Raj Joshi — see [LICENSE](LICENSE).
