"""
Configuration management for Bank News pipeline.
Loads settings from environment variables with sensible defaults.
"""

import os
from typing import Optional


class Config:
    """Configuration class for Bank News pipeline."""

    # MongoDB Configuration
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    MONGO_USERNAME: Optional[str] = os.getenv("MONGO_USERNAME")
    MONGO_PASSWORD: Optional[str] = os.getenv("MONGO_PASSWORD")
    MONGO_DATABASE: str = os.getenv("MONGO_DATABASE", "crawlab")
    MONGO_COLLECTION: str = os.getenv("MONGO_COLLECTION", "results_news_telegram")

    # Yandex AI Configuration
    YAGPT_URL: str = os.getenv("YAGPT_URL", "http://localhost:11434")
    YAGPT_TOKEN: Optional[str] = os.getenv("YAGPT_TOKEN")
    YAGPT_MODEL: str = os.getenv("YAGPT_MODEL", "/model")

    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHANNEL_ID: Optional[str] = os.getenv("TELEGRAM_CHANNEL_ID")

    # LLM Prompt Configuration
    # Priority: 1) Environment variable LLM_PROMPT, 2) Default template below
    LLM_PROMPT: Optional[str] = os.getenv("LLM_PROMPT")

    # Default prompt template for fintech/banking trends analysis
    # This focuses on FINTECH TRENDS, not AI-specific topics
    DEFAULT_LLM_PROMPT = """
Проанализируй статью о банковской и финтех индустрии и создай краткую сводку для Telegram-канала.

**Метаданные статьи:**
- Заголовок: {title}
- URL: {url}
- Дата: {article_date}

**Содержание статьи:**
{content}

**Задача:**
Создай краткую и информативную сводку в формате Markdown для публикации в Telegram-канале.

1. Кратко опиши основную тему статьи (2-3 предложения)
2. Выдели ключевые финтех тренды и их влияние на банковскую сферу
3. Не фокусируйся на ИИ (AI) - основной интерес это финтех тренды, инновации в платежах, цифровых услугах, регуляторных изменениях
4. Если статья не о финтехе - кратко опиши общий финансовый контент

**Формат ответа:**
📌 **{Заголовок статьи}**

{Краткое описание - 2-3 предложения}

💡 **Ключевые моменты:**
- • Тренд 1
- • Тренд 2
- • Тренд 3 (если применимо)

📰 Источник: {url}

**Важно:**
- Используй эмодзи для форматирования (как в примере выше)
- Будь кратким и информативным (до 200-300 слов)
- Не изобретай информацию, которой нет в статье
- Фокусируйся на финтех инновациях и банковских трендах

Верни только готовый Markdown без дополнительных комментариев.
"""

    # Processing Configuration
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "10"))  # Articles to process per run
    DELAY_BETWEEN_REQUESTS: int = int(
        os.getenv("DELAY_BETWEEN_REQUESTS", "2")
    )  # Seconds between API calls
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "2"))  # Retry attempts for failed calls

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def get_prompt(cls) -> str:
        """
        Get LLM prompt from environment variable or use default template.
        Returns the prompt to be used for Yandex AI analysis.
        """
        if cls.LLM_PROMPT and cls.LLM_PROMPT.strip():
            # Use custom prompt from environment variable (customer-provided)
            return cls.LLM_PROMPT.strip()
        else:
            # Use default fintech trends prompt
            return cls.DEFAULT_LLM_PROMPT

    @classmethod
    def validate(cls) -> bool:
        """Validate that all required configuration is present."""
        errors = []

        if not cls.MONGO_USERNAME:
            errors.append("MONGO_USERNAME is required")
        if not cls.MONGO_PASSWORD:
            errors.append("MONGO_PASSWORD is required")
        if not cls.YAGPT_TOKEN:
            errors.append("YAGPT_TOKEN is required")
        if not cls.YAGPT_URL:
            errors.append("YAGPT_URL is required")

        # Telegram is optional for testing (can skip sending)
        # if not cls.TELEGRAM_BOT_TOKEN:
        #     errors.append("TELEGRAM_BOT_TOKEN is required")
        # if not cls.TELEGRAM_CHANNEL_ID:
        #     errors.append("TELEGRAM_CHANNEL_ID is required")

        if errors:
            print("❌ Configuration errors:")
            for error in errors:
                print(f"  - {error}")
            print("\nPlease set the required environment variables in .env file")
            return False

        return True

    @classmethod
    def print_config(cls):
        """Print current configuration (without sensitive data)."""
        print("\n" + "=" * 60)
        print("Configuration:")
        print("=" * 60)
        print(f"MongoDB URI: {cls.MONGO_URI}")
        print(f"MongoDB Database: {cls.MONGO_DATABASE}")
        print(f"MongoDB Collection: {cls.MONGO_COLLECTION}")
        print(f"Yandex AI URL: {cls.YAGPT_URL}")
        print(f"Yandex AI Model: {cls.YAGPT_MODEL}")
        print(f"Telegram Bot Token: {'SET' if cls.TELEGRAM_BOT_TOKEN else 'NOT SET'}")
        print(f"Telegram Channel ID: {cls.TELEGRAM_CHANNEL_ID}")
        print(f"LLM Prompt: {'CUSTOM (from env)' if cls.LLM_PROMPT else 'DEFAULT (fintech trends)'}")
        print(f"Batch Size: {cls.BATCH_SIZE}")
        print(f"Max Retries: {cls.MAX_RETRIES}")
        print("=" * 60 + "\n")
