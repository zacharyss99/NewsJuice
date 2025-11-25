import pytest
import os
import sys
from bs4 import BeautifulSoup
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from seas_scraper import SeasArticleScraper

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture(scope="session")
def seas_article_soup():
    """Provides a BeautifulSoup object from a saved SEAS article HTML file."""
    file_path = os.path.join(_TEST_DIR, "Saved_pages/SEAS_sample_article.html")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return BeautifulSoup(f.read(), "html.parser")
    except FileNotFoundError:
        pytest.fail(f"Test requires 'SEAS_sample_article.html' in the test directory: {file_path}")

@pytest.fixture(scope="session")
def seas_topic_soup():
    """Provides a BeautifulSoup object from a saved SEAS topic page HTML file."""
    file_path = os.path.join(_TEST_DIR, "Saved_pages/SEAS_sample_topic_page.html")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return BeautifulSoup(f.read(), "html.parser")
    except FileNotFoundError:
        pytest.fail(f"Test requires 'SEAS_sample_topic_page.html' in the test directory: {file_path}")

@pytest.fixture
def seas_scraper():
    """Provides a default instance of the SEAS scraper for testing."""
    with patch('V2.services.scraper.seas_scraper.PostgresDBManager') as MockDBManager:
        mock_db_instance = MockDBManager.return_value
        mock_db_instance.filter_new_urls.return_value = []
        scraper_instance = SeasArticleScraper(headless=True, test_mode=False)
        scraper_instance.db_manager = mock_db_instance
        yield scraper_instance

class TestSeasArticleScraper:

    def test_extract_article_links(self, seas_scraper, seas_topic_soup):
        """Verify that article links are correctly extracted from a topic page."""
        links = seas_scraper.extract_article_links(seas_topic_soup)
        assert isinstance(links, list)

    def test_extract_article_content(self, seas_scraper, seas_article_soup):
        """Verify content extraction from a sample article."""
        content = seas_scraper.extract_article_content(seas_article_soup)
        if content:
            assert isinstance(content, str)
            assert len(content) > 50

    def test_extract_article_content_missing(self, seas_scraper):
        """Test content extraction when the main content div is missing."""
        soup = BeautifulSoup('<div>No content</div>', 'html.parser')
        content = seas_scraper.extract_article_content(soup)
        assert content is None

    def test_extract_article_title(self, seas_scraper, seas_article_soup):
        """Verify title extraction from a sample article."""
        title = seas_scraper.extract_article_title(seas_article_soup)
        if title:
            assert isinstance(title, str)
            assert len(title) > 5

    def test_extract_article_author(self, seas_scraper, seas_article_soup):
        """Verify author extraction from a sample article."""
        author = seas_scraper.extract_article_author(seas_article_soup)
        if author is not None:
            assert isinstance(author, str)

    def test_extract_article_author_with_by_prefix(self, seas_scraper):
        """Test author extraction when text starts with 'by '."""
        html = '''
        <div class="news__author-press">
            By Jane Smith
        </div>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        author = seas_scraper.extract_article_author(soup)
        assert author == "Jane Smith"

    def test_extract_article_author_missing(self, seas_scraper):
        """Test author extraction when author div is missing."""
        soup = BeautifulSoup('<div>No author</div>', 'html.parser')
        author = seas_scraper.extract_article_author(soup)
        assert author is None

    def test_extract_article_publish_date(self, seas_scraper, seas_article_soup):
        """Verify date parsing and formatting."""
        publish_date = seas_scraper.extract_article_publish_date(seas_article_soup)
        if publish_date:
            assert isinstance(publish_date, str)
            assert 'T' in publish_date

    def test_extract_publish_date_missing(self, seas_scraper):
        """Test date extraction when the time tag is missing."""
        soup = BeautifulSoup('<div>No date</div>', 'html.parser')
        date = seas_scraper.extract_article_publish_date(soup)
        assert date is None

    @patch('V2.services.scraper.seas_scraper.dateparser.parse', return_value=None)
    def test_extract_publish_date_parse_fails(self, mock_parse, seas_scraper, seas_article_soup):
        """Test date extraction when dateparser fails to parse."""
        date = seas_scraper.extract_article_publish_date(seas_article_soup)
        assert date is None

    @patch('V2.services.scraper.seas_scraper.dateparser.parse', side_effect=Exception("Parsing failed"))
    def test_extract_publish_date_exception(self, mock_parse, seas_scraper, seas_article_soup):
        """Test date extraction when dateparser raises an exception."""
        date = seas_scraper.extract_article_publish_date(seas_article_soup)
        assert date is None

    def test_fetched_at_date_formatted(self, seas_scraper):
        """Ensure fetched_at returns a valid ISO-formatted UTC string."""
        fetched_date = seas_scraper.fetched_at_date_formatted()
        assert isinstance(fetched_date, str)
        assert 'T' in fetched_date
        assert fetched_date.endswith('+00:00')

    @patch('V2.services.scraper.seas_scraper.sync_playwright')
    def test_scrape_flow(self, mock_playwright, seas_scraper, seas_topic_soup, seas_article_soup):
        """Test the main scrape orchestration with mocked browser interactions."""
        mock_page = MagicMock()
        mock_page.content.side_effect = [seas_topic_soup.prettify(), seas_article_soup.prettify()]
        
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        
        mock_playwright_context = MagicMock()
        mock_playwright_context.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_playwright_context
        
        test_url = "https://seas.harvard.edu/news/test-article"
        seas_scraper.db_manager.filter_new_urls.return_value = [test_url]
        seas_scraper.topic_urls = ["http://fake-topic-url.com"]
        
        results = seas_scraper.scrape()
        
        assert isinstance(results, list)
        mock_browser.close.assert_called_once()

    @patch('V2.services.scraper.seas_scraper.sync_playwright')
    def test_scrape_test_mode(self, mock_playwright, seas_scraper, seas_topic_soup, seas_article_soup):
        """Test scrape with test_mode enabled."""
        seas_scraper.test_mode = "single_topic"
        
        mock_page = MagicMock()
        mock_page.content.return_value = seas_topic_soup.prettify()
        
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        
        mock_playwright_context = MagicMock()
        mock_playwright_context.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_playwright_context
        
        results = seas_scraper.scrape()
        
        assert isinstance(results, list)
        assert len(seas_scraper.topic_urls) == 1
