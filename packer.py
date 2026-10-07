#!/usr/bin/env python3
"""
Universal Project Packer / Unpacker – Setuptools‑Aware (MANIFEST.in only)

Pack:
    python packer.py pack [root] [-o output] [-v] [--respect-gitignore] [--manifest FILE]

Unpack:
    python packer.py unpack <packed_file> [target_dir] [-v]
"""

import os
import sys
import ast
import time
import fnmatch
from pathlib import Path

# ---------- Default ignore patterns ----------
DEFAULT_IGNORE = {
    '__pycache__', '.git', '.venv', 'venv', '.tox', '.eggs', 'dist', 'build',
    '*.egg-info', '*.egg', '*.cache', '.pytest_cache', '.mypy_cache', '.ruff_cache',
    '*.pyc', '*.pyo', '*.so', '*.dll', '*.exe', '*.log', '*.tmp',
    '*.json', '*.csv', '*.txt.bak', '*.pickle', 'cookies.txt', 'youtube_token.pickle',
    'client_secrets.json', 'gallery-dl.conf',
    '*.bak', '*.backup', '*~', '.DS_Store', 'Thumbs.db',
    '*.mp4', '*.mkv', '*.avi', '*.mov', '*.webm', '*.tif', '*.tiff',
}

# ---------- MANIFEST.in parser (also used for packer.manifest) ----------
class ManifestParser:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.includes = set()          # exact patterns or (dir, pattern)
        self.excludes = set()
        self.global_includes = set()
        self.global_excludes = set()

    def parse(self, manifest_path):
        if not manifest_path.exists():
            return
        with open(manifest_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if not parts:
                    continue
                cmd = parts[0]
                args = parts[1:]
                self._process_directive(cmd, args)

    def _process_directive(self, cmd, args):
        if cmd == 'include':
            for pat in args:
                self.includes.add(pat)
        elif cmd == 'exclude':
            for pat in args:
                self.excludes.add(pat)
        elif cmd == 'recursive-include':
            if len(args) >= 2:
                dirname, pat = args[0], args[1]
                self.includes.add((dirname, pat))
        elif cmd == 'recursive-exclude':
            if len(args) >= 2:
                dirname, pat = args[0], args[1]
                self.excludes.add((dirname, pat))
        elif cmd == 'graft':
            for dirname in args:
                self.includes.add(dirname)
        elif cmd == 'prune':
            for dirname in args:
                self.excludes.add(dirname)
        elif cmd == 'global-include':
            for pat in args:
                self.global_includes.add(pat)
        elif cmd == 'global-exclude':
            for pat in args:
                self.global_excludes.add(pat)

    def matches_include(self, rel_path):
        # Global include
        for pat in self.global_includes:
            if fnmatch.fnmatch(rel_path, pat):
                return True
        # Explicit includes
        for item in self.includes:
            if isinstance(item, tuple):
                dirname, pat = item
                if rel_path.startswith(dirname) and fnmatch.fnmatch(rel_path, f"{dirname}/{pat}"):
                    return True
            else:
                # string pattern or directory name
                if '/' not in item and '.' not in item:
                    # directory (graft)
                    if rel_path.startswith(item):
                        return True
                else:
                    if fnmatch.fnmatch(rel_path, item):
                        return True
        return False

    def matches_exclude(self, rel_path):
        # Global exclude
        for pat in self.global_excludes:
            if fnmatch.fnmatch(rel_path, pat):
                return True
        # Explicit excludes
        for item in self.excludes:
            if isinstance(item, tuple):
                dirname, pat = item
                if rel_path.startswith(dirname) and fnmatch.fnmatch(rel_path, f"{dirname}/{pat}"):
                    return True
            else:
                if '/' not in item and '.' not in item:
                    # directory (prune)
                    if rel_path.startswith(item):
                        return True
                else:
                    if fnmatch.fnmatch(rel_path, item):
                        return True
        return False

# ---------- .gitignore parser ----------
def parse_gitignore(root):
    gitignore_path = Path(root) / '.gitignore'
    if not gitignore_path.exists():
        return [], []
    includes = []
    excludes = []
    with open(gitignore_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('!'):
                includes.append(line[1:])
            else:
                excludes.append(line)
    return includes, excludes

# ---------- setup.py parsing (minimal) ----------
def parse_setup_py(setup_path, verbose=False):
    if not setup_path.exists():
        if verbose:
            print("   ⚠️ setup.py not found.")
        return None, None, None, False, {}

    if verbose:
        print("🔍 Parsing setup.py")

    with open(setup_path, 'r', encoding='utf-8') as f:
        content = f.read()

    try:
        tree = ast.parse(content)
    except SyntaxError:
        if verbose:
            print("   ⚠️ Syntax error in setup.py")
        return None, None, None, False, {}

    name = version = None
    packages = None
    include_package_data = False
    entry_points = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == 'setup':
                for kw in node.keywords:
                    if kw.arg == 'name' and isinstance(kw.value, ast.Constant):
                        name = kw.value.value
                    elif kw.arg == 'version' and isinstance(kw.value, ast.Constant):
                        version = kw.value.value
                    elif kw.arg == 'packages':
                        if isinstance(kw.value, ast.List):
                            packages = [elt.value for elt in kw.value.elts if isinstance(elt, ast.Constant)]
                        elif isinstance(kw.value, ast.Call) and isinstance(kw.value.func, ast.Name) and kw.value.func.id == 'find_packages':
                            packages = None
                    elif kw.arg == 'include_package_data' and isinstance(kw.value, ast.Constant):
                        include_package_data = kw.value.value
                    elif kw.arg == 'entry_points' and isinstance(kw.value, ast.Dict):
                        for key, val in zip(kw.value.keys, kw.value.values):
                            if isinstance(key, ast.Constant) and key.value == 'console_scripts':
                                if isinstance(val, ast.List):
                                    for elt in val.elts:
                                        if isinstance(elt, ast.Constant):
                                            entry_points[elt.value] = True

    if verbose:
        print(f"   📦 Project name: {name or 'unknown'}, version: {version or 'unknown'}")
        if packages:
            print(f"   📂 Packages: {', '.join(packages)}")
        else:
            print("   📂 No explicit packages – using find_packages()")
        print(f"   📂 include_package_data: {include_package_data}")
        if entry_points:
            print(f"   📂 Entry points: {', '.join(entry_points.keys())}")
    return name, version, packages, include_package_data, entry_points

# ---------- File collection using manifest ----------
def is_ignored_by_default(rel_path):
    """Check if a file path matches default ignore patterns."""
    parts = rel_path.split(os.sep)
    for part in parts:
        if part in DEFAULT_IGNORE or any(fnmatch.fnmatch(part, pat) for pat in DEFAULT_IGNORE if '*' in pat):
            return True
    return False

def collect_files(root, verbose=False, respect_gitignore=False, manifest_file=None):
    root_path = Path(root).resolve()
    files = set()
    reasons = {}  # store reason for each file

    # Parse setup.py for metadata
    name, version, packages, include_package_data, entry_points = parse_setup_py(root_path / 'setup.py', verbose)

    # Determine which manifest to use
    if manifest_file is not None:
        manifest_path = Path(manifest_file)
        manifest_source = "custom"
    else:
        # Look for packer.manifest first, then MANIFEST.in
        packer_manifest = root_path / 'packer.manifest'
        if packer_manifest.exists():
            manifest_path = packer_manifest
            manifest_source = "packer.manifest"
        else:
            manifest_path = root_path / 'MANIFEST.in'
            manifest_source = "MANIFEST.in"

    manifest = ManifestParser(root_path)
    has_manifest = manifest_path.exists()
    if has_manifest:
        if verbose:
            print(f"📄 Parsing {manifest_source} ({manifest_path})")
        manifest.parse(manifest_path)
        if verbose:
            print(f"   ✅ Found {len(manifest.includes)} include rules, {len(manifest.excludes)} exclude rules")
    else:
        if verbose:
            print("⚠️  No manifest file found – will include all non‑ignored files.")

    # Step 1: If manifest exists, apply its rules
    if has_manifest:
        # Scan all files and apply include/exclude
        for item in root_path.rglob('*'):
            if item.is_file():
                rel = str(item.relative_to(root_path))
                # Skip if it matches an exclude rule
                if manifest.matches_exclude(rel):
                    if verbose:
                        print(f"      🚫 Excluded (manifest): {rel}")
                    continue
                # Check if it matches any include rule
                if manifest.matches_include(rel):
                    if not is_ignored_by_default(rel):
                        files.add(rel)
                        reasons[rel] = "manifest include"
                        if verbose:
                            print(f"      ✅ Include (manifest): {rel}")
                    else:
                        if verbose:
                            print(f"      ⏭️  Skipped (default ignore): {rel}")
                else:
                    if verbose:
                        print(f"      ⏭️  Not included (no manifest rule): {rel}")

        # Add metadata files that are not excluded and not already added
        for meta in ['setup.py', 'README.md', 'README.rst', 'README.txt', 'LICENSE', 'MANIFEST.in', 'packer.manifest']:
            if (root_path / meta).exists():
                rel = meta
                if rel not in files and not manifest.matches_exclude(rel):
                    if not is_ignored_by_default(rel):
                        files.add(rel)
                        reasons[rel] = "metadata (default)"
                        if verbose:
                            print(f"      ✅ Include (metadata): {rel}")
    else:
        # No manifest: include all non-ignored files
        if verbose:
            print("📂 Including all non‑ignored files (no manifest)")
        for item in root_path.rglob('*'):
            if item.is_file():
                rel = str(item.relative_to(root_path))
                if not is_ignored_by_default(rel):
                    files.add(rel)
                    reasons[rel] = "all files (fallback)"
                    if verbose:
                        print(f"      ✅ Include (fallback): {rel}")
                else:
                    if verbose:
                        print(f"      ⏭️  Skipped (default ignore): {rel}")

        # Add metadata even if they were ignored by default (e.g., setup.py)
        for meta in ['setup.py', 'README.md', 'README.rst', 'README.txt', 'LICENSE', 'MANIFEST.in', 'packer.manifest']:
            if (root_path / meta).exists():
                if meta not in files:
                    files.add(meta)
                    reasons[meta] = "metadata (forced)"
                    if verbose:
                        print(f"      ✅ Include (metadata): {meta}")

    # Apply .gitignore exclusions if requested
    if respect_gitignore:
        if verbose:
            print("📂 Applying .gitignore rules")
        git_includes, git_excludes = parse_gitignore(root_path)
        for f in list(files):
            excluded = False
            for pat in git_excludes:
                if fnmatch.fnmatch(f, pat):
                    excluded = True
                    break
            if excluded:
                # Check if it's re-included by ! patterns
                for inc_pat in git_includes:
                    if fnmatch.fnmatch(f, inc_pat):
                        excluded = False
                        break
                if excluded:
                    files.remove(f)
                    if verbose:
                        print(f"      🚫 Excluded (.gitignore): {f}")

    if verbose:
        print(f"\n📊 Total files collected: {len(files)}")
        # Optionally list all with reasons
        if len(files) <= 50:
            for f in sorted(files):
                print(f"   • {f} ({reasons.get(f, 'unknown')})")
        else:
            print(f"   (First 10 files shown)")
            for f in sorted(files)[:10]:
                print(f"   • {f} ({reasons.get(f, 'unknown')})")
            print(f"   ... and {len(files)-10} more")

    return sorted(files)

# ---------- Pack ----------
def pack_project(root, output_file=None, verbose=False, force=False, respect_gitignore=False, manifest_file=None):
    root = Path(root).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory")
        sys.exit(1)

    if not (root / 'setup.py').exists() and not (root / '.git').exists():
        if force:
            print("⚠️  --force: continuing without setup.py or .git")
        else:
            print("❌ Not a Python project root (no setup.py or .git).")
            print("   Use --force to override this check.")
            sys.exit(1)

    if verbose:
        print(f"\n📦 Packing project from: {root}")

    name, version, _, _, _ = parse_setup_py(root / 'setup.py', verbose)
    if not name:
        name = root.name
        if verbose:
            print(f"   ℹ️ Using directory name as project name: {name}")
    if not version:
        version = 'unknown'

    if output_file is None:
        if version and version != 'unknown':
            output_file = f"{name}-{version}.py"
        else:
            output_file = f"{name}.py"
    if verbose:
        print(f"📄 Output file: {output_file}")

    files = collect_files(str(root), verbose, respect_gitignore, manifest_file)

    with open(output_file, 'w', encoding='utf-8') as out:
        out.write(f"# Project: {name}\n")
        out.write(f"# Version: {version}\n")
        out.write(f"# Packed on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        out.write(f"# Total files: {len(files)}\n")
        out.write("#" + "=" * 70 + "\n")
        out.write("# This file contains the complete source code.\n")
        out.write("# To unpack, use: python packer.py unpack <this_file>\n")
        out.write("#" + "=" * 70 + "\n\n")

        written = 0
        for rel_path in files:
            full_path = root / rel_path
            if not full_path.exists():
                if verbose:
                    print(f"   ⚠️ File missing: {rel_path} (skipping)")
                continue
            if verbose:
                print(f"   📄 Writing: {rel_path}")
            out.write(f"#---- FILE: {rel_path} ----\n")
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                out.write(content)
            except UnicodeDecodeError:
                out.write(f"[Binary file: {rel_path} - content not shown]\n")
                if verbose:
                    print(f"      ⚠️ Binary file – content skipped")
            if not content.endswith('\n'):
                out.write('\n')
            out.write(f"#---- END FILE: {rel_path} ----\n\n")
            written += 1

    print(f"✅ Packed {written} files into {output_file}")

# ---------- Unpack (unchanged) ----------
def unpack_project(packed_file, target_dir=None, verbose=False):
    if not os.path.exists(packed_file):
        print(f"Error: {packed_file} not found")
        sys.exit(1)

    name = None
    version = None
    try:
        with open(packed_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('# Project: '):
                    name = line[len('# Project: '):].strip()
                elif line.startswith('# Version: '):
                    version = line[len('# Version: '):].strip()
                if name and version:
                    break
    except:
        pass

    if target_dir is None:
        if name and version:
            target_dir = f"{name}-{version}"
        else:
            base = os.path.splitext(os.path.basename(packed_file))[0]
            target_dir = base + "_unpacked"
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"📂 Unpacking to: {target_dir}")

    with open(packed_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_file = None
    content_lines = []
    file_count = 0

    for line in lines:
        if line.startswith('#---- FILE: '):
            if current_file is not None:
                write_file(target / current_file, ''.join(content_lines), verbose)
                file_count += 1
                content_lines = []
            raw = line[len('#---- FILE: '):].strip()
            if raw.endswith('----'):
                raw = raw[:-4].rstrip()
            current_file = raw
            if verbose:
                print(f"   📄 Creating: {current_file}")
            continue
        elif line.startswith('#---- END FILE: '):
            if current_file is not None:
                write_file(target / current_file, ''.join(content_lines), verbose)
                file_count += 1
                current_file = None
                content_lines = []
            continue
        if current_file is not None:
            content_lines.append(line)

    if current_file is not None and content_lines:
        write_file(target / current_file, ''.join(content_lines), verbose)
        file_count += 1

    print(f"✅ Unpacked {file_count} files into {target_dir}")

def write_file(path, content, verbose=False):
    parent = path.parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', errors='ignore') as f:
        f.write(content)

# ---------- CLI ----------
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Pack or unpack a Python project.')
    subparsers = parser.add_subparsers(dest='command', required=True)

    pack_parser = subparsers.add_parser('pack', help='Pack project')
    pack_parser.add_argument('root', nargs='?', default='.', help='Project root (must contain setup.py or .git)')
    pack_parser.add_argument('-o', '--output', help='Output file name (default: <project_name>-<version>.py)')
    pack_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    pack_parser.add_argument('-f', '--force', action='store_true', help='Force packing even without setup.py/.git')
    pack_parser.add_argument('--respect-gitignore', action='store_true', help='Also apply .gitignore exclusions')
    pack_parser.add_argument('--manifest', help='Custom manifest file (default: packer.manifest, then MANIFEST.in)')

    unpack_parser = subparsers.add_parser('unpack', help='Unpack a packed file')
    unpack_parser.add_argument('packed_file', help='Packed file to unpack')
    unpack_parser.add_argument('target', nargs='?', help='Target directory (default: <name>-<version> if available, else <base>_unpacked)')
    unpack_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    if args.command == 'pack':
        pack_project(args.root, args.output, args.verbose, args.force, args.respect_gitignore, args.manifest)
    elif args.command == 'unpack':
        unpack_project(args.packed_file, args.target, args.verbose)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
