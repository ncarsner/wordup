"""Parity check: verify lexicon.toml matches the source dict in __init__.py exactly."""
import ast
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = ROOT / "src" / "wordup" / "__init__.py"
TOML = ROOT / "src" / "wordup" / "data" / "lexicon.toml"

# --- parse source dict ---
text = SRC.read_text()
m = re.search(r"self\.replacements\s*=\s*(\{.*?\})\n\n", text, re.DOTALL)
if not m:
    sys.exit("ERROR: could not find replacements dict in __init__.py")
source: dict[str, list[str]] = ast.literal_eval(m.group(1))

# --- parse TOML ---
with TOML.open("rb") as fh:
    toml_data: dict[str, list[str]] = tomllib.load(fh)

# --- compare ---
errors: list[str] = []

if set(source) != set(toml_data):
    only_src = set(source) - set(toml_data)
    only_toml = set(toml_data) - set(source)
    if only_src:
        errors.append(f"Keys only in source: {sorted(only_src)}")
    if only_toml:
        errors.append(f"Keys only in TOML: {sorted(only_toml)}")

for key in source:
    if key in toml_data and source[key] != toml_data[key]:
        errors.append(f"Mismatch for {key!r}: source={source[key]!r}, toml={toml_data[key]!r}")

# --- counts ---
bases_src = len(source)
alts_src = sum(len(v) for v in source.values())
bases_toml = len(toml_data)
alts_toml = sum(len(v) for v in toml_data.values())

print(f"Source: {bases_src} base words, {alts_src} alternatives")
print(f"TOML:   {bases_toml} base words, {alts_toml} alternatives")

if bases_toml != 86:
    errors.append(f"Expected 86 base words, got {bases_toml}")
if alts_toml != 526:
    errors.append(f"Expected 526 alternatives, got {alts_toml}")

# --- special entries ---
specials = {
    "deal with": "address",
    "apply for": "request",
    "make known": "divulge",
    "before long": "soon",
    "clear-cut": "decisive",
}
for word, base in specials.items():
    if base in toml_data and word not in toml_data[base]:
        errors.append(f"Missing special entry {word!r} in {base!r}")
    elif base in toml_data:
        print(f"OK: {word!r} present in {base!r}")

if errors:
    for e in errors:
        print(f"FAIL: {e}", file=sys.stderr)
    sys.exit(1)

print("\nParity check PASSED -- TOML matches source dict exactly.")
