# readersync - Implementation Guide for Claude

This document contains detailed architecture, API exploration results, and implementation instructions for AI assistants working on this project.

## Project Overview

A Python CLI tool called `readersync` that syncs Readwise Reader documents to local markdown files with the following requirements:
- Incremental sync using timestamps
- Download PDFs and extract content
- Convert web articles to markdown
- Group highlights with parent documents
- Obsidian-compatible markdown with frontmatter
- Chronologically sortable filenames

## API Research Results

### Authentication
- Header: `Authorization: Token YOUR_TOKEN`
- Get token from: https://readwise.io/access_token
- Test token: `GET https://readwise.io/api/v2/auth/` (expect 204)

### Key API Endpoint

**Document List**
```
GET https://readwise.io/api/v3/list/
```

**Critical Parameters:**
- `updatedAfter` - ISO 8601 timestamp for incremental sync (e.g., "2025-11-24T17:05:46Z")
- `withHtmlContent=true` - Returns cleaned HTML in `html_content` field
- `withRawSourceUrl=true` - Returns pre-signed S3 URLs (valid 1 hour) for PDFs/EPUBs/HTML
- `pageCursor` - For pagination (response includes `nextPageCursor`)
- `tag` - Filter by tag (supports 1 tag)
- `category` - Filter by category (article, pdf, rss, etc.)
- `id` - Get specific document by ID

**Response Structure:**
```json
{
  "count": 32,
  "nextPageCursor": "cursor_string_or_null",
  "results": [
    {
      "id": "01kavd87rsgpqbbjqmwzz4yhtm",
      "url": "https://read.readwise.io/read/01kavd87...",
      "title": "Document Title",
      "author": "Author Name",
      "source": "Readwise web highlighter",
      "category": "pdf",  // or "article", "rss", etc.
      "location": "new",  // or "later", "archive", "feed"
      "tags": {},
      "site_name": "example.com",
      "word_count": 7795,
      "reading_time": "30 mins",
      "created_at": "2025-11-24T17:05:46.606468+00:00",
      "updated_at": "2025-11-24T22:56:05.839239+00:00",
      "published_date": "2025-11-12",
      "summary": "Brief summary...",
      "image_url": "https://...",
      "content": null,  // Always null, use withHtmlContent parameter
      "html_content": "<p>HTML content here</p>",  // Only with withHtmlContent=true
      "source_url": "https://original-source.com/article",
      "raw_source_url": "https://readwise-assets.s3.amazonaws.com/...",  // Only with withRawSourceUrl=true
      "notes": "",
      "parent_id": null,  // Non-null for highlights/notes
      "reading_progress": 1.0,  // 0.0 to 1.0
      "first_opened_at": "2025-11-24T17:05:46.265000+00:00",
      "last_opened_at": "2025-11-24T22:55:25.258000+00:00",
      "saved_at": "2025-11-24T17:05:46.265000+00:00",
      "last_moved_at": "2025-11-24T17:05:46.265000+00:00"
    }
  ]
}
```

### Document Types

1. **Parent Documents** (`parent_id == null`):
   - Articles, PDFs, RSS feeds, etc.
   - Have actual content
   - Should generate markdown files

2. **Highlights/Notes** (`parent_id != null`):
   - References parent document via `parent_id`
   - Should be grouped with parent in markdown file
   - Don't create separate files for these

### Content Retrieval Strategies

**PDFs** (`category: "pdf"`):
- Download from `raw_source_url` (pre-signed S3 URL, valid 1 hour)
- Verified working: Successfully downloaded 627KB PDF
- Fallback: Try `source_url` if `raw_source_url` is empty
- Use MarkItDown to extract text
- Keep both PDF and markdown file

**Web Articles** (`category: "article"`):
- Use `html_content` field (clean parsed HTML)
- Use MarkItDown to convert HTML → markdown
- Only create markdown file

**EPUBs/Other** (`category: "epub"`, etc.):
- Similar to PDFs - download from `raw_source_url`
- Use MarkItDown for conversion

### Rate Limits
- Standard: 20 requests/minute
- Create/Update: 50 requests/minute (not used in this tool)
- Check `Retry-After` header on 429 responses

### Tested API Calls

Successfully tested with token: `Jm9n4hldb6t5X08IiR9Bhg8xPASdPXlnUSGrJuTHQRDTXrMolc`

