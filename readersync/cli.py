"""Command-line interface for readersync."""

import click
import sys
import os
from dotenv import load_dotenv
from .sync_manager import sync

# Load environment variables from .env file
load_dotenv()


@click.command()
@click.option(
    '--folder',
    default='.',
    help='Output folder for markdown files (defaults to current directory)',
    type=click.Path(file_okay=False, writable=True)
)
@click.option(
    '--token',
    envvar='READWISE_TOKEN',
    required=True,
    help='Readwise access token (or set READWISE_TOKEN env var)'
)
@click.option(
    '--full-sync',
    is_flag=True,
    help='Ignore last sync timestamp and sync all documents'
)
@click.option(
    '--tag',
    help='Filter documents by tag'
)
@click.option(
    '--category',
    help='Filter documents by category (article, pdf, rss, etc.)'
)
@click.option(
    '--flat',
    is_flag=True,
    help='Save all files in flat structure (no category subfolders)'
)
def main(folder, token, full_sync, tag, category, flat):
    """Sync Readwise Reader documents to local markdown files.

    This tool downloads your Readwise Reader documents and converts them
    to markdown files with YAML frontmatter, perfect for use with Obsidian
    and other markdown-based tools.

    Examples:

        \b
        # Sync to current directory
        readersync --token YOUR_TOKEN

        \b
        # Sync to specific folder
        readersync --folder ./my-obsidian-vault --token YOUR_TOKEN

        \b
        # Use environment variable for token
        export READWISE_TOKEN=YOUR_TOKEN
        readersync

        \b
        # Full re-sync (ignore incremental state)
        readersync --full-sync

        \b
        # Sync only PDFs
        readersync --category pdf
    """
    try:
        sync(
            token=token,
            folder=folder,
            full_sync=full_sync,
            tag=tag,
            category=category,
            flat=flat
        )
    except KeyboardInterrupt:
        print("\n\nSync interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
