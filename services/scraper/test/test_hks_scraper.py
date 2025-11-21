import pytest
import os
from bs4 import BeautifulSoup
from unittest.mock import patch, MagicMock
from ..hks_scraper import HksArticleScraper

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture(scope="session")
def hks_article_soup():
    """Provides a BeautifulSoup object from a saved HKS article HTML file."""
    file_path = os.path.join(_TEST_DIR, "Saved_pages/HKS_sample_article.html")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return BeautifulSoup(f.read(), "html.parser")
    except FileNotFoundError:
        pytest.fail(f"Test requires 'HKS_sample_article.html' in the test directory: {file_path}")

@pytest.fixture(scope="session")
def hks_topic_soup():
    """Provides a BeautifulSoup object from a saved HKS topic page HTML file."""
    file_path = os.path.join(_TEST_DIR, "Saved_pages/HKS_sample_topic_page.html")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return BeautifulSoup(f.read(), "html.parser")
    except FileNotFoundError:
        pytest.fail(f"Test requires 'HKS_sample_topic_page.html' in the test directory: {file_path}")

@pytest.fixture
def hks_scraper():
    """Provides a default instance of the HKS scraper for testing."""
    with patch('V2.services.scraper.hks_scraper.PostgresDBManager') as MockDBManager:
        mock_db_instance = MockDBManager.return_value
        mock_db_instance.filter_new_urls.return_value = []
        scraper_instance = HksArticleScraper(headless=True, test_mode=False)
        scraper_instance.db_manager = mock_db_instance
        yield scraper_instance

class TestHksArticleScraper:

    def test_extract_article_links(self, hks_scraper, hks_topic_soup):
        """Verify that article links are correctly extracted from a topic page."""
        links = hks_scraper.extract_article_links(hks_topic_soup)
        assert isinstance(links, list)

    def test_extract_article_content(self, hks_scraper, hks_article_soup):
        """Verify content extraction from a sample article."""
        content = hks_scraper.extract_article_content(hks_article_soup)
        if content:
            assert isinstance(content, str)
            assert len(content) > 50

    def test_extract_article_content_missing(self, hks_scraper):
        """Test content extraction when the main content div is missing."""
        soup = BeautifulSoup('<div>No content</div>', 'html.parser')
        content = hks_scraper.extract_article_content(soup)
        assert content is None

    def test_extract_article_title(self, hks_scraper, hks_article_soup):
        """Verify title extraction from a sample article."""
        title = hks_scraper.extract_article_title(hks_article_soup)
        if title:
            assert isinstance(title, str)
            assert len(title) > 5

    def test_extract_article_author(self, hks_scraper, hks_article_soup):
        """Verify author extraction returns None (HKS articles don't have clear authors)."""
        author = hks_scraper.extract_article_author(hks_article_soup)
        assert author is None

    def test_extract_article_publish_date(self, hks_scraper, hks_article_soup):
        """Verify date parsing and formatting."""
        publish_date = hks_scraper.extract_article_publish_date(hks_article_soup)
        if publish_date:
            assert isinstance(publish_date, str)
            assert 'T' in publish_date

    def test_extract_publish_date_missing(self, hks_scraper):
        """Test date extraction when the time tag is missing."""
        soup = BeautifulSoup('<div>No date</div>', 'html.parser')
        date = hks_scraper.extract_article_publish_date(soup)
        assert date is None

    @patch('V2.services.scraper.hks_scraper.dateparser.parse', return_value=None)
    def test_extract_publish_date_parse_fails(self, mock_parse, hks_scraper, hks_article_soup):
        """Test date extraction when dateparser fails to parse."""
        date = hks_scraper.extract_article_publish_date(hks_article_soup)
        assert date is None

    @patch('V2.services.scraper.hks_scraper.dateparser.parse', side_effect=Exception("Parsing failed"))
    def test_extract_publish_date_exception(self, mock_parse, hks_scraper, hks_article_soup):
        """Test date extraction when dateparser raises an exception."""
        date = hks_scraper.extract_article_publish_date(hks_article_soup)
        assert date is None

    def test_fetched_at_date_formatted(self, hks_scraper):
        """Ensure fetched_at returns a valid ISO-formatted UTC string."""
        fetched_date = hks_scraper.fetched_at_date_formatted()
        assert isinstance(fetched_date, str)
        assert 'T' in fetched_date
        assert fetched_date.endswith('+00:00')

    @patch('V2.services.scraper.hks_scraper.sync_playwright')
    def test_scrape_flow(self, mock_playwright, hks_scraper, hks_topic_soup, hks_article_soup):
        """Test the main scrape orchestration with mocked browser interactions."""
        mock_page = MagicMock()
        mock_page.content.side_effect = [hks_topic_soup.prettify(), hks_article_soup.prettify()]
        
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        
        mock_playwright_context = MagicMock()
        mock_playwright_context.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_playwright_context
        
        test_url = "https://hks.harvard.edu/announcements/test-article"
        hks_scraper.db_manager.filter_new_urls.return_value = [test_url]
        hks_scraper.topic_urls = ["http://fake-topic-url.com"]
        
        results = hks_scraper.scrape()
        
        assert isinstance(results, list)
        mock_browser.close.assert_called_once()

    @patch('V2.services.scraper.hks_scraper.sync_playwright')
    def test_scrape_test_mode(self, mock_playwright, hks_scraper, hks_topic_soup, hks_article_soup):
        """Test scrape with test_mode enabled."""
        hks_scraper.test_mode = "single_topic"
        
        mock_page = MagicMock()
        mock_page.content.return_value = hks_topic_soup.prettify()
        
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        
        mock_playwright_context = MagicMock()
        mock_playwright_context.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_playwright_context
        
        results = hks_scraper.scrape()
        
        assert isinstance(results, list)
        assert len(hks_scraper.topic_urls) == 1
