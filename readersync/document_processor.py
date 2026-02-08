"""Document processing logic."""

import os
import re
import tempfile
from typing import List, Dict, Tuple, Optional
from markitdown import MarkItDown


def group_documents(documents: List[Dict]) -> Tuple[List[Dict], Dict[str, List[Dict]]]:
    """Separate parents and children, group highlights by parent.

    Args:
        documents: List of document dictionaries from API

    Returns:
        Tuple of (parent_documents, highlights_by_parent_id)
    """
    parents = []
    highlights_by_parent = {}

    for doc in documents:
        parent_id = doc.get('parent_id')
        if parent_id:
            # This is a highlight/note
            if parent_id not in highlights_by_parent:
                highlights_by_parent[parent_id] = []
            highlights_by_parent[parent_id].append(doc)
        else:
            # This is a parent document
            parents.append(doc)

    print(f"Found {len(parents)} parent documents and {sum(len(h) for h in highlights_by_parent.values())} highlights")
    return parents, highlights_by_parent


def extract_content_from_pdf(pdf_path: str) -> Optional[str]:
    """Extract text content from PDF file.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Extracted text content or None
    """
    try:
        md = MarkItDown()
        result = md.convert(pdf_path)
        return result.text_content
    except Exception as e:
        print(f"Failed to extract content from PDF {pdf_path}: {e}")
        return None


def extract_content_from_html(html_content: str) -> Optional[str]:
    """Convert HTML content to markdown.

    Args:
        html_content: HTML string

    Returns:
        Markdown content or None
    """
    try:
        # Pre-process HTML to fix spacing issues
        # Add <br> tags before all closing tags to force line breaks
        # This is especially important for video transcripts where inline elements
        # can cause words to be mushed together when tags are stripped
        # It's okay to have extra line breaks - better than concatenated words
        html_content = re.sub(r'</(\w+)>', r'<br></\1>', html_content)

        # MarkItDown expects file paths, so we need to write to a temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            temp_path = f.name

        try:
            md = MarkItDown()
            result = md.convert(temp_path)
            return result.text_content
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    except Exception as e:
        print(f"Failed to convert HTML to markdown: {e}")
        return None


def extract_content(document: Dict, output_folder: str, api_client, flat: bool = False, filename_format: Optional[str] = None) -> Optional[str]:
    """Extract document content based on category.

    Args:
        document: Document dictionary from API
        output_folder: Folder to save PDFs
        api_client: API client for downloading files
        flat: If True, save files in flat structure (no category subfolders)
        filename_format: Optional filename format template

    Returns:
        Extracted markdown content or None
    """
    from .utils import generate_filename, get_category_folder

    category = document.get('category', 'article')
    doc_id = document.get('id', 'unknown')

    print(f"Extracting content for {doc_id} (category: {category})")

    if category == 'pdf':
        # First, try to use Readwise's parsed HTML content (much better quality)
        html_content = document.get('html_content')

        if html_content:
            print(f"  Converting parsed HTML to markdown")
            content = extract_content_from_html(html_content)
            if content:
                print(f"  Converted {len(content)} characters")

            # Still download the original PDF for reference
            raw_url = document.get('raw_source_url')
            if not raw_url:
                raw_url = document.get('source_url')
                if raw_url and not raw_url.endswith('.pdf'):
                    raw_url = None

            if raw_url:
                pdf_filename = generate_filename(document, '.pdf', fmt=filename_format)
                category_folder = get_category_folder(output_folder, category, flat)
                os.makedirs(category_folder, exist_ok=True)
                pdf_path = os.path.join(category_folder, pdf_filename)
                print(f"  Downloading original PDF to {pdf_filename}")
                api_client.download_file(raw_url, pdf_path)

            return content
        else:
            # Fallback: download and extract text from PDF
            raw_url = document.get('raw_source_url')
            if not raw_url:
                raw_url = document.get('source_url')
                if raw_url and not raw_url.endswith('.pdf'):
                    raw_url = None

            if raw_url:
                pdf_filename = generate_filename(document, '.pdf', fmt=filename_format)
                category_folder = get_category_folder(output_folder, category, flat)
                os.makedirs(category_folder, exist_ok=True)
                pdf_path = os.path.join(category_folder, pdf_filename)
                print(f"  Downloading PDF to {pdf_filename}")
                success = api_client.download_file(raw_url, pdf_path)

                if success and os.path.exists(pdf_path):
                    print(f"  Extracting text from PDF")
                    content = extract_content_from_pdf(pdf_path)
                    if content:
                        print(f"  Extracted {len(content)} characters")
                    return content
                else:
                    print(f"  PDF download failed")
                    return None
            else:
                print(f"  No PDF URL available")
                return None

    else:
        # Web article - use html_content
        html_content = document.get('html_content')

        if html_content:
            print(f"  Converting HTML to markdown")
            content = extract_content_from_html(html_content)
            if content:
                print(f"  Converted {len(content)} characters")
            return content
        else:
            # No content available
            print(f"  No HTML content available")
            return None
