import pytest
import os
from bs4 import BeautifulSoup
from unittest.mock import patch, MagicMock
from ..hms_scraper import HmsArticleScraper

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture(scope="session")
def hms_article_soup():
    """Provides a BeautifulSoup object from a saved HMS article HTML file."""
    file_path = os.path.join(_TEST_DIR, "Saved_pages/HMS_sample_article.html")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return BeautifulSoup(f.read(), "html.parser")
    except FileNotFoundError:
        pytest.fail(f"Test requires 'HMS_sample_article.html' in the test directory: {file_path}")

@pytest.fixture(scope="session")
def hms_topic_soup():
    """Provides a BeautifulSoup object from a saved HMS topic page HTML file."""
    file_path = os.path.join(_TEST_DIR, "Saved_pages/HMS_sample_topic_page.html")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return BeautifulSoup(f.read(), "html.parser")
    except FileNotFoundError:
        pytest.fail(f"Test requires 'HMS_sample_topic_page.html' in the test directory: {file_path}")

@pytest.fixture
def hms_scraper():
    """Provides a default instance of the HMS scraper for testing."""
    with patch('V2.services.scraper.hms_scraper.PostgresDBManager') as MockDBManager:
        mock_db_instance = MockDBManager.return_value
        mock_db_instance.filter_new_urls.return_value = []
        scraper_instance = HmsArticleScraper(headless=True, test_mode=False)
        scraper_instance.db_manager = mock_db_instance
        yield scraper_instance

class TestHmsArticleScraper:

    def test_extract_article_links(self, hms_scraper, hms_topic_soup):
        """Verify that article links are correctly extracted from a topic page."""
        links = hms_scraper.extract_article_links(hms_topic_soup)
        assert isinstance(links, list)

    def test_extract_article_content(self, hms_scraper, hms_article_soup):
        """Verify content extraction from a sample article."""
        content = hms_scraper.extract_article_content(hms_article_soup)
        if content:
            assert isinstance(content, str)
            assert len(content) > 50

    def test_extract_article_content_missing(self, hms_scraper):
        """Test content extraction when the main content div is missing."""
        soup = BeautifulSoup('<div>No content</div>', 'html.parser')
        content = hms_scraper.extract_article_content(soup)
        assert content is None

    def test_extract_article_title(self, hms_scraper, hms_article_soup):
        """Verify title extraction from a sample article."""
        title = hms_scraper.extract_article_title(hms_article_soup)
        if title:
            assert isinstance(title, str)
            assert len(title) > 5

    def test_extract_article_author(self, hms_scraper, hms_article_soup):
        """Verify author extraction from a sample article."""
        author = hms_scraper.extract_article_author(hms_article_soup)
        if author is not None:
            assert isinstance(author, str)

    def test_extract_article_author_with_by_prefix(self, hms_scraper):
        """Test author extraction when text starts with 'by '."""
        html = '''
        <span class="article-author field__item">
            By Jane Smith
        </span>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        author = hms_scraper.extract_article_author(soup)
        assert author == "Jane Smith"

    def test_extract_article_author_missing(self, hms_scraper):
        """Test author extraction when author span is missing."""
        soup = BeautifulSoup('<div>No author</div>', 'html.parser')
        author = hms_scraper.extract_article_author(soup)
        assert author is None

    def test_extract_article_publish_date(self, hms_scraper, hms_article_soup):
        """Verify date parsing and formatting."""
        publish_date = hms_scraper.extract_article_publish_date(hms_article_soup)
        if publish_date:
            assert isinstance(publish_date, str)
            assert 'T' in publish_date

    def test_extract_publish_date_missing(self, hms_scraper):
        """Test date extraction when the date span is missing."""
        soup = BeautifulSoup('<div>No date</div>', 'html.parser')
        date = hms_scraper.extract_article_publish_date(soup)
        assert date is None

    @patch('V2.services.scraper.hms_scraper.dateparser.parse', return_value=None)
    def test_extract_publish_date_parse_fails(self, mock_parse, hms_scraper, hms_article_soup):
        """Test date extraction when dateparser fails to parse."""
        date = hms_scraper.extract_article_publish_date(hms_article_soup)
        assert date is None

    @patch('V2.services.scraper.hms_scraper.dateparser.parse', side_effect=Exception("Parsing failed"))
    def test_extract_publish_date_exception(self, mock_parse, hms_scraper, hms_article_soup):
        """Test date extraction when dateparser raises an exception."""
        date = hms_scraper.extract_article_publish_date(hms_article_soup)
        assert date is None

    def test_fetched_at_date_formatted(self, hms_scraper):
        """Ensure fetched_at returns a valid ISO-formatted UTC string."""
        fetched_date = hms_scraper.fetched_at_date_formatted()
        assert isinstance(fetched_date, str)
        assert 'T' in fetched_date
        assert fetched_date.endswith('+00:00')

    @patch('V2.services.scraper.hms_scraper.sync_playwright')
    def test_scrape_flow(self, mock_playwright, hms_scraper, hms_topic_soup, hms_article_soup):
        """Test the main scrape orchestration with mocked browser interactions."""
        mock_page = MagicMock()
        mock_page.content.side_effect = [hms_topic_soup.prettify(), hms_article_soup.prettify()]
        
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        
        mock_playwright_context = MagicMock()
        mock_playwright_context.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_playwright_context
        
        test_url = "https://hms.harvard.edu/news/test-article"
        hms_scraper.db_manager.filter_new_urls.return_value = [test_url]
        hms_scraper.topic_urls = ["http://fake-topic-url.com"]
        
        results = hms_scraper.scrape()
        
        assert isinstance(results, list)
        mock_browser.close.assert_called_once()

    @patch('V2.services.scraper.hms_scraper.sync_playwright')
    def test_scrape_test_mode(self, mock_playwright, hms_scraper, hms_topic_soup, hms_article_soup):
        """Test scrape with test_mode enabled."""
        hms_scraper.test_mode = "single_topic"
        
        mock_page = MagicMock()
        mock_page.content.return_value = hms_topic_soup.prettify()
        
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        
        mock_playwright_context = MagicMock()
        mock_playwright_context.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_playwright_context
        
        results = hms_scraper.scrape()
        
        assert isinstance(results, list)
        assert len(hms_scraper.topic_urls) == 1
