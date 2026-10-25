# gbsdconv

A GUI for the [bsdconv](https://github.com/buganini/bsdconv) encoding converter,
written with [PUI](https://github.com/buganini/PUI) and its PySide6 backend.

## Features

- **Multi-conversions:** evaluate multiple conversion candidates and select the
  best result using configurable error and language scores.
- **Text conversion:** convert pasted text, preview the result, and copy or save
  the output.
- **Text file conversion:** convert file contents in batches with streaming and
  optional backups.
- **File path conversion:** preview and rename files and folders, including
  selected symlink targets.
- **Multimedia metadata conversion:** preview and convert media tags through
  the optional TagLib bridge.
- **Conversion helpers:** regional profiles, codec chains, URL decoding, and
  mojibake repair.

## Requirements

- Python 3.10–3.14 and a platform supported by PySide6. Python 2 is not supported.
- A PUI checkout containing `TextEdit`, with the `PySide6` extra.
  Until that API is released, install the updated sibling `PUI` checkout.
- libbsdconv and the `bsdconv` Python binding, version 11.7.0 or newer.
- Optional: TagLib 2.x development headers, library and a C++17 compiler for
  media tag conversion. Other pages work without the TagLib bridge.

The current rewrite is tested on macOS arm64 with Python 3.14, PySide6 6.12
and TagLib 2.3. Linux and Windows still need platform testing.

## Install and run

On macOS, install the native dependencies with Homebrew:

```sh
brew install bsdconv taglib
python3 -m venv env
source env/bin/activate
python -m pip install -e "../PUI[PySide6]"
python -m pip install .
gbsdconv
```

Homebrew prefixes are detected automatically, including `/opt/homebrew` on
Apple Silicon. On other systems, install libbsdconv and TagLib 2.x development
packages using your package manager, then use the same virtual environment and
pip commands. Source builds require a compiler.

If `bsdconv` 11.7.0 is not yet available from your package index, install the
updated sibling checkout before installing gbsdconv:

```sh
python -m pip install ../python-bsdconv
python -m pip install .
```

For custom native library locations, set `BSDCONV_PREFIX` when building the
Python binding and `TAGLIB_PREFIX` when building gbsdconv. The corresponding
shared libraries must also be available to the system loader at runtime.

The TagLib bridge is optional at build time. If you installed gbsdconv before
TagLib, rebuild it after installing TagLib:

```sh
python -m pip install --force-reinstall --no-deps --no-cache-dir .
```

Run `gbsdconv [file-or-folder ...]`, or use `python gbsdconv` from this checkout.

## Using the interface

The **Setup** tab comes first. Its **Conversion type** menu defaults to
**Text**, showing only the Setup and Text tabs. Select **File Names**,
**File Contents**, or **Media Tags** to show **Select Files** and the matching
operation tab instead. Switching types preserves entered text and file selections.

The conversion expression at the top applies to all conversion pages. Use the
**Setup** page to choose a regional profile, build a codec chain, adjust
scoring weights, or construct URL decoding and mojibake repair expressions.
Semicolon-separated candidates are evaluated automatically; `:SCORE:` enables
language scoring. Filename training uses temporary score data.

- **Text:** convert pasted UTF-8 text, copy the preview, or save the exact output
  bytes. Set the preview encoding when the output is not UTF-8.
- **Select Files:** add files or recursively collect a folder, select by type or glob,
  and choose the focused file. Removing an item only removes it from the list.
- **File Names:** preview selected names and symlink targets, then apply the
  preview. Children are renamed before parent folders. Existing destinations,
  conversion errors and changed files prevent application.
- **File Contents:** preview the focused file or convert selected files. The
  preview is limited to 1 MiB; conversion streams the complete file. The default
  filter includes only text file extensions.
- **Media Tags:** preview and convert selected title, artist, album, comment and
  genre fields. Year and track are preserved. Latin-1 mojibake recovery,
  comment clearing and MP3 ID3 options are available. Output must be UTF-8.

Content and tag conversions work on temporary copies and replace each original
only after successful conversion. Backups are enabled by default and named
`filename.bsdconv.bak`; existing backups are never overwritten. Symlinks are
excluded from content and tag writes. Batch processing reports individual
failures and continues with the remaining files.

Only symlinks included in a filename preview have their targets adjusted.
Links outside the selection may need updating after a rename. File writes are
atomic per file; a whole batch is not a single transaction.

## Development

```sh
python -m pip install -e .
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
```

Tests exercise real bsdconv conversions, streaming across multibyte boundaries,
backup protection, nested renames, stale previews, TagLib WAV round trips and
native Qt controls. Media tests are skipped if the optional bridge is absent.
The UI uses PUI state, declarative subviews and its shared `TextEdit`
component for multiline editing. Conversion work runs on one
background worker and returns results to the Qt event loop.
