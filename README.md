# readersync

A Python CLI tool to sync your Readwise Reader documents to local markdown files for use with Obsidian and other markdown-based tools.

## Features

- **Incremental sync** - Only fetches documents updated since last sync
- **Full content extraction** - Downloads PDFs and converts web articles to clean markdown
- **Highlights integration** - Automatically groups highlights with their parent documents
- **Obsidian-friendly** - Generates markdown files with YAML frontmatter
- **Chronological organisation** - Filenames include dates for easy sorting
- **Configurable filenames** - Customise the filename format with `{date}`, `{title}`, `{id}` placeholders
- **Location filtering** - Sync only documents from specific locations (new, later, archive, etc.)
- **Smart conversion** - Uses Microsoft's MarkItDown to convert HTML and PDFs to clean markdown

## How It Works

The tool connects to the Readwise Reader API to:
1. Fetch all documents (articles, PDFs, etc.) updated since the last sync
2. Download PDFs and extract their content
3. Convert web articles from HTML to markdown
4. Group highlights with their parent documents
5. Generate markdown files with metadata and content

### File Naming Convention

Files are named for chronological sorting and unique identification:

```
YYYYMMDD-sanitized-title-READERID.md
YYYYMMDD-sanitized-title-READERID.pdf  (for PDFs)
```

Example:
```
20241124-climate-change-computing-responsibility-01kavd87rsgpqbbjqmwzz4yhtm.md
20241124-climate-change-computing-responsibility-01kavd87rsgpqbbjqmwzz4yhtm.pdf
```

- **Date**: When you saved the document to Reader (`saved_at` timestamp)
- **Title**: Sanitized and truncated to 50-60 characters
- **ID**: Readwise Reader document ID (ensures uniqueness)

### Markdown File Format

Each markdown file includes:

```markdown
---
readwise_id: 01kavd87rsgpqbbjqmwzz4yhtm
title: "Climate Change: What Is Computing's Responsibility?"
author: "Author Name"
url: "https://read.readwise.io/read/..."
source_url: "https://original-source.com/article"
category: pdf
location: new
tags:
  - sustainability
  - computing
site_name: "dagstuhl.de"
word_count: 7795
reading_progress: 1.0
cover: "https://..."
date: "2025-11-24"
created_at: "2025-11-24T17:05:46"
saved_at: "2025-11-24T17:05:46"
updated_at: "2025-11-24T22:56:05"
summary: "Brief summary of the document..."
---

> [!highlight] My thoughts on this highlight
> First highlight text here
>
> ✏️ 2025-11-24 | 🔗 [View in Readwise](https://read.readwise.io/read/...)

> [!highlight]
> Second highlight text
>
> ✏️ 2025-11-24 | 🔗 [View in Readwise](https://read.readwise.io/read/...)

---

[Full article content converted to clean markdown]
```

## Installation

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Setup

**Recommended: Using uv (fast, automatic virtual environment)**

