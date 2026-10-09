# Packed file format

The `.py` file produced by `project-packer pack` is a plain-text
container. It is a valid Python file (it parses), but you should not
import it — run it through `packer unpack` instead.

## Structure

```
# Project: <name>
# Version: <version>
# Packed on: <YYYY-MM-DD HH:MM:SS>
# Total files: <n>
#======================================================================
# This file contains the complete source code.
# To unpack, use: python packer.py unpack <this_file>
#======================================================================

#---- FILE: <relative/path/to/file> ----
<raw file contents>
#---- END FILE: <relative/path/to/file> ----

#---- FILE: <relative/path/to/file2> ----
<raw file contents>
#---- END FILE: <relative/path/to/file2> ----
```

## Rules

1. **Header.** Every line before the first `#---- FILE:` is metadata. Lines
   starting with `# Project:`, `# Version:`, `# Packed on:`, and
   `# Total files:` are consumed by the unpacker. Other header lines are
   ignored.

2. **Delimiters.** Each embedded file is bracketed by two lines:

   ```
   #---- FILE: <path> ----
   ...
   #---- END FILE: <path> ----
   ```

   The path after `#---- FILE: ` is relative to the project root and uses
   forward slashes on all platforms. The trailing ` ----` is stripped by the
   unpacker.

3. **Content.** Everything between the delimiters is written verbatim. If a
   file's contents don't end with a newline, one is appended so the next
   `#---- END FILE:` marker starts on its own line.

4. **Binary files.** Non-UTF-8 files are replaced with a single line:

   ```
   [Binary file: <path> - content not shown]
   ```

   This placeholder is written into the target file on unpack — it is **not**
   the original bytes.

5. **Line endings.** Packed files use `\n` throughout. Windows clients will
   see them converted by git or their editor on checkout.

## Writing a compatible unpacker

Minimal Python:

```python
import re
from pathlib import Path

src = Path("my-project-1.2.0.py")
dst = Path("my-project-1.2.0")
dst.mkdir(exist_ok=True)

current = None
buf = []

for line in src.read_text(encoding="utf-8").splitlines(keepends=True):
    m = re.match(r"^#---- FILE: (.+?)(?: ----)?$", line)
    if m:
        current = m.group(1)
        buf = []
        continue
    if line.startswith("#---- END FILE: "):
        if current:
            out = dst / current
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text("".join(buf), encoding="utf-8")
        current = None
        continue
    if current is not None:
        buf.append(line)
```

That's the entire contract.

## Versioning

The format itself is versioned implicitly by the header — no version number is
stored. Future revisions will add a `# Format: 2` line at the top; unpackers
should treat its absence as format 1.
