# Bank News

A Python pipeline that aggregates banking/fintech news from MongoDB, processes it through Yandex AI, and publishes summaries to Telegram channels.

## Overview

This project implements a three-stage pipeline:

1. **MongoDB Ingestion**: Reads articles from `results_news_telegram` collection
2. **LLM Processing**: Sends unprocessed articles to Yandex AI for fintech/banking trends analysis
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
- **Batching**: Each cron run processes available articles and sends one summary message
- **Tracking**: MongoDB documents marked with `processed: true` after successful Telegram posting
- **No Filtering**: All unprocessed articles are processed - no relevance filtering

## Installation

1. Clone or download this repository

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables:

```bash
# Copy example file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Required environment variables:
- `MONGO_URI`: MongoDB connection string
- `MONGO_USERNAME`: MongoDB username
- `MONGO_PASSWORD`: MongoDB password
- `MONGO_DATABASE`: Database name (default: `crawlab`)
- `MONGO_COLLECTION`: Collection name (default: `results_news_telegram`)
- `YAGPT_URL`: Yandex AI API URL
- `YAGPT_TOKEN`: Yandex AI API token
- `YAGPT_MODEL`: Yandex AI model name
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `TELEGRAM_CHANNEL_ID`: Telegram channel ID

Optional:
- `LLM_PROMPT`: Custom prompt for LLM (overrides default fintech trends prompt)
- `BATCH_SIZE`: Articles to process per run (default: 10)
- `DELAY_BETWEEN_REQUESTS`: Seconds between API calls (default: 2)
- `MAX_RETRIES`: Retry attempts for failed calls (default: 2)

## Usage

### Running Manually

```bash
python main.py
```

### Running with Cron (4x Daily)

To schedule automatic runs 4 times per day, add these entries to your crontab:

```bash
# Edit crontab
crontab -e

# Add these lines (runs at 6:00, 12:00, 18:00, 00:00)
0 6,12,18,0 * * * cd /path/to/bank_news && /usr/bin/python3 main.py >> logs/bank_news.log 2>&1
```

**Alternative schedules:**

Every 6 hours (4x daily at 0:00, 6:00, 12:00, 18:00):
```bash
0 */6 * * * cd /path/to/bank_news && /usr/bin/python3 main.py >> logs/bank_news.log 2>&1
```

Morning, midday, afternoon, evening:
```bash
0 6,12,15,18 * * * cd /path/to/bank_news && /usr/bin/python3 main.py >> logs/bank_news.log 2>&1
```

Make sure to:
- Replace `/path/to/bank_news` with your actual project path
- Replace `/usr/bin/python3` with your Python path (find with `which python3`)
- Create logs directory: `mkdir logs`

### Test Mode (No Telegram Sending)

To test without sending to Telegram, comment out or remove `TELEGRAM_BOT_TOKEN` from `.env` file. The script will process articles and mark them as completed but skip Telegram posting.

## Configuration

### Custom LLM Prompt

The project includes a default prompt for fintech/banking trends analysis. To use your own prompt:

1. Create or edit `.env` file
2. Add your custom prompt:
   ```
   LLM_PROMPT=Your custom prompt text here...
   ```

The prompt should include placeholders:
- `{title}` - Article title
- `{url}` - Article URL
- `{article_date}` - Article publication date
- `{content}` - Article content

### Example Custom Prompt

```bash
LLM_PROMPT=Analyze this fintech article:\n\nTitle: {title}\nURL: {url}\nDate: {article_date}\nContent: {content}\n\nCreate a brief summary highlighting key trends.
```

## Features

- **MongoDB Integration**: Reads from and updates MongoDB collections
- **Yandex AI Processing**: Analyzes articles using custom or default prompts
- **Telegram Publishing**: Posts formatted summaries to Telegram channels
- **Batch Processing**: Processes multiple articles per run
- **Error Handling**: Retries failed requests with configurable limits
- **Progress Tracking**: Marks processed articles to avoid duplicates
- **Progress Bars**: Visual feedback with tqdm
- **Long Message Splitting**: Automatically splits long messages into multiple parts
- **Logging**: Comprehensive logging for debugging

## Troubleshooting

### MongoDB Connection Issues

- Check MongoDB is running: `sudo systemctl status mongodb`
- Verify credentials in `.env` file
- Check network connectivity to MongoDB server

### Yandex AI Issues

- Verify `YAGPT_URL` is correct and accessible
- Check `YAGPT_TOKEN` is valid
- Increase `MAX_RETRIES` in `.env` if needed
- Check Yandex AI service status

### Telegram Issues

- Verify `TELEGRAM_BOT_TOKEN` is valid
- Check bot has permissions to post to the channel
- Ensure bot is a member/admin of the channel
- Verify `TELEGRAM_CHANNEL_ID` format (e.g., `-1001234567890`)

### Check Logs

```bash
# View real-time logs
tail -f logs/bank_news.log

# View recent errors
grep ERROR logs/bank_news.log | tail -n 20
```

## Development

### Project Structure

- `config.py` - Configuration management
- `mongo_yandex_telegram.py` - Main processing agent
- `main.py` - Entry point
- `requirements.txt` - Python dependencies
- `.env.example` - Configuration template
- `CLAUDE.md` - Claude Code instructions

### Running Tests

```bash
# Test without Telegram (set TELEGRAM_BOT_TOKEN= in .env or remove it)
python main.py

# Test with custom batch size
BATCH_SIZE=3 python main.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the [MIT License](LICENSE).
