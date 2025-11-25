import pytest
import os
import sys
from bs4 import BeautifulSoup
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from crimson_scraper import CrimsonArticleScraper

# ----------------- Test Data Setup -----------------
# Instructions:
# 1. Save the HTML of a Crimson article page as 'sample_article.html' in this directory.
# 2. Save the HTML of a Crimson section/topic page as 'sample_topic_page.html'.

# Helper to get the absolute path for test files
_TEST_DIR = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture(scope="session")
def article_soup():
    """Provides a BeautifulSoup object from a saved article HTML file."""
    file_path = os.path.join(_TEST_DIR, "Saved_pages/Crimson_sample_article.html")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return BeautifulSoup(f.read(), "html.parser")
    except FileNotFoundError:
        pytest.fail(f"Test requires 'Crimson_sample_article.html' in the test directory: {file_path}")

@pytest.fixture(scope="session")
def topic_soup():
    """Provides a BeautifulSoup object from a saved topic page HTML file."""
    file_path = os.path.join(_TEST_DIR, "Saved_pages/Crimson_sample_topic_page.html")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return BeautifulSoup(f.read(), "html.parser")
    except FileNotFoundError:
        pytest.fail(f"Test requires 'Crimson_sample_topic_page.html' in the test directory: {file_path}")

# Fixtures for edge cases
@pytest.fixture(scope="session")
def soup_no_content():
    return BeautifulSoup('<div><p>no content div</p></div>', 'html.parser')

@pytest.fixture(scope="session")
def soup_alt_title_author():
    return BeautifulSoup('<h1 class="css-1rfyg0l">Alt Title</h1><span class="css-x0hxbi">Alt Author</span>', 'html.parser')

@pytest.fixture(scope="session")
def soup_no_date():
    return BeautifulSoup('<div>No time tag</div>', 'html.parser')


@pytest.fixture
def scraper():
    """Provides a default instance of the scraper for testing."""
    # Mock the DB manager to avoid actual DB calls
    with patch('V2.services.scraper.crimson_scraper.PostgresDBManager') as MockDBManager:
        # Configure the mock instance returned by the constructor
        mock_db_instance = MockDBManager.return_value
        mock_db_instance.filter_new_urls.return_value = [] # Assume all URLs are new

        # Instantiate the scraper
        scraper_instance = CrimsonArticleScraper(headless=True)
        scraper_instance.db_manager = mock_db_instance
        yield scraper_instance

class TestCrimsonArticleScraper:

    def test_extract_article_links(self, scraper, topic_soup):
        """Verify that article links are correctly extracted from a topic page."""
        links = scraper.extract_article_links(topic_soup)
        assert isinstance(links, list)
        # Add more specific assertions, e.g., check if a known link is present
        # assert "/article/2023/1/1/some-known-article/" in links

    def test_extract_article_content(self, scraper, article_soup):
        """Verify content extraction from a sample article."""
        content = scraper.extract_article_content(article_soup)
        assert isinstance(content, str)
        assert len(content) > 100 # Check for substantial content

    def test_extract_article_title(self, scraper, article_soup):
        """Verify title extraction from a sample article."""
        title = scraper.extract_article_title(article_soup)
        assert isinstance(title, str)
        assert len(title) > 5

    def test_extract_article_author(self, scraper, article_soup):
        """Verify author extraction from a sample article."""
        author = scraper.extract_article_author(article_soup)
        assert isinstance(author, str)

    def test_extract_article_publish_date(self, scraper, article_soup):
        """Verify date parsing and formatting."""
        publish_date = scraper.extract_article_publish_date(article_soup)
        assert isinstance(publish_date, str) # Should be ISO format
        assert 'T' in publish_date
        assert publish_date.endswith('Z') or publish_date.endswith('+00:00')

    def test_fetched_at_date_formatted(self, scraper):
        """Ensure fetched_at returns a valid ISO-formatted UTC string."""
        fetched_date = scraper.fetched_at_date_formatted()
        assert isinstance(fetched_date, str)
        assert 'T' in fetched_date and fetched_date.endswith('+00:00')

    # New tests for increased coverage
    def test_extract_content_missing(self, scraper, soup_no_content):
        """Test content extraction when the main content div is missing."""
        content = scraper.extract_article_content(soup_no_content)
        assert content is None

    def test_extract_alt_title_author(self, scraper, soup_alt_title_author):
        """Test extraction of alternate title and author classes."""
        title = scraper.extract_article_title(soup_alt_title_author)
        author = scraper.extract_article_author(soup_alt_title_author)
        assert title == "Alt Title"
        assert author == "Alt Author"

    def test_extract_publish_date_missing(self, scraper, soup_no_date):
        """Test date extraction when the time tag is missing."""
        date = scraper.extract_article_publish_date(soup_no_date)
        assert date is None

    @patch('V2.services.scraper.crimson_scraper.dateparser.parse', return_value=None)
    def test_extract_publish_date_parse_fails(self, mock_parse, scraper, article_soup):
        """Test date extraction when dateparser fails to parse."""
        date = scraper.extract_article_publish_date(article_soup)
        assert date is None

    @patch('V2.services.scraper.crimson_scraper.dateparser.parse', side_effect=Exception("Parsing failed"))
    def test_extract_publish_date_exception(self, mock_parse, scraper, article_soup):
        """Test date extraction when dateparser raises an exception."""
        date = scraper.extract_article_publish_date(article_soup)
        assert date is None

    @patch('V2.services.scraper.crimson_scraper.sync_playwright')
    def test_scrape_flow(self, mock_playwright, scraper, topic_soup, article_soup):
        """Test the main scrape orchestration with mocked browser interactions."""
        # --- Setup Mocks ---
        mock_page = MagicMock()
        # Mock page.content() to return different HTML for topic and article pages
        mock_page.content.side_effect = [topic_soup.prettify(), article_soup.prettify()]

        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page

        mock_playwright_context = MagicMock()
        mock_playwright_context.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_playwright_context

        # Mock the DB filter to return one new URL
        test_url = "https://www.thecrimson.com/article/1234/1/1/test/"
        scraper.db_manager.filter_new_urls.return_value = [test_url]

        # --- Run Scrape ---
        # Limit to one topic to simplify the test
        scraper.topic_urls = ["http://fake-topic-url.com"]
        results = scraper.scrape()

        # --- Assertions ---
        assert len(results) == 1
        assert results[0]["article_url"] == test_url
        assert results[0]["article_title"] is not None

        # Verify browser interactions
        mock_page.goto.assert_called()
        mock_browser.close.assert_called_once()

    @patch('V2.services.scraper.crimson_scraper.sync_playwright')
    def test_scrape_flow_test_mode(self, mock_playwright, scraper, topic_soup, article_soup):
        """Test the scrape method's behavior with test_mode='single_topic'."""
        # --- Setup Mocks ---
        mock_page = MagicMock()
        mock_page.content.side_effect = [topic_soup.prettify(), article_soup.prettify()]

        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page

        mock_playwright_context = MagicMock()
        mock_playwright_context.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__enter__.return_value = mock_playwright_context

        # --- Run Scrape in test_mode ---
        scraper.test_mode = "single_topic"
        scraper.db_manager.filter_new_urls.return_value = ["https://www.thecrimson.com/article/123"]
        results = scraper.scrape()

        # --- Assertions ---
        # Assert that goto was called for the topic page and the article page
        assert mock_page.goto.call_count == 2
        calls = mock_page.goto.call_args_list
        assert calls[0].args[0] == "https://www.thecrimson.com/section/news/"
        assert calls[1].args[0] == "https://www.thecrimson.com/article/123"
        assert len(results) == 1
