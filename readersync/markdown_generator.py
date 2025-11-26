"""Markdown file generation."""

import os
import yaml
from typing import List, Dict, Optional


def clean_datetime(datetime_str: Optional[str]) -> Optional[str]:
    """Remove microseconds and timezone from datetime string.

    Args:
        datetime_str: ISO 8601 datetime string

    Returns:
        Cleaned datetime string in format YYYY-MM-DDTHH:MM:SS or None
    """
    if not datetime_str:
        return None

    # Remove microseconds and timezone
    # Handles formats like:
    # - 2025-11-24T17:05:46.123456Z -> 2025-11-24T17:05:46
    # - 2025-11-24T17:05:46+00:00 -> 2025-11-24T17:05:46
    # - 2025-11-24T17:05:46Z -> 2025-11-24T17:05:46

    # Split on 'T' to separate date and time
    if 'T' not in datetime_str:
        return datetime_str

    date_part, time_part = datetime_str.split('T', 1)

    # Remove microseconds (everything after the dot)
    if '.' in time_part:
        time_part = time_part.split('.', 1)[0]

    # Remove timezone (Z or +/-offset)
    if 'Z' in time_part:
        time_part = time_part.split('Z', 1)[0]
    elif '+' in time_part:
        time_part = time_part.split('+', 1)[0]
    elif time_part.count('-') > 0:
        # Be careful - time might have HH-MM-SS format (shouldn't, but be safe)
        # Only remove timezone offset like -05:00, not part of time
        parts = time_part.split('-')
        if len(parts) > 1 and ':' in parts[-1]:
            time_part = '-'.join(parts[:-1])

    return f"{date_part}T{time_part}"


def generate_frontmatter(document: Dict) -> str:
    """Generate YAML frontmatter from document metadata.

    Args:
        document: Document dictionary from API

    Returns:
        YAML frontmatter as string
    """
    # Get cleaned saved_at for reuse
    saved_at_clean = clean_datetime(document.get('saved_at'))

    # Extract date component from saved_at (YYYY-MM-DD)
    date_only = None
    if saved_at_clean and 'T' in saved_at_clean:
        date_only = saved_at_clean.split('T')[0]
    elif saved_at_clean:
        date_only = saved_at_clean

    # Extract relevant fields
    metadata = {
        'readwise_id': document.get('id'),
        'title': document.get('title'),
        'author': document.get('author'),
        'url': document.get('url'),
        'source_url': document.get('source_url'),
        'category': document.get('category'),
        'location': document.get('location'),
        'tags': list(document.get('tags', {}).keys()) if document.get('tags') else [],
        'site_name': document.get('site_name'),
        'word_count': document.get('word_count'),
        'reading_progress': document.get('reading_progress'),
        'cover': document.get('image_url'),
        'date': date_only,
        'created_at': clean_datetime(document.get('created_at')),
        'saved_at': saved_at_clean,
        'updated_at': clean_datetime(document.get('updated_at')),
        'published_date': clean_datetime(document.get('published_date')),
        'summary': document.get('summary'),
    }

    # Remove None values
    metadata = {k: v for k, v in metadata.items() if v is not None}

    # Convert to YAML
    yaml_str = yaml.dump(metadata, default_flow_style=False, allow_unicode=True, sort_keys=False)

    return f"---\n{yaml_str}---\n"


def generate_highlights_section(highlights: List[Dict]) -> str:
    """Generate markdown for highlights section.

    Args:
        highlights: List of highlight/note documents

    Returns:
        Markdown string for highlights section
    """
    if not highlights:
        return ""

    lines = []

    for highlight in highlights:
        # Get the content field which contains the highlighted text
        text = highlight.get('content', '')
        if text:
            # Format as blockquote, handling multi-line highlights
            for line in text.strip().split('\n'):
                if line.strip():
                    lines.append(f"> {line}")
            lines.append("")  # Empty line after quote

        # Add any notes
        notes = highlight.get('notes', '')
        if notes:
            lines.append(f"**Note:** {notes}\n")

        # Add tags if any
        tags = highlight.get('tags', {})
        if tags:
            tag_list = ', '.join(tags.keys())
            lines.append(f"**Tags:** {tag_list}\n")

        lines.append("")  # Empty line between highlights

    return "\n".join(lines)


def generate_markdown(
    document: Dict,
    highlights: List[Dict],
    content: Optional[str],
    output_folder: str,
    flat: bool = False
) -> str:
    """Generate complete markdown file.

    Args:
        document: Document dictionary from API
        highlights: List of highlight documents
        content: Extracted content (or None)
        output_folder: Folder to save markdown file
        flat: If True, save files in flat structure (no category subfolders)

    Returns:
        Path to generated markdown file
    """
    from .utils import generate_filename, get_category_folder

    # Generate frontmatter
    frontmatter = generate_frontmatter(document)

    # Start building markdown
    markdown_parts = [frontmatter]

    # Add highlights section if any
    if highlights:
        highlights_md = generate_highlights_section(highlights)
        if highlights_md:
            markdown_parts.append("## Highlights\n")
            markdown_parts.append(highlights_md)
            markdown_parts.append("---\n")

    # Add content section
    if content:
        markdown_parts.append("## Content\n")
        markdown_parts.append(content)
    else:
        # No content available, just add a note
        markdown_parts.append("## Content\n")
        markdown_parts.append("*No content available for this document.*\n")

    # Combine all parts
    full_markdown = "\n".join(markdown_parts)

    # Generate filename and determine output folder
    filename = generate_filename(document, '.md')
    category = document.get('category', 'article')
    category_folder = get_category_folder(output_folder, category, flat)
    os.makedirs(category_folder, exist_ok=True)
    filepath = os.path.join(category_folder, filename)

    # Write to file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(full_markdown)

    print(f"  Generated {filename}")
    return filepath
