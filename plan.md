  ## Plan: MongoDB → Yandex AI → Telegram Pipeline (4x Daily)

  ### Program Structure

  Create `mongo_yandex_telegram.py` based on the reference files:

  1. **Data Flow**
     - Read ALL articles from MongoDB collection: `results_news_telegram`
     - No filtering by relevance/categories - process everything
     - Mark articles as `processed: true` after sending to Telegram

  2. **LLM Processing**
     - Send articles to Yandex AI for fintech/banking trends analysis
     - Use customer-provided prompt (will be provided later)
     - Focus on fintech trends, not AI
     - Process in batches based on cron schedule

  3. **Telegram Integration**
     - Script runs 4x daily via cron
     - **Each run sends 1 summary message** containing multiple articles
     - Format: Article title, brief summary, link to source
     - Total: 4 Telegram messages per day (1 per cron run)

  4. **Files to Create**
     - `mongo_yandex_telegram.py` - Main processing script
     - `requirements.txt` - Dependencies (pymongo, python-telegram-bot, openai)
     - `.env.example` - Configuration template
     - `config.py` - Configuration management
     - `README.md` - Setup instructions with cron examples
     - `main.py` - Entry point

  5. **Configuration (via environment variables)**
     - MongoDB: URI, username, password, database
     - Yandex AI: URL, token, model
     - Telegram: Bot token (placeholder), channel ID (placeholder)
     - Optional: Customer prompt for LLM

  6. **Cron Schedule (4x daily)**
     - Examples: 6:00, 12:00, 18:00, 00:00 (or custom times)

  ### Key Features
  - Batch processing per cron run
  - Error handling with retries
  - Markdown/HTML formatting for Telegram
  - Progress tracking in MongoDB
  - Comprehensive logging

