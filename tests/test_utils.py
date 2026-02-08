"""Tests for readersync utility functions."""

import os
import tempfile
import pytest
from readersync.utils import (
    sanitize_title,
    generate_filename,
    validate_filename_format,
    find_existing_file,
    DEFAULT_FILENAME_FORMAT,
)


# --- sanitize_title ---

def test_sanitize_title_basic():
    assert sanitize_title("Hello World") == "hello-world"


def test_sanitize_title_special_chars():
    assert sanitize_title("What's Up? (2024)") == "what-s-up-2024"


def test_sanitize_title_truncates():
    long_title = "a" * 100
    result = sanitize_title(long_title, max_length=60)
    assert len(result) <= 60


def test_sanitize_title_empty():
    assert sanitize_title("") == "untitled"
    assert sanitize_title(None) == "untitled"


def test_sanitize_title_only_special_chars():
    assert sanitize_title("!!!???") == "untitled"


def test_sanitize_title_strips_hyphens():
    assert sanitize_title("  --hello--  ") == "hello"


# --- validate_filename_format ---

def test_validate_format_default():
    assert validate_filename_format("{date}-{title}-{id}") is True


def test_validate_format_title_id():
    assert validate_filename_format("{title}-{id}") is True


def test_validate_format_id_title():
    assert validate_filename_format("{id}-{title}") is True


def test_validate_format_missing_id():
    with pytest.raises(ValueError, match="must contain {id}"):
        validate_filename_format("{date}-{title}")


def test_validate_format_unknown_placeholder():
    with pytest.raises(ValueError, match="Unknown placeholders"):
        validate_filename_format("{date}-{title}-{id}-{author}")


def test_validate_format_only_id():
    with pytest.raises(ValueError, match="at least two placeholders"):
        validate_filename_format("{id}")


# --- generate_filename ---

SAMPLE_DOC = {
    'id': '01kavd87rsgpqbbjqmwzz4yhtm',
    'title': 'Climate Change: Computing Responsibility',
    'saved_at': '2024-11-24T17:05:46.606468+00:00',
}


def test_generate_filename_default_format():
    result = generate_filename(SAMPLE_DOC)
    assert result == "20241124-climate-change-computing-responsibility-01kavd87rsgpqbbjqmwzz4yhtm.md"


def test_generate_filename_title_id_format():
    result = generate_filename(SAMPLE_DOC, fmt="{title}-{id}")
    assert result == "climate-change-computing-responsibility-01kavd87rsgpqbbjqmwzz4yhtm.md"


def test_generate_filename_id_title_format():
    result = generate_filename(SAMPLE_DOC, fmt="{id}-{title}")
    assert result == "01kavd87rsgpqbbjqmwzz4yhtm-climate-change-computing-responsibility.md"


def test_generate_filename_date_id_format():
    result = generate_filename(SAMPLE_DOC, fmt="{date}-{id}-{title}")
    assert result == "20241124-01kavd87rsgpqbbjqmwzz4yhtm-climate-change-computing-responsibility.md"


def test_generate_filename_pdf_extension():
    result = generate_filename(SAMPLE_DOC, extension=".pdf")
    assert result.endswith(".pdf")
    assert "01kavd87rsgpqbbjqmwzz4yhtm" in result


def test_generate_filename_no_saved_at():
    doc = {'id': 'abc123', 'title': 'Test'}
    result = generate_filename(doc)
    # Should use today's date as fallback
    assert result.endswith("-abc123.md")
    assert "test" in result


def test_generate_filename_no_title():
    doc = {'id': 'abc123', 'saved_at': '2024-01-01T00:00:00Z'}
    result = generate_filename(doc)
    assert "untitled" in result


# --- find_existing_file ---

def test_find_existing_file_found():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a file with the ID in the name
        filename = "20241124-some-title-abc123def.md"
        open(os.path.join(tmpdir, filename), 'w').close()

        result = find_existing_file(tmpdir, "abc123def")
        assert result == os.path.join(tmpdir, filename)


def test_find_existing_file_not_found():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = find_existing_file(tmpdir, "nonexistent")
        assert result is None


def test_find_existing_file_different_format():
    with tempfile.TemporaryDirectory() as tmpdir:
        # File with ID in a different position
        filename = "abc123def-some-title.md"
        open(os.path.join(tmpdir, filename), 'w').close()

        result = find_existing_file(tmpdir, "abc123def")
        assert result == os.path.join(tmpdir, filename)


def test_find_existing_file_nonexistent_dir():
    result = find_existing_file("/nonexistent/path", "abc123")
    assert result is None


def test_find_existing_file_ignores_wrong_extension():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a PDF with the ID
        open(os.path.join(tmpdir, "20241124-title-abc123.pdf"), 'w').close()

        # Searching for .md should not find the .pdf
        result = find_existing_file(tmpdir, "abc123", extension=".md")
        assert result is None

        # Searching for .pdf should find it
        result = find_existing_file(tmpdir, "abc123", extension=".pdf")
        assert result is not None
