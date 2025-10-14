# Chatter Service

A microservice that provides interactive chat functionality using Google's Gemini API and logs conversations to the newsdb database.

## Features

- Interactive terminal interface for user questions
- Integration with Google Gemini API for AI responses
- Conversation logging to PostgreSQL database
- Error handling and graceful failure modes
- Docker containerization support

## Prerequisites

1. **Google Gemini API Key**: You need a valid API key from Google AI Studio
2. **Database Access**: Access to the newsdb PostgreSQL database
3. **Environment Variables**: Proper configuration of environment variables

## Database Schema

The service uses the `llm_conversations` table with the following schema:

```sql
CREATE TABLE llm_conversations (
    id bigint NOT NULL DEFAULT,
    user_id text NOT NULL,
    model_name text NOT NULL,
    conversation_data jsonb NOT NULL containing fields for "error", "question", and "response",
    created_at timestamp with time zone DEFAULT (now()),
    updated_at timestamp with time zone DEFAULT (now())
);
```

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
- `GEMINI_API_KEY`: Your Google Gemini API key (optional, but required for AI functionality)

## Usage

### Running with Docker Compose

The service is designed to run as part of the NewsJuice pipeline:

```bash
# From the NewsJuice-Pipeline_MS_2 directory
docker-compose run --rm chatter
```

### Running Standalone

1. **Set up environment variables**:
   ```bash
   export DATABASE_URL="postgresql://postgres:Newsjuice25%2B@host.docker.internal:5432/newsdb"
   export GEMINI_API_KEY="your_gemini_api_key_here"
   ```

2. **Install dependencies**:
   ```bash
   cd services/chatter
   uv sync
   ```

3. **Run the service**:
   ```bash
   python chatter.py
   ```

### Interactive Usage

1. The service will prompt you for a user ID
2. Enter your question when prompted
3. The service will:
   - Send your question to Google Gemini API
   - Display the AI response
   - Log the conversation to the database
4. Choose to ask another question or exit

## API Integration

### Google Gemini API

- Uses the `gemini-2.5-flash` model by default
- Handles API errors gracefully
- Falls back to error logging when API is unavailable

### Database Logging

- Automatically creates the `llm_conversations` table if it doesn't exist
- Logs all conversations with timestamps
- Stores error messages for failed API calls
- Uses PostgreSQL's JSON support for structured data

## Error Handling

The service includes comprehensive error handling for:

- Database connection failures
- Gemini API errors
- Invalid user input
- Network connectivity issues

## Development

### Project Structure

```
services/chatter/
├── Dockerfile          # Container configuration
├── pyproject.toml      # Python dependencies
├── README.md          # This file
├── chatter.py         # Main application
└── wait_for_db.py     # Database readiness check
```

### Dependencies

- `psycopg[binary]`: PostgreSQL adapter
- `google-generativeai`: Google Gemini API client
- `python-dotenv`: Environment variable management

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Ensure the Cloud SQL proxy is running
   - Verify DATABASE_URL is correctly set
   - Check network connectivity

2. **Gemini API Not Working**
   - Verify GEMINI_API_KEY is set correctly
   - Check API key permissions and quotas
   - Ensure internet connectivity

3. **Table Creation Failed**
   - Verify database permissions
   - Check for existing table conflicts

### Logs

The service provides detailed logging for:
- Database connection status
- API call results
- Error messages and stack traces
- User interaction flow

## Integration with NewsJuice Pipeline

This service integrates with the broader NewsJuice pipeline by:

- Using the same database connection pattern as other services
- Following the established Docker containerization approach
- Implementing the standard `wait_for_db.py` pattern for database readiness
- Using consistent environment variable naming conventions

## License

This project is part of the NewsJuice prototype. All rights reserved.
