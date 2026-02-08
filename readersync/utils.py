"""Utility functions for readersync."""

import os
import re
from datetime import datetime
from dateutil import parser as date_parser


DEFAULT_FILENAME_FORMAT = "{date}-{title}-{id}"

VALID_PLACEHOLDERS = {'date', 'title', 'id'}


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


def validate_filename_format(fmt):
    """Validate a filename format string.

    Args:
        fmt: Format string with {date}, {title}, {id} placeholders

    Returns:
        True if valid

    Raises:
        ValueError: If format is invalid
    """
    if '{id}' not in fmt:
        raise ValueError(
            f"Filename format must contain {{id}} placeholder. Got: {fmt}"
        )

    # Check for unknown placeholders
    used = set(re.findall(r'\{(\w+)\}', fmt))
    unknown = used - VALID_PLACEHOLDERS
    if unknown:
        raise ValueError(
            f"Unknown placeholders: {{{', '.join(unknown)}}}. "
            f"Valid placeholders: {{{', '.join(sorted(VALID_PLACEHOLDERS))}}}"
        )

    if len(used) < 2:
        raise ValueError(
            "Filename format must contain at least two placeholders "
            "(a filename of just an ID is unhelpful)"
        )

    return True


def generate_filename(document, extension=".md", fmt=None):
    """Generate filename from document data.

    Args:
        document: Document dictionary from API
        extension: File extension (default: .md)
        fmt: Format string with {date}, {title}, {id} placeholders.
             Defaults to DEFAULT_FILENAME_FORMAT.

    Returns:
        Generated filename
    """
    if fmt is None:
        fmt = DEFAULT_FILENAME_FORMAT

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

    name = fmt.format(date=date_prefix, title=sanitized, id=readwise_id)
    return f"{name}{extension}"


def find_existing_file(folder, readwise_id, extension=".md"):
    """Find an existing file for a Readwise document by its ID.

    Searches for files containing the readwise_id in their filename,
    regardless of the filename format used.

    Args:
        folder: Folder to search in
        readwise_id: Readwise document ID to search for

    Returns:
        Full path to existing file, or None if not found
    """
    if not os.path.isdir(folder):
        return None

    for filename in os.listdir(folder):
        if readwise_id in filename and filename.endswith(extension):
            return os.path.join(folder, filename)

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