[uv](https://github.com/astral-sh/uv) is a modern Python package manager (like pnpm/bun for Node). It's much faster and handles virtual environments automatically.

1. Install uv if you don't have it:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone or download this repository:
```bash
cd /path/to/readwise
```

3. Install the tool with uv:
```bash
uv pip install -e .
```

uv automatically creates and manages a virtual environment, keeping everything isolated.

**Alternative: Using pip + venv**

1. Clone or download this repository:
```bash
cd /path/to/readwise
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the tool:
```bash
pip install -e .
```

**Get your Readwise access token:**
- Visit: https://readwise.io/access_token
- Copy your access token

**Setup environment variables (recommended):**

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your token:

```
READWISE_TOKEN=your_actual_token_here
```

The `.env` file is gitignored so your token stays private.

## Usage

If you used uv, you can run commands directly. If you used pip+venv, make sure your virtual environment is activated first (`source venv/bin/activate`).

### Basic Sync

With `.env` file (recommended):

```bash
readersync
```

Or pass token directly:

```bash
readersync --token YOUR_TOKEN
```

Or use environment variable:

```bash
export READWISE_TOKEN=YOUR_TOKEN
readersync
```

Specify a different folder:

```bash
readersync --folder ./my-obsidian-vault
```

### Full Re-sync

Ignore the last sync timestamp and re-sync everything:

```bash
readersync --full-sync
```

### Filter by Tag

Sync only documents with a specific tag:

```bash
readersync --tag productivity
```

### Filter by Category

Sync only specific document types (article, pdf, rss, etc.):

```bash
readersync --category pdf
```

### Filter by Location

Sync only documents from a specific location:

```bash
readersync --location archive
readersync --location new
```

Valid locations: `new`, `later`, `shortlist`, `archive`, `feed`.

### Custom Filename Format

Change the filename format using placeholders (`{id}` is always required):

```bash
readersync --filename-format "{title}-{id}"
readersync --filename-format "{id}-{title}"
readersync --filename-format "{date}-{id}-{title}"
```

### Flat Structure

Save all files in the output folder without category subfolders:

```bash
readersync --flat
```

### All Options

```bash
readersync --help

Options:
  --folder PATH              Output folder (defaults to current directory)
  --token TEXT                Readwise access token (or set READWISE_TOKEN env var)
  --full-sync                 Ignore last sync timestamp and sync all documents
  --tag TEXT                  Filter by tag
  --category TEXT             Filter by category (article, pdf, rss, etc.)
  --location [new|later|shortlist|archive|feed]
                              Filter by location
  --flat                      Save all files without category subfolders
  --filename-format TEXT      Filename format (default: {date}-{title}-{id})
  --help                      Show this message and exit
```

## Sync State

The tool maintains a `.last_sync` file in your output folder containing the ISO 8601 timestamp of the last successful sync. This enables incremental syncing - only fetching documents that have been added or updated since the last run.

To force a full re-sync, either:
- Delete the `.last_sync` file, or
- Use the `--full-sync` flag

## PDF Handling

PDFs are handled specially:
1. The original PDF is downloaded and saved (e.g., `YYYYMMDD-title-ID.pdf`)
2. MarkItDown extracts the text content
3. A markdown file is created with the extracted content (e.g., `YYYYMMDD-title-ID.md`)

Both files are kept so you have the original PDF for reference and searchable markdown for text operations.

## Rate Limits

The Readwise Reader API has the following rate limits:
- Standard endpoints: 20 requests/minute
- Create/Update endpoints: 50 requests/minute

The tool automatically handles pagination and respects these limits.

## Project Structure

```
readwise/
├── README.md                    # This file
├── CLAUDE.md                    # Detailed implementation guide
├── requirements.txt             # Python dependencies
├── setup.py                     # Package setup (defines 'readersync' command)
├── readersync/
│   ├── __init__.py
│   ├── cli.py                   # Command-line interface
│   ├── api_client.py            # Readwise API wrapper
│   ├── sync_manager.py          # Orchestrates sync process
│   ├── document_processor.py    # Groups documents with highlights
│   ├── markdown_generator.py    # Creates markdown files
│   └── utils.py                 # Helper functions
└── tests/                       # Unit tests
```

## Troubleshooting

### PDFs Not Downloading

PDFs are downloaded using pre-signed S3 URLs that expire after 1 hour. If you see 403 errors, the tool will automatically fetch fresh URLs.

### Missing Content

Some documents may not have full content available:
- Web pages that can't be parsed
- Restricted or paywalled content
- Documents that are just links/bookmarks

In these cases, the markdown file will include available metadata and any highlights.

### File Name Conflicts

File names are unique due to the Readwise ID suffix. If you manually rename files, the tool won't be able to update them - it will create new files with the correct naming convention.

## Obsidian Integration

Rather than running readersync manually, you can automate it from within Obsidian using two community plugins.

### Setup

1. **Install readersync globally** so it's available on your PATH:

   ```bash
   # If developing locally
   uv tool install -e /path/to/readwise

   # Or for end users
   pipx install readersync
   ```

2. **Install the [Shell Commands](https://github.com/Taitava/obsidian-shellcommands) plugin** in Obsidian. Define a new shell command:

   ```bash
   readersync --folder {{vault_path}}/Readwise
   ```

   For the token, either:
   - Set `READWISE_TOKEN` in your shell profile (`~/.zshrc`, `~/.bashrc`), or
   - Place a `.env` file in the output folder, or
   - Hardcode it: `readersync --folder {{vault_path}}/Readwise --token YOUR_TOKEN`

3. **Install the [Cron](https://github.com/cdloh/obsidian-cron) plugin** in Obsidian. Create a scheduled job pointing at the shell command you defined, e.g. every 30 minutes (`*/30 * * * *`) or once an hour (`0 * * * *`).

### How It Works

Obsidian Cron triggers Obsidian commands on a schedule. Shell Commands registers your `readersync` invocation as an Obsidian command. Together, they run the sync automatically in the background. Since Obsidian watches the filesystem, new and updated markdown files appear in your vault immediately after each sync completes.

### Why Not a Native Obsidian Plugin?

We considered rewriting readersync as an Obsidian plugin (TypeScript), but the main barrier is PDF text extraction. Obsidian plugins run in Electron/Node.js where there's no equivalent to Python's MarkItDown for high-quality PDF-to-markdown conversion. The JavaScript PDF libraries (`pdf-parse`, `pdf.js`) produce noticeably worse results on complex documents.

Keeping readersync as a Python CLI and triggering it from Obsidian gives you the best of both worlds: full PDF extraction quality and seamless vault integration.

## Contributing

This is a proof-of-concept tool for personal use. Contributions and suggestions are welcome!

## License

MIT License - feel free to modify and use for your own purposes.

## Related Projects

- [Readwise](https://readwise.io/) - Highlight management service
- [Readwise Reader](https://readwise.io/read) - Read-it-later app
- [MarkItDown](https://github.com/microsoft/markitdown) - Microsoft's document converter
- [Obsidian](https://obsidian.md/) - Markdown-based knowledge base

## API Documentation

- [Readwise Reader API](https://readwise.io/reader_api)
- [Get your access token](https://readwise.io/access_token)
