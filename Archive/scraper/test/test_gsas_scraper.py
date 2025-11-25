import pytest
import os
import sys
from bs4 import BeautifulSoup
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gsas_scraper import GsasArticleScraper

# Helper to get the absolute path for test files
_TEST_DIR = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture(scope="session")
def gsas_article_soup():
    """Provides a BeautifulSoup object from a saved GSAS article HTML file."""
    file_path = os.path.join(_TEST_DIR, "Saved_pages/GSAS_sample_article.html")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return BeautifulSoup(f.read(), "html.parser")
    except FileNotFoundError:
        pytest.fail(f"Test requires 'GSAS_sample_article.html' in the test directory: {file_path}")

@pytest.fixture(scope="session")
def gsas_topic_soup():
    """Provides a BeautifulSoup object from a saved GSAS topic page HTML file."""
    file_path = os.path.join(_TEST_DIR, "Saved_pages/GSAS_sample_topic_page.html")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return BeautifulSoup(f.read(), "html.parser")
    except FileNotFoundError:
        pytest.fail(f"Test requires 'GSAS_sample_topic_page.html' in the test directory: {file_path}")

@pytest.fixture
def gsas_scraper():
    """Provides a default instance of the GSAS scraper for testing."""
    with patch('V2.services.scraper.gsas_scraper.PostgresDBManager') as MockDBManager:
        mock_db_instance = MockDBManager.return_value
        mock_db_instance.filter_new_urls.return_value = []
        scraper_instance = GsasArticleScraper(headless=True)
        scraper_instance.db_manager = mock_db_instance
        yield scraper_instance

class TestGsasArticleScraper:

    def test_extract_article_links(self, gsas_scraper, gsas_topic_soup):
        """Verify that article links are correctly extracted from a topic page."""
        links = gsas_scraper.extract_article_links(gsas_topic_soup)
        assert isinstance(links, list)
        # Add more specific assertions based on your sample HTML

    def test_extract_article_content(self, gsas_scraper, gsas_article_soup):
        """Verify content extraction from a sample article."""
        content = gsas_scraper.extract_article_content(gsas_article_soup)
        assert isinstance(content, str)
        assert len(content) > 50

    def test_extract_article_title(self, gsas_scraper, gsas_article_soup):
        """Verify title extraction from a sample article."""
        title = gsas_scraper.extract_article_title(gsas_article_soup)
        assert isinstance(title, str)
        assert len(title) > 5

    def test_extract_article_author(self, gsas_scraper, gsas_article_soup):
        """Verify author extraction from a sample article."""
        author = gsas_scraper.extract_article_author(gsas_article_soup)
        # This might be None if the sample doesn't have an author
        if author is not None:
            assert isinstance(author, str)

    def test_extract_article_publish_date(self, gsas_scraper, gsas_article_soup):
        """Verify date parsing and formatting."""
        publish_date = gsas_scraper.extract_article_publish_date(gsas_article_soup)
        assert isinstance(publish_date, str)
        assert 'T' in publish_date

    def test_fetched_at_date_formatted(self, gsas_scraper):
        """Ensure fetched_at returns a valid ISO-formatted UTC string."""
        fetched_date = gsas_scraper.fetched_at_date_formatted()
        assert isinstance(fetched_date, str)
        assert 'T' in fetched_date and fetched_date.endswith('+00:00')

    @patch('V2.services.scraper.gsas_scraper.sync_playwright')
    def test_scrape_flow(self, mock_playwright, gsas_scraper, gsas_topic_soup, gsas_article_soup):
        """Test the main scrape orchestration with mocked browser interactions."""
        mock_page = MagicMock()
        mock_page.content.side_effect = [gsas_topic_soup.prettify(), gsas_article_soup.prettify()]
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        mock_playwright_context = MagicMock()
        mock_playwright_context.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_playwright_context

        test_url = "https://gsas.harvard.edu/news/some-article"
        gsas_scraper.db_manager.filter_new_urls.return_value = [test_url]
        gsas_scraper.topic_urls = ["http://fake-topic-url.com"]

        results = gsas_scraper.scrape()

        assert len(results) == 1
        assert results[0]["article_url"] == test_url
        mock_browser.close.assert_called_once()
