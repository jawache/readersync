"""Readwise Reader API client."""

import requests
import time
from typing import List, Dict, Optional


class ReadwiseAPIClient:
    """Client for interacting with Readwise Reader API."""

    BASE_URL = "https://readwise.io/api/v3"

    def __init__(self, token: str):
        """Initialize API client.

        Args:
            token: Readwise access token
        """
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {token}'
        })

    def test_connection(self) -> bool:
        """Test API connection.

        Returns:
            True if connection successful
        """
        try:
            response = self.session.get('https://readwise.io/api/v2/auth/')
            return response.status_code == 204
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False

    def list_documents(
        self,
        updated_after: Optional[str] = None,
        tag: Optional[str] = None,
        category: Optional[str] = None,
        document_id: Optional[str] = None
    ) -> List[Dict]:
        """Fetch documents from API with pagination.

        Args:
            updated_after: ISO 8601 timestamp for incremental sync
            tag: Filter by tag
            category: Filter by category
            document_id: Get specific document by ID

        Returns:
            List of document dictionaries
        """
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
        if document_id:
            params['id'] = document_id

        all_documents = []
        page_cursor = None
        page_count = 0

        while True:
            if page_cursor:
                params['pageCursor'] = page_cursor

            try:
                response = self.session.get(
                    f'{self.BASE_URL}/list/',
                    params=params
                )
                response.raise_for_status()

                data = response.json()
                documents = data.get('results', [])
                all_documents.extend(documents)

                page_count += 1
                print(f"Fetched page {page_count}: {len(documents)} documents")

                page_cursor = data.get('nextPageCursor')
                if not page_cursor:
                    break

                # Small delay to respect rate limits
                time.sleep(0.1)

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    # Rate limited
                    retry_after = int(e.response.headers.get('Retry-After', 60))
                    print(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                else:
                    raise

        print(f"Total documents fetched: {len(all_documents)}")
        return all_documents

    def download_file(self, url: str, output_path: str) -> bool:
        """Download file from URL.

        Args:
            url: URL to download from
            output_path: Path to save file

        Returns:
            True if download successful
        """
        try:
            # Don't use auth headers for S3 pre-signed URLs
            response = requests.get(url, stream=True)
            response.raise_for_status()

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return True
        except Exception as e:
            print(f"Failed to download {url}: {e}")
            return False
