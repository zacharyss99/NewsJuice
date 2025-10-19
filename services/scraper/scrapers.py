'''
Scraper service

* Captures news from Harvard Gazette RSS feed
* Stores them in a jsonl file (news.jsonl) in the artifacts folder

News Sources: 
✅ The Harvard Gazette
    https://news.harvard.edu/gazette/feed/
✅ The Harvard Crimson
    https://www.thecrimson.com/
✅ Harvard Magazine
    https://www.harvardmagazine.com/harvard-headlines
✅ Colloquy: The alumni newsletter for the Graduate School of Arts and Sciences.
    https://gsas.harvard.edu/news/all
✅ Harvard Business School Communications Office: Publishes news and research from the business school.
    https://www.hbs.edu/news/Pages/browse.aspx?format=Article&source=Harvard%20Business%20School
✅ Harvard Law Today: The news hub for Harvard Law School.
    https://hls.harvard.edu/today/
✅ Harvard Medical School Office of Communications and External Relations - News: Disseminates news from the medical school.
    https://hms.harvard.edu/news
✅ Harvard Kennedy School
    https://www.hks.harvard.edu/news-announcements
- Harvard School of Engineering
    https://seas.harvard.edu/news


'''

import uuid
import argparse
from pathlib import Path
from gazette_scraper import GazetteArticleScraper
from crimson_scraper import CrimsonArticleScraper
from harvard_magazine_scraper import HarvardMagazineArticleScraper
from gsas_scraper import GsasArticleScraper
from hbs_scraper import HbsArticleScraper
from hls_scraper import HlsArticleScraper
from hms_scraper import HmsArticleScraper
from hks_scraper import HksArticleScraper
from seas_scraper import SeasArticleScraper
from db_manager import PostgresDBManager

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Scrape news articles')
    parser.add_argument('--out', default='artifacts/news.jsonl', help='Output file path')
    args = parser.parse_args()
    
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize database manager
    db_manager = PostgresDBManager(url_column="source_link")

    print("\nStarting Gazette Scraper")
    gazzet_scraper = GazetteArticleScraper(test_mode=False)
    gazzet_details = gazzet_scraper.scrape()

    print("\nStarting Crimson Scraper")
    crimson_scraper = CrimsonArticleScraper(headless=True, test_mode=False, wait_ms=1000)
    crimson_details = crimson_scraper.scrape()

    print("\nStarting Harvard Magazine Scraper")
    harvard_magazine_scraper = HarvardMagazineArticleScraper(headless=True, test_mode=False, wait_ms=1000)
    harvard_magazine_details = harvard_magazine_scraper.scrape()  

    print("\nGSAS News Scraper")
    gsas_news_scraper = GsasArticleScraper(headless=True, test_mode=False, wait_ms=1000)
    gsas_news_details = gsas_news_scraper.scrape()  

    print("\nHBS  News Scraper")
    hbs_news_scraper = HbsArticleScraper(headless=True, test_mode=False, wait_ms=1000)
    hbs_news_details = hbs_news_scraper.scrape()
        
    print("\nHLS  News Scraper")
    hls_news_scraper = HlsArticleScraper(headless=True, test_mode=False, wait_ms=1000)
    hls_news_details = hls_news_scraper.scrape()

    print("\nHMS  News Scraper")
    hms_news_scraper = HmsArticleScraper(headless=True, test_mode=False, wait_ms=1000)
    hms_news_details = hms_news_scraper.scrape()

    print("\nHKS  News Scraper")
    hks_news_scraper = HksArticleScraper(headless=True, test_mode=False, wait_ms=1000)
    hks_news_details = hks_news_scraper.scrape()

    print("\nSEAS  News Scraper")
    seas_news_scraper = SeasArticleScraper(headless=True, test_mode=False, wait_ms=1000)
    seas_news_details = seas_news_scraper.scrape()

    all_articles = [
                    *gazzet_details,
                    *crimson_details,
                    *harvard_magazine_details,
                    *gsas_news_details,
                    *hbs_news_details,
                    *hls_news_details,
                    *hms_news_details,
                    *hks_news_details,
                    *seas_news_details
                    ]
    
    # Map scraper field names to database column names
    db_records = []
    for article in all_articles:
        db_record = {
            "author": article.get("article_author", ""),
            "title": article.get("article_title", ""),
            "summary": article.get("summary", ""),
            "content": article.get("article_content", ""),
            "source_link": article.get("article_url", ""),
            "source_type": article.get("source_type", ""),
            "fetched_at": article.get("fetched_at"),
            "published_at": article.get("article_publish_date"),
            "vflag": 0,  # 0 = new/unprocessed
            "article_id": str(uuid.uuid4()),  # Generate unique ID
        }
        db_records.append(db_record)
    
    # Insert into database
    inserted_count = db_manager.insert_records(db_records)
    print(f"\n✅ Inserted {inserted_count} new articles into the database.")
    print(f"Total articles scraped: {len(all_articles)}")
    print(f"Skipped (already in DB): {len(all_articles) - inserted_count}")
    
    # # Optional: still write to JSONL for backup
    # with out.open("w", encoding="utf-8") as f:
    #     for article in all_articles:
    #         f.write(json.dumps(article, ensure_ascii=False) + "\n")    


if __name__ == "__main__":
    main()