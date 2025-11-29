"""
HELPER FUNCTIONS (called by main.py in chatter_deployed)
THE HELPER FUNCTIONS USED CURRENTLY ARE

1. call_retriever_service(query: str) -> List[Tuple[int, str, float]]:
===================================================================
Call the retriever service to get relevant articles.
Input: query
Returns: List of tuples: (id, chunk, score) for each matching article


2. call_gemini_api(question: str, context_articles: List[Tuple[int, str, float]] = None) ->
tuple[Optional[str], Optional[str]]:
===================================================================================================
Call Google Gemini LLM API with the question and context articles to generate a podcast-style
response.
Input: question text + tuple of relevant chunks (with id, chunk text and similarity score)
Output: tuple of response text + error message

THE HELPER FUNCTIONS NOT YET USED ARE
check_llm_conversations_table()
================================
Check if the llm_conversations table exists.
Inpùt: -
Output: TRUE if table exists, FALSE otherwise


log_conversation
================
NOT YET USED

"""

from typing import List, Tuple, Optional
import psycopg
import json
import os

# from vertexai.generative_models import GenerativeModel


# NEW should work for production and local
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise RuntimeError("DATABASE_URL environment variable not set")


def call_retriever_service(query: str) -> List[Tuple[int, str, float]]:
    """Call the retriever service to get relevant articles."""
    try:
        # Import the retriever function directly since we're in the same environment
        import sys

        sys.path.append("/app/retriever")
        from retriever import search_articles

        print(f"[retriever] Searching for: '{query[:50]}...'")
        articles = search_articles(query, limit=10)
        print(f"[retriever] Found {len(articles)} relevant chunks")
        return articles
    except Exception as e:
        print(f"[retriever-error] Error calling retriever service: {e}")
        return []


def call_gemini_api(
    question: str, context_articles: List[Tuple[int, str, float]] = None, model=None
) -> tuple[Optional[str], Optional[str]]:
    """Call Google Gemini API with the question and context articles to generate a podcast-style
    response."""
    if not model:
        return None, "Gemini API not configured"

    try:
        # Build the prompt with context if articles are provided
        if context_articles:
            context_text = "\n\n".join(
                [
                    f"News Article {i+1} (Relevance Score: {score:.3f}):\n{chunk}"
                    for i, (_, chunk, score) in enumerate(context_articles)
                ]
            )

            prompt = f"""You are NewsJuice, the AI host of a news podcast about Harvard University. Your role is to deliver factual, informative summaries based on news article chunks.

LISTENER'S QUESTION: {question}

NEWS ARTICLES TO REFERENCE:
{context_text}

YOUR TASK:
1. Synthesize the information from the news article chunks above into a clear, factual podcast segment
2. Directly answer the listener's question using specific details, numbers, and quotes from the article chunks
3. Present information authoritatively - you are delivering news, not seeking clarification
4. Structure your response with these elements:
   - OPENING: Directly state the answer to the question
   - KEY FACTS: Present the most important details with specific numbers, names, and dates
   - CONTEXT: Provide background information and explain implications
   - CLOSING: Brief summary statement (NO invitation for follow-up questions)
5. Target 500 words for a comprehensive answer
6. If the articles lack sufficient information to answer the question, state: "The latest Harvard news I have doesn't cover that topic in detail."

DELIVERY STYLE:
- Professional but conversational tone
- Use specific numbers, names, dates, and quotes from the articles
- NO collaborative phrases like "Great question!", "What do you think?", or "Let me know if you want more details"
- ABSOLUTELY NO COLLABORATIVE PHRASES LIKE "That's a great summary you provided!", or "Thank you for the information"
- NO requests for more information from the listener
- You are INFORMING, not CONVERSING

EXAMPLE STRUCTURE:
"Harvard is facing significant budget challenges this year. According to recent reports, the university posted a $113 million operating deficit in fiscal year 2025 - its first since 2020. This deficit stems from multiple factors, including the Trump administration's temporary termination of nearly all federal research grants in spring 2025, which removed approximately $116 million in sponsored funds overnight. To address these shortfalls, Harvard has implemented several cost-cutting measures: freezing salaries for non-union staff, leaving positions unfilled, and conducting targeted workforce reductions including 38 IT workers in November. The situation is compounded by a scheduled 400 percent increase in the federal endowment tax taking effect in 2027. Despite these challenges, Harvard's endowment grew 11.9 percent to $56.9 billion in fiscal 2025, which financial officers credit as central to navigating this uncertain period."

Now generate your podcast segment answering the listener's question:"""
        else:
            prompt = f"""You are a news podcast host. The user has asked: "{question}"

However, no relevant news articles were found to provide context. Please provide a thoughtful
response acknowledging this limitation and suggest how the user might find more information about
their question."""

        response = model.generate_content(prompt)
        return response.text, None
    except Exception as e:
        return None, str(e)


def check_llm_conversations_table():  # [Z] check_llm_convos is not used by our current workflow.
    # its use case is to first check if there is previous context already present to pull from for
    # our podcast generation.

    """Check if the llm_conversations table exists."""
    try:
        with psycopg.connect(DB_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'llm_conversations'
                    );
                """
                )
                exists = cur.fetchone()[0]
                if exists:
                    print("[db] llm_conversations table found")
                else:
                    print("[db-warning] llm_conversations table not found")
                return exists
    except Exception as e:
        print(f"[db-error] Failed to check table: {e}")
        raise


# [Z] log conversations is here in case we plan to insert conversations into db for context
def log_conversation(
    user_id: str,
    question: str,
    response: Optional[str],
    error_message: Optional[str],
):
    """Log the conversation to the database."""
    try:
        # Prepare conversation data as JSON
        conversation_data = {
            "question": question,
            "response": response,
            "error": error_message,
        }

        with psycopg.connect(DB_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO llm_conversations (user_id, model_name, conversation_data)
                    VALUES (%s, %s, %s);
                """,
                    (user_id, "gemini-2.5-flash", json.dumps(conversation_data)),
                )

                print("[db] Conversation logged successfully")
    except Exception as e:
        print(f"[db-error] Failed to log conversation: {e}")
