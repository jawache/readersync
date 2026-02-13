"""Sync orchestration and state management."""

import os
from datetime import datetime, timezone
from typing import Optional

from .api_client import ReadwiseAPIClient
from .document_processor import group_documents, extract_content
from .markdown_generator import generate_markdown


LAST_SYNC_FILE = '.last_sync'


def read_last_sync(folder: str) -> Optional[str]:
    """Read last sync timestamp from file.

    Args:
        folder: Output folder containing .last_sync file

    Returns:
        ISO 8601 timestamp string or None
    """
    sync_file = os.path.join(folder, LAST_SYNC_FILE)

    if os.path.exists(sync_file):
        try:
            with open(sync_file, 'r') as f:
                timestamp = f.read().strip()
                if timestamp:
                    print(f"Last sync: {timestamp}")
                    return timestamp
        except Exception as e:
            print(f"Failed to read last sync timestamp: {e}")

    return None


def write_last_sync(folder: str, timestamp: Optional[str] = None):
    """Write current timestamp to .last_sync file.

    Args:
        folder: Output folder
        timestamp: ISO 8601 timestamp (defaults to now)
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')

    sync_file = os.path.join(folder, LAST_SYNC_FILE)

    try:
        with open(sync_file, 'w') as f:
            f.write(timestamp)
        print(f"Updated last sync timestamp: {timestamp}")
    except Exception as e:
        print(f"Failed to write last sync timestamp: {e}")


def sync(
    token: str,
    folder: str,
    full_sync: bool = False,
    tag: Optional[str] = None,
    category: Optional[str] = None,
    location: Optional[str] = None,
    flat: bool = False,
    filename_format: Optional[str] = None,
    force: bool = False
):
    """Perform sync of Readwise Reader documents.

    Args:
        token: Readwise access token
        folder: Output folder for markdown files
        full_sync: If True, ignore last sync and fetch all documents
        tag: Optional tag filter
        category: Optional category filter
        location: Optional location filter (new, later, shortlist, archive, feed)
        flat: If True, save files in flat structure (no category subfolders)
        filename_format: Optional filename format template
        force: If True, overwrite existing files even if unchanged
    """
    print("=" * 60)
    print("Starting readersync")
    print("=" * 60)

    # Create output folder if it doesn't exist
    os.makedirs(folder, exist_ok=True)
    print(f"Output folder: {os.path.abspath(folder)}")

    # Initialize API client
    print("\nConnecting to Readwise API...")
    api_client = ReadwiseAPIClient(token)

    # Test connection
    if not api_client.test_connection():
        print("ERROR: Failed to connect to Readwise API. Check your token.")
        return

    print("✓ Connected successfully")

    # Determine sync timestamp
    updated_after = None
    if not full_sync:
        updated_after = read_last_sync(folder)

    if full_sync:
        print("\nPerforming FULL sync (ignoring last sync timestamp)")
    elif updated_after:
        print(f"\nPerforming INCREMENTAL sync (since {updated_after})")
    else:
        print("\nPerforming initial sync (no previous sync found)")

    # Fetch documents from API
    print("\nFetching documents from Readwise...")
    documents = api_client.list_documents(
        updated_after=updated_after,
        tag=tag,
        category=category,
        location=location
    )

    if not documents:
        print("\nNo documents to sync.")
        write_last_sync(folder)
        return

    print(f"\n{len(documents)} documents to process")

    # Show location breakdown
    from collections import Counter
    location_counts = Counter(doc.get('location', 'unknown') for doc in documents if not doc.get('parent_id'))
    if location_counts:
        print("Location breakdown (parent documents only):")
        for loc, count in sorted(location_counts.items()):
            print(f"  {loc}: {count}")

    # Group documents (parents vs highlights)
    print("\nGrouping documents...")
    parents, highlights_by_parent = group_documents(documents)

    # Process each parent document
    print(f"\nProcessing {len(parents)} parent documents...")
    print("-" * 60)

    processed_count = 0
    error_count = 0

    for i, doc in enumerate(parents, 1):
        doc_id = doc.get('id', 'unknown')
        title = doc.get('title', 'Untitled')

        print(f"\n[{i}/{len(parents)}] {title[:60]}")
        print(f"  ID: {doc_id}")

        try:
            # Get highlights for this document
            doc_highlights = highlights_by_parent.get(doc_id, [])
            if doc_highlights:
                print(f"  Found {len(doc_highlights)} highlights")

            # Extract content
            content = extract_content(doc, folder, api_client, flat, filename_format)

            # Generate markdown file
            filepath = generate_markdown(doc, doc_highlights, content, folder, flat, filename_format, force=force)
            processed_count += 1

        except Exception as e:
            print(f"  ERROR: Failed to process document: {e}")
            error_count += 1
            continue

    # Update last sync timestamp
    print("\n" + "=" * 60)
    print(f"Sync completed!")
    print(f"  Processed: {processed_count}")
    print(f"  Errors: {error_count}")
    print("=" * 60)

    # Always write last sync timestamp so subsequent runs are incremental.
    # Failed documents will be retried on next sync since they'll still
    # show as updated in the API.
    write_last_sync(folder)
