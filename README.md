# 🍎 lastbite

*Take one last bite of LastPass before you go.*

Convert a LastPass CSV export into a CSV that Apple's **Passwords** app (macOS
Sequoia+) can import — with the row-level bugs that make the naive version of
this conversion fail silently already fixed.

Runs entirely on your Mac. Nothing is uploaded anywhere. Two plain-stdlib
Python scripts, no dependencies.

## The problem this solves

If you export your LastPass vault to CSV and either import it into Apple
Passwords directly, or run it through a very simple converter, you can end up
with hundreds or thousands of imported items that have **no username, no URL,
and a generic icon**. It looks like your data is missing. It usually isn't —
it's a parsing bug, not missing data. See [Known LastPass export quirks](#known-lastpass-export-quirks-this-handles)
below for exactly why this happens.

## Usage

```bash
python3 lastpass_to_apple.py ~/Downloads/lastpass_export.csv
```

This writes two files next to your input file, named after it (so converting
several exports — say, your own and a family member's — in the same folder
never overwrites one with the other):
- `<yourfile>_apple_import.csv` — import this into Apple Passwords (File >
  Import Passwords)
- `<yourfile>_secure_notes_REVIEW.csv` — LastPass secure notes, which Apple
  Passwords has no equivalent for. Review and move these manually; they are
  **not** included in the Apple import file.

If something looks off, run the diagnostic script first — it inspects the
file's structure (delimiter, column shapes, non-empty counts per column) and
**never prints passwords, usernames, TOTP secrets, or note contents**:

```bash
python3 lastpass_diagnose.py ~/Downloads/lastpass_export.csv
```

When you're done importing, delete the exported/converted CSV files — they
contain your passwords in plain text.

## Known LastPass export quirks this handles

- **Blank/junk rows counted as real logins.** LastPass exports can contain
  rows that are entirely empty except for the `fav` column (always `"0"` or
  `"1"`, never truly blank as a string). A naive "is this row blank?" check
  that includes `fav` treats thousands of junk rows as real logins missing a
  username and URL — this is very likely the #1 cause of the "no username,
  generic icon" symptom.
- **LastPass internal folder/group markers** (`url == "http://group"`) are
  skipped rather than imported as fake logins.
- **Secure notes** (`url == "http://sn"`) are routed to a separate review
  file instead of becoming broken logins with no username/password.
- **Delimiter auto-detection** covers comma, semicolon, and tab — not just
  comma/tab. Excel in decimal-comma locales (Germany, France, Spain, Italy,
  etc.) silently writes semicolons when you "Save As CSV," which is a common
  real-world cause of a LastPass export looking corrupted after being opened
  and re-saved.
- **Missing `totp` column tolerated.** Older LastPass exports, and
  `lastpass-cli`'s default export, use a 7-column format without `totp` at
  all. The script parses by header name, not fixed column position, so this
  just works.
- **HTML-entity corruption from the LastPass Chrome extension** (`&` exported
  as `&amp;`, etc.) is unescaped for every field, which also harmlessly
  no-ops on exports that don't have this bug (web vault / Firefox exports).
- **Multi-line secure notes** (e.g. structured note types like Server, SSH
  Key, Bank Account) are parsed with Python's `csv` module against an open
  file handle, so an embedded newline in a properly-quoted field doesn't
  corrupt the following rows.
