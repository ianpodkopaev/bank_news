# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bank News is a Python pipeline that aggregates banking/fintech news from MongoDB, processes it through Yandex AI, and publishes summaries to Telegram channels.

## Intended Architecture

The project follows a three-stage pipeline pattern:

1. **MongoDB Ingestion**: Reads articles from `results_news_telegram` collection without filtering (all articles are processed)
2. **LLM Processing**: Sends unprocessed articles to Yandex AI for fintech/banking trends analysis (not AI-focused)
3. **Telegram Publishing**: Posts analyzed articles as summary messages to Telegram channel

### Data Flow

```
MongoDB (results_news_telegram collection)
    ↓ (unprocessed articles)
Yandex AI API
    ↓ (fintech trends analysis)
MongoDB (update with processed=true)
    ↓ (batched articles)
Telegram Bot
```

### Processing Model

- **Schedule**: 4x daily via cron jobs
- **Batching**: Each cron run processes available articles and sends ONE summary message containing multiple articles
- **Tracking**: MongoDB documents marked with `processed: true` after successful Telegram posting
- **No Deduplication**: Each article posted exactly once, tracked via `processed` field

## Reference Implementations

The codebase architecture is based on two reference scripts in `/home/confuseduser/GolandProjects/WebScrapper/`:

1. **MongoYandexConfluenseAgent.py** (`/home/confuseduser/GolandProjects/WebScrapper/moca/MongoYandexConfluenseAgent.py`)
   - MongoDB connection handling with authentication
   - Yandex AI integration via OpenAI client
   - Two-stage analysis pipeline (pre-analysis + full analysis)
   - Progress tracking with `processed` field
   - Comprehensive error handling and retries

2. **byn.py** (`/home/confuseduser/GolandProjects/WebScrapper/spiders/scrapy_belta/byn/byn.py`)
   - Similar MongoDB + Yandex AI pattern
   - JSON response parsing
   - Notification sending to external endpoints
   - Deduplication algorithms (connected components)

Both use:
- `pymongo` for MongoDB
- `openai` library (with custom base_url for Yandex)
- Environment variables for configuration
- Logging with `tqdm` progress bars

## Configuration

All configuration via environment variables (use `.env` file):
- MongoDB: `MONGO_URI`, `MONGO_USERNAME`, `MONGO_PASSWORD`, `MONGO_DATABASE`
- Yandex AI: `YAGPT_URL`, `YAGPT_TOKEN`, `YAGPT_MODEL`
- Telegram: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`
- Optional: `LLM_PROMPT` (customer-provided analysis prompt)

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the main processing script (typically called by cron)
python main.py

# Run in development mode (for testing)
python mongo_yandex_telegram.py --test

# View logs
tail -f logs/bank_news.log
```

## Key Implementation Notes

- Use OpenAI client with Yandex's base URL (format: `{YAGPT_URL}/v1`)
- MongoDB queries should look for `{ "processed": { "$ne": true } }`
- Telegram messages support Markdown formatting
- All unprocessed articles should be included - no relevance filtering
- Each cron execution sends ONE message with batch of processed articles
