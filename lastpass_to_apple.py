#!/usr/bin/env python3
"""Convert a LastPass export (comma, semicolon, or tab separated) into Apple Passwords CSV.
Usage: python3 lastpass_to_apple.py ~/Downloads/lastpass_export.csv
Runs entirely on your Mac, never uploads anything. Delete all CSVs when finished.

Handles: exports missing the "totp" column (older exports, and lastpass-cli's
default export); semicolon-delimited exports (common after opening/re-saving in
Excel under decimal-comma locales); LastPass's Chrome-extension HTML-entity-
encoding of &, <, > (unescaped here for every field); secure notes
(url=="http://sn") and LastPass's internal folder/group markers
(url=="http://group"), both routed away from the login list; and blank/junk
rows LastPass sometimes exports with every field empty except "fav" (which is
always "0" or "1", so a naive "is this row blank" check that includes it wrongly
treats junk rows as real logins missing a username/URL).

Note: LastPass's standard CSV export does not include TOTP secrets for regular
password items (only its separate Authenticator app has its own export/transfer
flow) -- if every OTPAuth cell comes out empty, that's a LastPass export
limitation, not a bug here.
"""
import csv, html, sys, urllib.parse
from pathlib import Path

SECURE_NOTE_URL = "http://sn"
FOLDER_MARKER_URL = "http://group"
DELIM_NAMES = {",": "COMMA", ";": "SEMICOLON", "\t": "TAB"}

if len(sys.argv) != 2:
    sys.exit(f"Usage: python3 {Path(sys.argv[0]).name} <lastpass_export.csv>")

src = Path(sys.argv[1]).expanduser()
if not src.is_file():
    sys.exit(f"File not found: {src}")

out = src.with_name("apple_passwords_import.csv")
notes_out = src.with_name("lastpass_secure_notes_REVIEW.csv")
logins, notes = [], []
total_rows = blank_skipped = folder_skipped = 0

try:
    with open(src, newline="", encoding="utf-8-sig") as f:
        header = f.readline()
        counts = {d: header.count(d) for d in DELIM_NAMES}
        delim = max(counts, key=counts.get)
        if counts[delim] == 0:
            delim = ","
        f.seek(0)
        reader = csv.DictReader(f, delimiter=delim)
        reader.fieldnames = [h.strip().lower() for h in reader.fieldnames or []]
        missing = {"url", "username", "password", "name"} - set(reader.fieldnames)
        if missing:
            sys.exit(f"Unexpected header, missing {missing}. Header was: {reader.fieldnames}")
        print(f"Detected {DELIM_NAMES[delim]}-separated input")

        for r in reader:
            total_rows += 1
            r = {k: html.unescape((v or "").strip()) for k, v in r.items() if k}
            url = r.get("url", "")
            if url == FOLDER_MARKER_URL:
                folder_skipped += 1
                continue  # LastPass internal folder/group marker, not a real item
            content = {k: v for k, v in r.items() if k != "fav"}
            if not any(content.values()):
                blank_skipped += 1
                continue  # blank row ("fav" is always "0"/"1", never a real value)
            if url == SECURE_NOTE_URL:
                notes.append(r)
                continue
            if url and "://" not in url:
                url = "https://" + url
            title = r.get("name") or urllib.parse.urlparse(url).hostname or "Untitled"
            secret = r.get("totp", "").replace(" ", "")
            otp = (f"otpauth://totp/{urllib.parse.quote(title)}?secret={secret}"
                   f"&issuer={urllib.parse.quote(title)}") if secret else ""
            note = r.get("extra", "")
            if r.get("grouping"):
                note = f"[LastPass folder: {r['grouping']}]\n{note}".strip()
            logins.append({"Title": title, "URL": url, "Username": r.get("username", ""),
                           "Password": r.get("password", ""), "Notes": note, "OTPAuth": otp})
except UnicodeDecodeError:
    sys.exit(f"Could not read {src} as UTF-8. If you opened and re-saved this file in "
             f"Excel or another spreadsheet app, re-export it fresh from LastPass instead "
             f"-- re-saving can corrupt the encoding.")

fields = ["Title", "URL", "Username", "Password", "Notes", "OTPAuth"]
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL)
    w.writeheader()
    w.writerows(logins)

if notes:
    with open(notes_out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(notes[0].keys()), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(notes)

print(f"Input rows: {total_rows}")
if folder_skipped:
    print(f"LastPass folder markers skipped: {folder_skipped}")
if blank_skipped:
    print(f"Blank/junk rows skipped: {blank_skipped}")
print(f"Logins written: {len(logins)} -> {out}")
print(f"Secure notes (move manually): {len(notes)} -> {notes_out if notes else 'none'}")
print(f"With 2FA codes: {sum(1 for l in logins if l['OTPAuth'])}")
print(f"No username (normal for some sites): {sum(1 for l in logins if not l['Username'])}")
print(f"Missing URL (Apple may skip these): {sum(1 for l in logins if not l['URL'])}")