```bash
# List all documents
curl -H "Authorization: Token TOKEN" "https://readwise.io/api/v3/list/"

# List with content
curl -H "Authorization: Token TOKEN" "https://readwise.io/api/v3/list/?withHtmlContent=true&withRawSourceUrl=true"

# List PDFs only
curl -H "Authorization: Token TOKEN" "https://readwise.io/api/v3/list/?category=pdf"

# Get specific document
curl -H "Authorization: Token TOKEN" "https://readwise.io/api/v3/list/?id=DOCUMENT_ID&withHtmlContent=true&withRawSourceUrl=true"

# Download PDF from raw_source_url
curl -o file.pdf "PRESIGNED_S3_URL"
```

## File Naming Strategy

### Format
```
YYYYMMDD-sanitized-title-READERID.md
YYYYMMDD-sanitized-title-READERID.pdf  (for PDFs)
```

### Components
1. **Date** (`YYYYMMDD`):
   - Use `saved_at` timestamp
   - Format: `%Y%m%d`
   - Enables chronological sorting in file browsers

2. **Sanitized Title**:
   - Lowercase
   - Replace spaces with hyphens
   - Remove special characters (keep only alphanumeric and hyphens)
   - Truncate to 50-60 characters max
   - Example: `climate-change-computing-responsibility`

3. **Readwise ID**:
   - Taken from `id` field
   - Always at the end of filename
   - Enables unique identification
   - Allows finding files to update when documents change
   - Example: `01kavd87rsgpqbbjqmwzz4yhtm`

### Why This Format?
- **Chronological**: Obsidian and file browsers can sort by date
- **Readable**: Title is visible for human reference
- **Unique**: ID prevents conflicts
- **Mappable**: Can extract ID from filename to update documents
- **Stable**: Once created, filename doesn't change (even if title changes in Readwise)

### Implementation
```python
def generate_filename(document, extension=".md"):
    """Generate filename from document data."""
    saved_date = parse_iso8601(document['saved_at'])
    date_prefix = saved_date.strftime('%Y%m%d')

    title = document['title']
    sanitized = sanitize_title(title, max_length=60)

    readwise_id = document['id']

    return f"{date_prefix}-{sanitized}-{readwise_id}{extension}"

def sanitize_title(title, max_length=60):
    """Sanitize title for filename."""
    # Lowercase
    title = title.lower()
    # Replace spaces and special chars with hyphens
    title = re.sub(r'[^a-z0-9]+', '-', title)
    # Remove leading/trailing hyphens
    title = title.strip('-')
    # Truncate
    if len(title) > max_length:
        title = title[:max_length].rstrip('-')
    return title
```

## Sync State Management

### .last_sync File
- Location: `{output_folder}/.last_sync`
- Content: ISO 8601 timestamp (e.g., `2025-11-24T23:30:45.123456+00:00`)
- Used for incremental sync via `updatedAfter` parameter

### Update Logic
```python
# Read timestamp at start
if os.path.exists('.last_sync'):
    with open('.last_sync', 'r') as f:
        last_sync = f.read().strip()
else:
    last_sync = None

# Fetch documents
documents = api_client.list_documents(updated_after=last_sync)

# After successful sync, write current timestamp
with open('.last_sync', 'w') as f:
    f.write(datetime.now(timezone.utc).isoformat())
```

## Markdown File Structure

### YAML Frontmatter
Include all relevant metadata from API:
```yaml
---
readwise_id: "01kavd87rsgpqbbjqmwzz4yhtm"
title: "Document Title"
author: "Author Name"
url: "https://read.readwise.io/read/..."
source_url: "https://original-source.com"
category: pdf
location: new
tags:
  - tag1
  - tag2
site_name: "example.com"
word_count: 7795
reading_progress: 1.0
created_at: "2025-11-24T17:05:46+00:00"
saved_at: "2025-11-24T17:05:46+00:00"
updated_at: "2025-11-24T22:56:05+00:00"
published_date: "2025-11-12"
summary: "Brief summary of the document..."
---
```

### Highlights Section
```markdown
## Highlights

> First highlight text here

**Note:** Any notes associated with this highlight

**Tags:** tag1, tag2

> Second highlight text

---
```

### Content Section
```markdown
## Content

[Full article/document content converted to markdown]
```

## Document Processing Workflow

