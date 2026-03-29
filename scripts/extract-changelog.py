#!/usr/bin/env python3
"""Extract release notes for a given version from CHANGELOG.md.

Usage: python3 extract-changelog.py <version>
Prints the body of the matching ## [version] section to stdout.
"""
import re
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: extract-changelog.py <version>", file=sys.stderr)
    sys.exit(1)

version = sys.argv[1].lstrip("v")
content = Path("CHANGELOG.md").read_text()

pattern = rf"## \[{re.escape(version)}\][^\n]*\n(.*?)(?=\n## \[|\Z)"
match = re.search(pattern, content, re.DOTALL)

if match:
    print(match.group(1).strip())
else:
    print(f"Release {version}", file=sys.stderr)
    sys.exit(1)
