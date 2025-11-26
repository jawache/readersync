"""Markdown file generation."""

import os
import yaml
from typing import List, Dict, Optional


def generate_frontmatter(document: Dict) -> str:
    """Generate YAML frontmatter from document metadata.

    Args:
        document: Document dictionary from API

    Returns:
        YAML frontmatter as string
    """
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
        'created_at': document.get('created_at'),
        'saved_at': document.get('saved_at'),
        'updated_at': document.get('updated_at'),
        'published_date': document.get('published_date'),
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
    output_folder: str
) -> str:
    """Generate complete markdown file.

    Args:
        document: Document dictionary from API
        highlights: List of highlight documents
        content: Extracted content (or None)
        output_folder: Folder to save markdown file

    Returns:
        Path to generated markdown file
    """
    from .utils import generate_filename

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

    # Generate filename
    filename = generate_filename(document, '.md')
    filepath = os.path.join(output_folder, filename)

    # Write to file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(full_markdown)

    print(f"  Generated {filename}")
    return filepath