### High-Level Flow
```
1. Read .last_sync timestamp (if exists)
2. Call API with updatedAfter + withHtmlContent + withRawSourceUrl
3. Handle pagination (follow nextPageCursor)
4. Separate documents:
   - Parents (parent_id == null) → need markdown files
   - Children (parent_id != null) → group by parent_id
5. For each parent document:
   a. Generate filename (YYYYMMDD-title-ID.md)
   b. Fetch content:
      - PDF: Download raw_source_url → save .pdf, extract with markitdown
      - Article: Use html_content, convert with markitdown
   c. Find associated highlights (children with matching parent_id)
   d. Generate markdown with frontmatter + highlights + content
   e. Compare with existing file; skip write if unchanged (unless --force)
6. Write current timestamp to .last_sync
```

### Detailed Processing Steps

**1. API Fetching** (api_client.py)
```python
def list_documents(updated_after=None, tag=None, category=None):
    """Fetch documents from API with pagination."""
    params = {
        'withHtmlContent': 'true',
        'withRawSourceUrl': 'true'
    }
    if updated_after:
        params['updatedAfter'] = updated_after
    if tag:
        params['tag'] = tag
    if category:
        params['category'] = category

    all_documents = []
    page_cursor = None

    while True:
        if page_cursor:
            params['pageCursor'] = page_cursor

        response = requests.get(
            'https://readwise.io/api/v3/list/',
            headers={'Authorization': f'Token {self.token}'},
            params=params
        )
        response.raise_for_status()

        data = response.json()
        all_documents.extend(data['results'])

        page_cursor = data.get('nextPageCursor')
        if not page_cursor:
            break

    return all_documents
```

**2. Document Grouping** (document_processor.py)
```python
def group_documents(documents):
    """Separate parents and children, group highlights by parent."""
    parents = []
    highlights_by_parent = {}

    for doc in documents:
        if doc.get('parent_id'):
            # This is a highlight/note
            parent_id = doc['parent_id']
            if parent_id not in highlights_by_parent:
                highlights_by_parent[parent_id] = []
            highlights_by_parent[parent_id].append(doc)
        else:
            # This is a parent document
            parents.append(doc)

    return parents, highlights_by_parent
```

**3. Content Extraction** (document_processor.py)
```python
def extract_content(document, output_folder):
    """Extract document content based on category."""
    category = document.get('category', 'article')

    if category == 'pdf':
        # Download PDF
        raw_url = document.get('raw_source_url')
        if not raw_url:
            # Fallback to source_url
            raw_url = document.get('source_url')

        if raw_url:
            pdf_filename = generate_filename(document, '.pdf')
            pdf_path = os.path.join(output_folder, pdf_filename)
            download_file(raw_url, pdf_path)

            # Extract text with markitdown
            md = MarkItDown()
            result = md.convert(pdf_path)
            return result.text_content
        else:
            return None

    else:
        # Web article - use html_content
        html_content = document.get('html_content')
        if html_content:
            # Convert HTML to markdown
            md = MarkItDown()
            # MarkItDown can convert HTML string
            # May need to write to temp file first
            result = md.convert_html(html_content)
            return result.text_content
        else:
            return None
```

**4. Markdown Generation** (markdown_generator.py)
```python
def generate_markdown(document, highlights, content, output_folder):
    """Generate complete markdown file."""
    # Generate frontmatter
    frontmatter = generate_frontmatter(document)

    # Generate highlights section
    highlights_md = generate_highlights_section(highlights)

    # Combine all parts
    markdown = f"{frontmatter}\n\n"

    if highlights_md:
        markdown += f"## Highlights\n\n{highlights_md}\n\n---\n\n"

    if content:
        markdown += f"## Content\n\n{content}\n"

    # Write to file
    filename = generate_filename(document, '.md')
    filepath = os.path.join(output_folder, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(markdown)

    return filepath
```

## Dependencies

### Required Packages
```
requests>=2.31.0          # API calls
markitdown[all]>=0.0.1    # Document conversion
python-dateutil>=2.8.2    # ISO 8601 date parsing
click>=8.1.0              # CLI framework
pyyaml>=6.0               # YAML frontmatter
```

### MarkItDown Installation
```bash
pip install 'markitdown[all]'
```

This includes support for:
- PDF conversion
- DOCX, PPTX, XLSX
- Image OCR
- HTML parsing
- Audio transcription

