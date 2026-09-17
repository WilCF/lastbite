#!/usr/bin/env python3
"""Structure-only check of a LastPass export. Never prints passwords or usernames.
Usage: python3 lastpass_diagnose.py ~/Downloads/lastpass_export.csv"""
import csv, sys
from collections import Counter
from pathlib import Path

DELIM_NAMES = {",": "COMMA", ";": "SEMICOLON", "\t": "TAB"}

src = Path(sys.argv[1]).expanduser()
raw = src.read_bytes()
text = raw.decode("utf-8-sig", errors="replace")
lines = text.splitlines()
header = lines[0]
print(f"File size: {len(raw):,} bytes | raw lines: {len(lines):,}")
crlf = raw.count(b"\r\n"); lf = raw.count(b"\n") - crlf; cr = raw.count(b"\r") - crlf
print(f"Line endings: CRLF={crlf}  LF-only={lf}  CR-only={cr}")
print(f"Header: {header!r}")
print(f"Header commas={header.count(',')} semicolons={header.count(';')} tabs={header.count(chr(9))}")
counts = {d: header.count(d) for d in DELIM_NAMES}
delim = max(counts, key=counts.get)
if counts[delim] == 0:
    delim = ","
print(f"Using delimiter: {DELIM_NAMES[delim]}")
print(f"Lines containing commas: {sum(1 for l in lines if ',' in l):,} | "
      f"semicolons: {sum(1 for l in lines if ';' in l):,} | "
      f"tabs: {sum(1 for l in lines if chr(9) in l):,}")

rows = list(csv.reader(text.splitlines(True), delimiter=delim))
hdr = [h.strip().lower() for h in rows[0]]
data = [r for r in rows[1:] if any(c.strip() for c in r)]
print(f"Parsed data rows: {len(data):,}")
print(f"Fields per row (expected {len(hdr)}): {dict(Counter(len(r) for r in data).most_common(8))}")

print("\nNon-empty count per column:")
for i, h in enumerate(hdr):
    print(f"  {h:10} {sum(1 for r in data if len(r) > i and r[i].strip()):,}")

if "url" in hdr:
    ui2 = hdr.index("url")
    sn = sum(1 for r in data if len(r) > ui2 and r[ui2].strip() == "http://sn")
    grp = sum(1 for r in data if len(r) > ui2 and r[ui2].strip() == "http://group")
    print(f"\nRows with url=='http://sn' (LastPass secure notes): {sn:,}")
    print(f"Rows with url=='http://group' (LastPass folder/group markers): {grp:,}")

def shape(v):
    v = v.strip()
    if not v: return "EMPTY"
    kind = "url-like" if "://" in v else ("has-dots" if "." in v and " " not in v else "text")
    return f"{len(v)}ch {kind}"

ui = hdr.index("url") if "url" in hdr else 0
ni = hdr.index("name") if "name" in hdr else None
bad = [r for r in data if len(r) <= ui or not r[ui].strip()][:6]
print("\nSample rows with EMPTY url (shapes only; 'name' shown as-is):")
for r in bad:
    cells = []
    for i, h in enumerate(hdr):
        v = r[i] if i < len(r) else "<missing>"
        cells.append(f"{h}={v[:40]!r}" if i == ni else f"{h}={shape(v)}")
    extra = f" +{len(r) - len(hdr)} extra fields" if len(r) > len(hdr) else ""
    print("  " + " | ".join(cells) + extra)