- **Output filenames are derived from the input filename**, not hardcoded —
  converting a second export in the same folder (e.g. a family member's) can't
  silently overwrite the first one's output.
- Standard LastPass CSV export **does not include TOTP secrets** for regular
  password items (only LastPass's separate Authenticator app has its own
  export/transfer flow). If every `OTPAuth` cell comes out empty, that's a
  LastPass export limitation, not a bug here.

Apple has not published an official schema for the Passwords app's CSV
import. The `Title,URL,Username,Password,Notes,OTPAuth` header used here
matches Apple Passwords' own CSV *export* format and is the de facto standard
used by other independent converters — but Apple's exact behavior on edge
cases like an empty URL, or any hard row/file-size limit, isn't documented
anywhere I could confirm. If you're migrating a very large vault, consider
testing the import with a small slice of the output file first.

## Related tools

- [zenone/lastpass-to-apple-passwords](https://github.com/zenone/lastpass-to-apple-passwords) —
  the most established existing converter for this exact task (17+ stars).
  Simpler than this one, and every gap below was confirmed by actually
  running its code against synthetic test files, not just reading it — see
  [Comparison with zenone/lastpass-to-apple-passwords](#comparison-with-zenonelastpass-to-apple-passwords).
- [FrancisBehnen/pw-merge](https://github.com/FrancisBehnen/pw-merge) — a
  broader tool that merges Keychain, Dashlane, and LastPass exports into one
  Apple-format CSV with deduplication. Independently arrived at similar
  LastPass secure-note handling.

## Comparison with zenone/lastpass-to-apple-passwords

Confirmed by running [zenone's actual script](https://github.com/zenone/lastpass-to-apple-passwords/blob/main/lastpass_to_apple_passwords.py)
against synthetic (fake) test files — not just reading the source. Given this
input:

```csv
url,username,password,totp,extra,name,grouping,fav
https://example.com,fake_user1,FakePass123!,,,Example Site,Personal,0
,,,,,,,0
http://group,,,,,,,0
```

zenone's converter outputs:

```csv
Title,URL,Username,Password,Notes,OTPAuth
Example Site,https://example.com,fake_user1,FakePass123!,,
,,,,,
,http://group,,,,
```

Two of the three rows are garbage entries with no title, URL, username, or
password — the exact symptom this project exists to fix. Rather than just
pointing bugs out, I opened small single-purpose PRs upstream for this one
([#2](https://github.com/zenone/lastpass-to-apple-passwords/pull/2)), the
HTML-entity bug ([#3](https://github.com/zenone/lastpass-to-apple-passwords/pull/3)),
and the delimiter bug ([#4](https://github.com/zenone/lastpass-to-apple-passwords/pull/4)).
If they get merged, the gaps in the table below shrink — and if you're stuck
on zenone's tool in the meantime, those PRs contain the exact fixes.

| Bug (verified by running the code) | zenone | lastbite |
|---|---|---|
| Blank/junk rows written as broken logins | ❌ (PR [#2](https://github.com/zenone/lastpass-to-apple-passwords/pull/2) open) | ✅ filtered |
| LastPass folder markers (`url=="http://group"`) | ❌ written as a fake login | ✅ skipped |
| Secure notes (`url=="http://sn"`) | ❌ written as a broken login with no username/password | ✅ routed to a separate review file |
| Multi-line secure notes | ❌ embedded newlines silently stripped, lines run together (open [PR #1](https://github.com/zenone/lastpass-to-apple-passwords/pull/1) by another contributor) | ✅ preserved |
| Semicolon-delimited exports (common Excel re-save) | ❌ silently produces an empty/garbage file, no error (PR [#4](https://github.com/zenone/lastpass-to-apple-passwords/pull/4) open) | ✅ auto-detected |
| UTF-8 BOM (added by Excel's "CSV UTF-8" save) | ❌ first column silently lost — every URL comes out blank | ✅ handled |
| HTML-entity corruption from Chrome-extension exports (`&` → `&amp;`) | ❌ written literally into the password (PR [#3](https://github.com/zenone/lastpass-to-apple-passwords/pull/3) open) | ✅ unescaped |
| Exports missing the `totp` column | ✅ (doesn't read totp at all, so nothing breaks) | ✅ tolerated |
| TOTP → `otpauth://` conversion | ❌ always empty | ✅ when a secret is present |

This isn't a criticism of zenone's project — it's a small, single-purpose
script doing a genuinely fiddly job, and the PRs above are meant as real
contributions back to it, not just a pitch for this repo.

## License

MIT — see [LICENSE](LICENSE).