## CLI Interface

### Command Name
The tool is installed as `readersync` (single word, no hyphens or underscores).

### Arguments
- `--folder PATH` (optional) - Output folder for markdown files (defaults to current directory)
- `--token TOKEN` - Readwise access token (or use READWISE_TOKEN env var)
- `--full-sync` - Ignore .last_sync and fetch all documents
- `--tag TAG` - Filter by tag
- `--category CATEGORY` - Filter by category (article, pdf, rss, etc.)
- `--location LOCATION` - Filter by location (new, later, shortlist, archive, feed)
- `--flat` - Save files in flat structure (no category subfolders)
- `--filename-format FORMAT` - Custom filename format with `{date}`, `{title}`, `{id}` placeholders
- `--force` - Overwrite existing files even if content is unchanged

### Example Usage
```bash
# Basic sync to current directory
readersync --token YOUR_TOKEN

# Sync to specific folder
readersync --folder ./my-readwise --token YOUR_TOKEN

# With environment variable
export READWISE_TOKEN=YOUR_TOKEN
readersync

# Full re-sync
readersync --full-sync

# Filter by tag
readersync --tag productivity

# Filter by category
readersync --category pdf

# Filter by location
readersync --location archive

# Force overwrite all files
readersync --force

# Full re-sync with forced overwrite
readersync --full-sync --force
```

### Installation as Command

**Recommended: Using uv**

The project uses modern Python packaging with `pyproject.toml` (like `package.json` in Node.js). This works best with `uv`, a fast Python package manager similar to pnpm/bun.

Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install the project:
```bash
uv pip install -e .
```

Run without installing:
```bash
uv run readersync --token YOUR_TOKEN
```

**pyproject.toml configuration:**
```toml
[project.scripts]
readersync = "readersync.cli:main"
```

This tells Python to create a `readersync` executable that calls the `main()` function in `readersync/cli.py`.

**cli.py must define:**
```python
import click

@click.command()
@click.option('--folder', default='.', help='Output folder (defaults to current directory)')
@click.option('--token', envvar='READWISE_TOKEN', help='Readwise access token')
@click.option('--full-sync', is_flag=True, help='Ignore last sync and sync all documents')
@click.option('--tag', help='Filter by tag')
@click.option('--category', help='Filter by category')
def main(folder, token, full_sync, tag, category):
    """Sync Readwise Reader documents to local markdown files."""
    # Implementation here
    pass

if __name__ == '__main__':
    main()
```

The key points:
- `--folder` defaults to `'.'` (current directory)
- `--token` reads from `READWISE_TOKEN` env var if not provided
- Click automatically generates `--help`

## Error Handling

### PDF Download Failures
- `raw_source_url` expires after 1 hour
- If download fails with 403, fetch fresh URL from API
- Fallback to `source_url` if `raw_source_url` is empty

### Missing Content
- Some documents may have no content available
- Create markdown file with metadata and highlights only
- Log warning for documents without content

### Rate Limiting
- Respect 20 requests/minute limit
- Add delays if hitting rate limits
- Check `Retry-After` header on 429 responses

### Network Failures
- Retry transient failures (timeouts, 5xx errors)
- Fail gracefully on auth errors (401, 403)
- Don't update .last_sync if sync fails

## Project Structure

```
readwise/
├── README.md                    # User-facing documentation
├── CLAUDE.md                    # This file - implementation guide
├── pyproject.toml               # Modern Python package config (like package.json)
├── requirements.txt             # Python dependencies (for compatibility)
├── setup.py                     # Legacy setup file (for compatibility)
├── .gitignore                   # Git ignore file
├── readersync/                  # Package name (no underscores)
│   ├── __init__.py
│   ├── __main__.py              # Entry point for `python -m readersync`
│   ├── cli.py                   # Click-based CLI (main entry point)
│   ├── api_client.py            # Readwise API wrapper
│   │   - authenticate()
│   │   - list_documents()
│   │   - download_file()
│   ├── sync_manager.py          # Orchestrates sync process
│   │   - sync()
│   │   - read_last_sync()
│   │   - write_last_sync()
│   ├── document_processor.py    # Document processing logic
│   │   - group_documents()
│   │   - extract_content()
│   ├── markdown_generator.py    # Markdown file generation
│   │   - generate_markdown()
│   │   - generate_frontmatter()
│   │   - generate_highlights_section()
│   └── utils.py                 # Helper functions
│       - generate_filename()
│       - sanitize_title()
│       - parse_iso8601()
└── tests/                       # Unit tests
    ├── __init__.py
    ├── test_api_client.py
    ├── test_document_processor.py
    ├── test_markdown_generator.py
    └── test_utils.py
```

