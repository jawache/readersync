"""Utility functions for readersync."""

import os
import re
from datetime import datetime
from dateutil import parser as date_parser


def parse_iso8601(date_string):
    """Parse ISO 8601 date string to datetime object.

    Args:
        date_string: ISO 8601 formatted date string

    Returns:
        datetime object
    """
    if not date_string:
        return None
    return date_parser.isoparse(date_string)


def sanitize_title(title, max_length=60):
    """Sanitize title for use in filename.

    Args:
        title: Original title string
        max_length: Maximum length of sanitized title

    Returns:
        Sanitized title safe for filenames
    """
    if not title:
        return "untitled"

    # Lowercase
    title = title.lower()

    # Replace spaces and special chars with hyphens
    title = re.sub(r'[^a-z0-9]+', '-', title)

    # Remove leading/trailing hyphens
    title = title.strip('-')

    # Truncate
    if len(title) > max_length:
        title = title[:max_length].rstrip('-')

    # Ensure we have something
    if not title:
        return "untitled"

    return title


def generate_filename(document, extension=".md"):
    """Generate filename from document data.

    Format: YYYYMMDD-sanitized-title-READERID.ext

    Args:
        document: Document dictionary from API
        extension: File extension (default: .md)

    Returns:
        Generated filename
    """
    # Get date from saved_at
    saved_at = document.get('saved_at')
    if saved_at:
        saved_date = parse_iso8601(saved_at)
        date_prefix = saved_date.strftime('%Y%m%d')
    else:
        # Fallback to current date
        date_prefix = datetime.now().strftime('%Y%m%d')

    # Sanitize title
    title = document.get('title', 'untitled')
    sanitized = sanitize_title(title, max_length=60)

    # Get Readwise ID
    readwise_id = document['id']

    return f"{date_prefix}-{sanitized}-{readwise_id}{extension}"


def extract_readwise_id_from_filename(filename):
    """Extract Readwise ID from filename.

    Args:
        filename: Filename in format YYYYMMDD-title-ID.ext

    Returns:
        Readwise ID or None if not found
    """
    # Remove extension
    name_without_ext = filename.rsplit('.', 1)[0]

    # Split by hyphen and get last part (the ID)
    parts = name_without_ext.split('-')
    if parts:
        return parts[-1]
    return None


def get_category_folder(base_folder, category, use_flat=False):
    """Get the output folder for a document based on its category.

    Args:
        base_folder: Base output folder
        category: Document category (article, pdf, video, etc.)
        use_flat: If True, return base_folder (flat structure)

    Returns:
        Full path to category subfolder or base_folder if flat
    """
    if use_flat:
        return base_folder

    # Map categories to folder names (pluralized for clarity)
    category_folders = {
        'article': 'articles',
        'pdf': 'pdfs',
        'video': 'videos',
        'rss': 'rss',
        'epub': 'books',
        'tweet': 'tweets',
        'email': 'emails',
        'podcast': 'podcasts',
    }

    subfolder = category_folders.get(category, 'other')
    return os.path.join(base_folder, subfolder)
