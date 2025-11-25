import pytest
import os
import sys
from bs4 import BeautifulSoup
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harvard_magazine_scraper import HarvardMagazineArticleScraper

# Helper to get the absolute path for test files
_TEST_DIR = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture(scope="session")
def hm_article_soup():
    """Provides a BeautifulSoup object from a saved Harvard Magazine article HTML file."""
    file_path = os.path.join(_TEST_DIR, "Saved_pages/Harvard_Magazine_sample_article.html")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return BeautifulSoup(f.read(), "html.parser")
    except FileNotFoundError:
        pytest.fail(f"Test requires 'HM_sample_article.html' in the test directory: {file_path}")

@pytest.fixture(scope="session")
def hm_topic_soup():
    """Provides a BeautifulSoup object from a saved Harvard Magazine topic page HTML file."""
    file_path = os.path.join(_TEST_DIR, "Saved_pages/Harvard_Magazine_sample_topic_page.html")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return BeautifulSoup(f.read(), "html.parser")
    except FileNotFoundError:
        pytest.fail(f"Test requires 'Harvard_Magazine_sample_topic_page.html' in the test directory: {file_path}")

@pytest.fixture
def hm_scraper():
    """Provides a default instance of the Harvard Magazine scraper for testing."""
    with patch('V2.services.scraper.harvard_magazine_scraper.PostgresDBManager') as MockDBManager:
        mock_db_instance = MockDBManager.return_value
        mock_db_instance.filter_new_urls.return_value = []
        scraper_instance = HarvardMagazineArticleScraper(headless=True)
        scraper_instance.db_manager = mock_db_instance
        yield scraper_instance

class TestHarvardMagazineArticleScraper:

    def test_extract_article_links(self, hm_scraper, hm_topic_soup):
        """Verify that article links are correctly extracted from a topic page."""
        links = hm_scraper.extract_article_links(hm_topic_soup)
        assert isinstance(links, list)
        # Add more specific assertions based on your sample HTML

    def test_extract_article_content(self, hm_scraper, hm_article_soup):
        """Verify content extraction from a sample article."""
        content = hm_scraper.extract_article_content(hm_article_soup)
        assert isinstance(content, str)
        assert len(content) > 50

    def test_extract_article_title(self, hm_scraper, hm_article_soup):
        """Verify title extraction from a sample article."""
        title = hm_scraper.extract_article_title(hm_article_soup)
        assert isinstance(title, str)
        assert len(title) > 5

    def test_extract_article_author(self, hm_scraper, hm_article_soup):
        """Verify author extraction from a sample article."""
        author = hm_scraper.extract_article_author(hm_article_soup)
        if author is not None:
            assert isinstance(author, str)

    def test_extract_article_publish_date(self, hm_scraper, hm_article_soup):
        """Verify date parsing and formatting."""
        publish_date = hm_scraper.extract_article_publish_date(hm_article_soup)
        assert isinstance(publish_date, str)
        assert 'T' in publish_date

    def test_fetched_at_date_formatted(self, hm_scraper):
        """Ensure fetched_at returns a valid ISO-formatted UTC string."""
        fetched_date = hm_scraper.fetched_at_date_formatted()
        assert isinstance(fetched_date, str)
        assert 'T' in fetched_date and fetched_date.endswith('+00:00')

    @patch('V2.services.scraper.harvard_magazine_scraper.sync_playwright')
    def test_scrape_flow(self, mock_playwright, hm_scraper, hm_topic_soup, hm_article_soup):
        """Test the main scrape orchestration with mocked browser interactions."""
        mock_page = MagicMock()
        mock_page.content.side_effect = [hm_topic_soup.prettify(), hm_article_soup.prettify()]
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        mock_playwright_context = MagicMock()
        mock_playwright_context.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_playwright_context

        test_url = "https://www.harvardmagazine.com/2023/01/some-article"
        hm_scraper.db_manager.filter_new_urls.return_value = [test_url]
        hm_scraper.topic_urls = ["http://fake-topic-url.com"]

        results = hm_scraper.scrape()

        assert len(results) == 1
        assert results[0]["article_url"] == test_url
        mock_browser.close.assert_called_once()