## Implementation Tasks

### Phase 1: Core Infrastructure
- [ ] Project setup (requirements.txt, setup.py, .gitignore)
- [ ] Create package structure (reader_sync/ directory with __init__.py)
- [ ] Implement utils.py (filename generation, sanitization, date parsing)
- [ ] Write tests for utils.py

### Phase 2: API Client
- [ ] Implement api_client.py
  - [ ] Authentication
  - [ ] list_documents() with pagination
  - [ ] download_file() for PDFs
- [ ] Write tests for api_client.py (using mocked responses)

### Phase 3: Document Processing
- [ ] Implement document_processor.py
  - [ ] group_documents() - separate parents/children
  - [ ] extract_content() - handle PDFs and articles
  - [ ] Test with MarkItDown for PDF and HTML conversion
- [ ] Write tests for document_processor.py

### Phase 4: Markdown Generation
- [ ] Implement markdown_generator.py
  - [ ] generate_frontmatter() - YAML metadata
  - [ ] generate_highlights_section() - format highlights
  - [ ] generate_markdown() - combine all parts
- [ ] Write tests for markdown_generator.py

### Phase 5: Sync Manager
- [ ] Implement sync_manager.py
  - [ ] read_last_sync() / write_last_sync()
  - [ ] sync() orchestration function
  - [ ] Error handling and logging
- [ ] Write integration tests

### Phase 6: CLI Interface
- [ ] Implement cli.py with Click
  - [ ] --folder argument
  - [ ] --token argument (+ env var support)
  - [ ] --full-sync flag
  - [ ] --tag and --category filters
- [ ] Create __main__.py for `python -m reader_sync`
- [ ] Test CLI manually

### Phase 7: Polish
- [ ] Add logging throughout
- [ ] Improve error messages
- [ ] Add progress indicators
- [ ] Handle edge cases (empty titles, missing fields)
- [ ] Test with real Readwise data

### Phase 8: Documentation
- [x] Write README.md
- [x] Write CLAUDE.md
- [ ] Add docstrings to all functions
- [ ] Create examples/ directory with sample output

## Testing Strategy

### Unit Tests
- Test each module independently with mocked dependencies
- Focus on edge cases (empty data, missing fields, malformed input)

### Integration Tests
- Test full sync flow with mocked API responses
- Test incremental sync vs full sync
- Test handling of highlights without parents

### Manual Testing
- Test with real Readwise account
- Verify PDFs download correctly
- Verify markdown files render correctly in Obsidian
- Test incremental sync (run twice, second should be fast)
- Test with documents that have highlights

## Known Limitations

1. **API Limitations**:
   - Can only filter by 1 tag at a time
   - No way to fetch highlights for specific document in one call
   - Pre-signed URLs expire after 1 hour

2. **Content Availability**:
   - Some documents may not have full content
   - Paywalled or restricted content won't be available
   - PDF extraction quality depends on PDF structure

3. **File Management**:
   - Manual file renames will break update mechanism
   - Deleting .last_sync forces full re-sync
   - No automatic cleanup of deleted documents

4. **Performance**:
   - Large PDFs may take time to process
   - Rate limits may slow down initial sync of large libraries

## Future Enhancements

- [ ] Support for multiple tags filter
- [ ] Automatic cleanup of deleted/archived documents
- [ ] Progress bar for large syncs
- [ ] Configurable markdown template
- [ ] Support for custom metadata fields
- [ ] Incremental PDF updates (only re-download if changed)
- [ ] Parallel processing for faster syncs
- [ ] Web interface for configuration
- [ ] Docker container for easy deployment

## References

- [Readwise Reader API Documentation](https://readwise.io/reader_api)
- [MarkItDown GitHub](https://github.com/microsoft/markitdown)
- [Click Documentation](https://click.palletsprojects.com/)
- [PyYAML Documentation](https://pyyaml.org/wiki/PyYAMLDocumentation)
