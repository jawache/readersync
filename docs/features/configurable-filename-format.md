# Feature Spec: Configurable Filename Format

**Status:** Planned
**Created:** 2026-02-08
**Last Updated:** 2026-02-08

## Overview

Allow users to configure the filename format for synced documents, while keeping the Readwise reader ID as a mandatory component.

## Problem Statement

The current filename format is hardcoded as `YYYYMMDD-sanitized-title-READERID.md`. This works well for chronological sorting, but not all users want the date prefix. Some prefer just the title for a cleaner vault sidebar, others may want a different date format or ordering.

However, the Readwise reader ID **must** remain in the filename. It serves two purposes:
1. **Uniqueness** - prevents clashes between documents with similar titles
2. **Mapping** - allows readersync to find and update existing files without scanning frontmatter

## Solution

Add a `--filename-format` CLI option (and config file support) that accepts a template string with placeholders. The `{id}` placeholder is always required.

### Available Placeholders

| Placeholder | Description | Example |
|---|---|---|
| `{date}` | Date from `saved_at` in `YYYYMMDD` format | `20241124` |
| `{title}` | Sanitised, truncated title | `climate-change-computing-responsibility` |
| `{id}` | Readwise reader ID (mandatory) | `01kavd87rsgpqbbjqmwzz4yhtm` |

### Example Formats

```
{date}-{title}-{id}     # current default: 20241124-climate-change-computing-01kavd87rsg.md
{title}-{id}             # no date prefix: climate-change-computing-01kavd87rsg.md
{id}-{title}             # ID first: 01kavd87rsg-climate-change-computing.md
{date}-{id}-{title}      # date then ID: 20241124-01kavd87rsg-climate-change-computing.md
```

### Validation Rules

- The format string **must** contain `{id}` - reject with a clear error if missing
- The format string must contain at least one other placeholder (a filename of just an ID is unhelpful)
- Unknown placeholders are rejected

## Design Decisions

### Why the ID is mandatory

Users can rename any part of the filename except the ID. If they change or remove the ID, readersync simply won't recognise the file on the next sync - it will download a fresh copy. This is acceptable behaviour and doesn't need special handling.

### Why not move the ID to a separate index file?

We considered storing the ID-to-filename mapping in a JSON index (e.g. `.readersync/index.json`). This was rejected because:
- Obsidian users frequently rename files, which would break the index
- The alternative (scanning all frontmatter for `readwise_id`) is slow on large vaults
- A glob for `*-READERID*` is fast and reliable
- The ID in the filename is honest - the file came from Readwise, and the source is traceable

### File discovery with configurable formats

The current code uses `extract_readwise_id_from_filename()` which assumes the ID is the last segment. With configurable formats, file discovery should instead glob for `*{id}*` - the ID is unique enough that a substring match will always find exactly one file regardless of where it sits in the filename.

## Implementation Plan

1. **Add `--filename-format` option to CLI** (`cli.py`)
   - Default: `{date}-{title}-{id}`
   - Validate that `{id}` is present
   - Pass format string through to sync manager

2. **Update `generate_filename()` in `utils.py`**
   - Accept a format template parameter
   - Replace placeholders with actual values
   - Keep existing sanitisation logic for the title

3. **Update file discovery in `sync_manager.py`**
   - When checking for existing files, glob for `*{readwise_id}*` instead of relying on filename position
   - This works regardless of the configured format

4. **Store format in config**
   - Consider a `.readersync.conf` or similar config file in the output folder
   - Allows the format to persist without passing it on every invocation
   - CLI flag overrides config file

5. **Update tests**
   - Test filename generation with various format strings
   - Test validation rejects formats without `{id}`
   - Test file discovery with different filename patterns
