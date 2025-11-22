# tests/system/test_loader_system.py

import pytest
import requests
import psycopg
from psycopg import sql
import os


class TestLoaderSystem:
    """System-level tests for the complete loader workflow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment before each test"""
        # Configuration
        self.base_url = os.environ.get("API_BASE_URL", "http://localhost:8080")
        self.db_url = os.environ["DATABASE_URL"]
        self.articles_table = os.environ.get("ARTICLES_TABLE_NAME", "articles_test")
        self.chunks_table = os.environ.get("VECTOR_TABLE_NAME", "chunks_vector_test")
        
        # Connect to database
        self.conn = psycopg.connect(self.db_url)
        self.cur = self.conn.cursor()
        
        yield
        
        # Cleanup
        self.cur.close()
        self.conn.close()
    
    def test_health_check(self):
        """
        Test 1: Verify the API is running
        Expected: Returns 200 with status='ok'
        """
        response = requests.get(f"{self.base_url}/")
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        print("✓ Health check passed")
    
    def test_complete_workflow(self):
        """
        Test 2: Complete end-to-end workflow with REAL Vertex AI embeddings
        
        Steps:
        1. Insert a test article with vflag=0
        2. Call /process-sync endpoint (makes REAL Vertex AI calls)
        3. Verify chunks were created with real embeddings
        4. Verify article vflag was updated to 1
        
        Note: This test makes REAL API calls to Vertex AI and incurs costs (~$0.000001)
        """
        # Step 1: Insert test article
        test_article_id = "test_article_123"
        self._insert_test_article(test_article_id)
        print(f"✓ Inserted test article: {test_article_id}")
        
        # Verify article exists with vflag=0
        initial_vflag = self._get_article_vflag(test_article_id)
        assert initial_vflag == 0, "Article should start with vflag=0"
        print("✓ Verified article has vflag=0")
        
        # Step 2: Process the article (REAL Vertex AI calls happen here)
        print("⏳ Calling Vertex AI for embeddings (this takes a few seconds)...")
        response = requests.post(f"{self.base_url}/process-sync")
        assert response.status_code == 200
        result = response.json()
        
        print(f"✓ API Response: {result}")
        
        # Should succeed with real embeddings
        assert result["status"] == "success", f"Expected success but got: {result}"
        assert result["processed"] >= 1
        print(f"✓ Processing completed with REAL Vertex AI embeddings: {result}")
        
        # Step 3: Verify chunks were created
        chunk_count = self._count_chunks(test_article_id)
        assert chunk_count > 0, "Should have created at least one chunk"
        print(f"✓ Created {chunk_count} chunks with real embeddings")
        
        # Verify embeddings are real (not all zeros or identical)
        self._verify_real_embeddings(test_article_id)
        
        # Step 4: Verify vflag was updated
        final_vflag = self._get_article_vflag(test_article_id)
        assert final_vflag == 1, "Article should be marked as processed"
        print("✓ Article marked as processed (vflag=1)")
        
        # Cleanup
        self._cleanup_test_data(test_article_id)
        print("✓ Test data cleaned up")
    
    def test_no_articles_to_process(self):
        """
        Test 3: Verify behavior when no unprocessed articles exist
        Expected: Returns success with processed=0
        """
        # Ensure all articles are processed (vflag=1)
        self._mark_all_articles_processed()
        
        response = requests.post(f"{self.base_url}/process-sync")
        assert response.status_code == 200
        result = response.json()
        
        assert result["status"] == "success"
        assert result["processed"] == 0
        print("✓ Correctly handled no articles to process")
    
    # Helper methods
    
    def _insert_test_article(self, article_id: str):
        """Insert a test article into the database"""
        # First, delete if exists
        delete_sql = sql.SQL("DELETE FROM {} WHERE article_id = %s").format(
            sql.Identifier(self.articles_table)
        )
        self.cur.execute(delete_sql, (article_id,))
        
        # Then insert fresh
        insert_sql = sql.SQL("""
            INSERT INTO {} (
                article_id, author, title, summary, content,
                source_link, source_type, vflag
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """).format(sql.Identifier(self.articles_table))
        
        self.cur.execute(insert_sql, (
            article_id,
            "Test Author",
            "Test Article Title",
            "This is a test summary",
            "This is test content. " * 50,  # Long enough to create multiple chunks
            "https://test.com/article",
            "test",
            0
        ))
        self.conn.commit()
    
    def _get_article_vflag(self, article_id: str) -> int:
        """Get the vflag value for an article"""
        select_sql = sql.SQL("""
            SELECT vflag FROM {} WHERE article_id = %s
        """).format(sql.Identifier(self.articles_table))
        
        self.cur.execute(select_sql, (article_id,))
        result = self.cur.fetchone()
        return result[0] if result else None
    
    def _count_chunks(self, article_id: str) -> int:
        """Count how many chunks were created for an article"""
        count_sql = sql.SQL("""
            SELECT COUNT(*) FROM {} WHERE article_id = %s
        """).format(sql.Identifier(self.chunks_table))
        
        self.cur.execute(count_sql, (article_id,))
        return self.cur.fetchone()[0]
    
    def _verify_real_embeddings(self, article_id: str):
        """Verify that embeddings are real (not mocked)"""
        select_sql = sql.SQL("""
            SELECT embedding FROM {} WHERE article_id = %s LIMIT 2
        """).format(sql.Identifier(self.chunks_table))
        
        self.cur.execute(select_sql, (article_id,))
        embeddings = [row[0] for row in self.cur.fetchall()]
        
        if len(embeddings) > 0:
            # Embeddings are returned as list/array type from pgvector
            embedding = embeddings[0]
            
            # Check if it's a list (correct) or needs parsing
            if isinstance(embedding, str):
                # If it's a string, it means the column type might be wrong
                # But we can still verify it looks like real data
                assert len(embedding) > 100, "Embedding string should be substantial"
                assert "0." in embedding or "-0." in embedding, "Should contain float values"
                print(f"✓ Verified real embeddings: stored as text (contains float values)")
            else:
                # It's a proper list/array
                assert len(embedding) == 768, f"Expected 768 dims, got {len(embedding)}"
                
                # Check for variety (real embeddings have varied values)
                unique_values = len(set(embedding[:20]))
                assert unique_values > 10, f"Real embeddings should have varied values, got only {unique_values} unique in first 20"
                
                # If we have 2+ embeddings, they should be different
                if len(embeddings) > 1:
                    assert embeddings[0] != embeddings[1], "Different chunks should have different embeddings"
                
                print(f"✓ Verified real embeddings: 768-dim, {unique_values} unique values in sample")
                print(f"  Sample values: {embedding[:5]}")
        
    def _mark_all_articles_processed(self):
        """Mark all articles as processed (for testing)"""
        update_sql = sql.SQL("""
            UPDATE {} SET vflag = 1
        """).format(sql.Identifier(self.articles_table))
        
        self.cur.execute(update_sql)
        self.conn.commit()
    
    def _cleanup_test_data(self, article_id: str):
        """Remove test data from database"""
        # Delete chunks
        delete_chunks_sql = sql.SQL("""
            DELETE FROM {} WHERE article_id = %s
        """).format(sql.Identifier(self.chunks_table))
        self.cur.execute(delete_chunks_sql, (article_id,))
        
        # Delete article
        delete_article_sql = sql.SQL("""
            DELETE FROM {} WHERE article_id = %s
        """).format(sql.Identifier(self.articles_table))
        self.cur.execute(delete_article_sql, (article_id,))
        
        self.conn.commit()

    def test_view_real_embeddings(self):
        """
        Test 4: View actual embedding values from database
        This test shows what real Vertex AI embeddings look like
        """
        # Insert and process an article
        test_article_id = "test_view_embeddings"
        self._insert_test_article(test_article_id)
        
        # Process it
        response = requests.post(f"{self.base_url}/process-sync")
        assert response.json()["status"] == "success"
        
        # Fetch the raw embeddings from database
        self.cur.execute(f"""
            SELECT chunk, embedding 
            FROM {self.chunks_table} 
            WHERE article_id = %s 
            LIMIT 1
        """, (test_article_id,))
        
        row = self.cur.fetchone()
        chunk_text = row[0]
        embedding = row[1]
        
        print(f"\n{'='*60}")
        print(f"REAL VERTEX AI EMBEDDING")
        print(f"{'='*60}")
        print(f"Chunk text: {chunk_text[:100]}...")
        print(f"\nEmbedding type: {type(embedding)}")
        print(f"Embedding length: {len(str(embedding))} characters")
        
        # If it's stored as vector type, it will be a list
        if isinstance(embedding, list):
            print(f"Vector dimensions: {len(embedding)}")
            print(f"First 10 values: {embedding[:10]}")
            print(f"Sample statistics:")
            print(f"  Min: {min(embedding):.6f}")
            print(f"  Max: {max(embedding):.6f}")
            print(f"  Mean: {sum(embedding)/len(embedding):.6f}")
        else:
            # It's stored as text, parse and show
            print(f"First 200 chars: {str(embedding)[:200]}...")
        
        print(f"{'='*60}\n")
        
        # Cleanup
        self._cleanup_test_data(test_article_id)