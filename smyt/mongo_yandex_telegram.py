"""
MongoDB → Yandex AI → Telegram Pipeline
Processes banking/fintech news articles and publishes to Telegram channel.
"""

import os
import asyncio
from pathlib import Path
from bson import ObjectId
import pymongo
import logging
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from telegram import Bot
from telegram.error import TelegramError
from tqdm import tqdm

# Import configuration
from config import Config


# Load .env file if it exists
def load_env_file():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)
        print(f"✅ Loaded environment variables from {env_path}")
    else:
        print(f"⚠️  No .env file found at {env_path}")
        print(f"   Please copy .env.example to .env and configure")


load_env_file()


class MongoYandexTelegramAgent:
    """Agent for processing MongoDB articles through Yandex AI and sending to Telegram."""

    def __init__(self):
        """Initialize the agent with MongoDB, Yandex AI, and Telegram connections."""
        self.setup_logging()

        # Initialize MongoDB client
        mongo_config = {
            "uri": Config.MONGO_URI,
            "database": Config.MONGO_DATABASE,
            "collection": Config.MONGO_COLLECTION,
            "username": Config.MONGO_USERNAME,
            "password": Config.MONGO_PASSWORD,
        }

        if mongo_config["username"] and mongo_config["password"]:
            self.mongo_client = pymongo.MongoClient(
                mongo_config["uri"],
                username=mongo_config["username"],
                password=mongo_config["password"],
            )
        else:
            self.mongo_client = pymongo.MongoClient(mongo_config["uri"])

        self.db = self.mongo_client[mongo_config["database"]]
        self.collection = self.db[mongo_config["collection"]]

        # Test MongoDB connection
        try:
            self.mongo_client.admin.command("ping")
            self.logger.info(
                f"MongoDB connection successful to {mongo_config['uri']}"
            )
        except Exception as e:
            self.logger.error(f"MongoDB connection failed: {e}")
            raise

        # Initialize Yandex AI client
        self.yagpt_url = Config.YAGPT_URL
        self.yagpt_token = Config.YAGPT_TOKEN
        self.yagpt_model = Config.YAGPT_MODEL

        # Initialize Telegram bot (optional for testing)
        self.telegram_bot: Optional[Bot] = None
        if Config.TELEGRAM_BOT_TOKEN:
            try:
                self.telegram_bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
                self.logger.info("✅ Telegram bot initialized")
            except Exception as e:
                self.logger.warning(f"⚠️  Failed to initialize Telegram bot: {e}")
                self.logger.warning("   Will run in test mode (no Telegram sending)")

        self.logger.info("MongoYandexTelegramAgent initialized")

    def setup_logging(self):
        """Configure logging."""
        log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def get_unprocessed_articles(self, limit: int = None) -> List[Dict]:
        """Get unprocessed articles from MongoDB.

        Args:
            limit: Maximum number of articles to retrieve (None for all)

        Returns:
            List of unprocessed articles
        """
        query = {
            "$or": [
                {"processed": {"$exists": False}},
                {"processed": False},
                {"processed": {"$eq": None}},
            ]
        }

        # Get total count
        total_unprocessed = self.collection.count_documents(query)
        self.logger.info(f"Found {total_unprocessed} total unprocessed articles")

        # Fetch articles
        cursor = self.collection.find(query)
        if limit:
            cursor = cursor.limit(limit)

        articles = list(cursor)
        self.logger.info(f"Retrieved {len(articles)} unprocessed articles (limit={limit})")
        return articles

    def call_yandexgpt(self, prompt: str, max_retries: int = None) -> str:
        """Send prompt to YandexGPT using OpenAI client.

        Args:
            prompt: The prompt to send to Yandex AI
            max_retries: Number of retry attempts (default: Config.MAX_RETRIES)

        Returns:
            Yandex AI response text
        """
        if max_retries is None:
            max_retries = Config.MAX_RETRIES

        for attempt in range(max_retries):
            try:
                self.logger.info(
                    f"Calling YandexGPT (attempt {attempt + 1}/{max_retries})..."
                )

                # Initialize OpenAI client with Yandex base URL
                client = OpenAI(
                    base_url=f"{self.yagpt_url}/v1",
                    api_key=self.yagpt_token,
                )

                # Use chat completions endpoint
                response = client.chat.completions.create(
                    model=self.yagpt_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=2000,
                )

                response_text = response.choices[0].message.content.strip()

                if response_text:
                    self.logger.info(
                        f"YandexGPT response received ({len(response_text)} chars)"
                    )
                    return response_text
                else:
                    self.logger.warning("YandexGPT returned empty response")
                    if attempt < max_retries - 1:
                        time.sleep(5)
                        continue

            except Exception as e:
                self.logger.error(
                    f"Error calling YandexGPT on attempt {attempt + 1}: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
                else:
                    raise

        return ""

    def create_analysis_prompt(self, article: Dict) -> str:
        """Create analysis prompt for an article.

        Args:
            article: MongoDB document with article data

        Returns:
            Formatted prompt for Yandex AI
        """
        # Get prompt template from config (custom or default)
        prompt_template = Config.get_prompt()

        # Extract article data
        title = article.get("title", "")
        url = article.get("url", "")
        article_date = article.get("article_date", article.get("date", "Не указана"))
        content = article.get("content_full", article.get("content", ""))
        description = article.get("description", "")

        # Combine content for analysis
        full_content = f"{description}\n\n{content}"

        # Format prompt with article data
        prompt = prompt_template.format(
            title=title,
            url=url,
            article_date=article_date,
            content=full_content[:8000],  # Limit to avoid token overflow
        )

        return prompt

    async def send_to_telegram_async(self, message: str, parse_mode: str = "Markdown") -> bool:
        """Async method to send message to Telegram channel.

        Args:
            message: Message text to send
            parse_mode: Message format (Markdown or HTML)

        Returns:
            True if successful, False otherwise
        """
        if not self.telegram_bot or not Config.TELEGRAM_CHANNEL_ID:
            self.logger.warning(
                "⚠️  Telegram bot not configured - skipping message send"
            )
            return False

        try:
            # Split message if too long (Telegram limit: 4096 chars)
            if len(message) > 4000:
                messages = self.split_long_message(message)
                for i, msg in enumerate(messages, 1):
                    self.logger.info(f"Sending part {i}/{len(messages)} to Telegram...")
                    await self.telegram_bot.send_message(
                        chat_id=Config.TELEGRAM_CHANNEL_ID,
                        text=msg,
                        parse_mode=parse_mode,
                    )
                    await asyncio.sleep(1)  # Small delay between parts
            else:
                self.logger.info("Sending message to Telegram...")
                await self.telegram_bot.send_message(
                    chat_id=Config.TELEGRAM_CHANNEL_ID,
                    text=message,
                    parse_mode=parse_mode,
                )

            self.logger.info("✅ Message sent to Telegram successfully")
            return True

        except TelegramError as e:
            self.logger.error(f"❌ Telegram API error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Error sending to Telegram: {e}")
            return False

    def send_to_telegram(self, message: str, parse_mode: str = "Markdown") -> bool:
        """Synchronous wrapper for async send_to_telegram method."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.send_to_telegram_async(message, parse_mode)
        )

    def split_long_message(self, message: str, max_length: int = 4000) -> List[str]:
        """Split long message into multiple parts.

        Args:
            message: Original message
            max_length: Maximum characters per part

        Returns:
            List of message parts
        """
        parts = []
        current_part = ""

        # Split by paragraphs first
        paragraphs = message.split("\n\n")

        for para in paragraphs:
            if len(current_part) + len(para) + 2 > max_length:
                if current_part:
                    parts.append(current_part)
                    current_part = ""
                # If single paragraph is too long, split it
                if len(para) > max_length:
                    words = para.split(" ")
                    current_word = ""
                    for word in words:
                        if len(current_word) + len(word) + 1 > max_length:
                            if current_word:
                                parts.append(current_word)
                            current_word = word
                        else:
                            current_word += " " + word
                    if current_word:
                        parts.append(current_word)
                        current_word = ""
                else:
                    current_part = para
            else:
                if current_part:
                    current_part += "\n\n" + para
                else:
                    current_part = para

        if current_part:
            parts.append(current_part)

        return parts

    def mark_article_processed(self, article_id: str, summary: str = None):
        """Mark article as processed in MongoDB.

        Args:
            article_id: MongoDB document ID
            summary: Optional summary from LLM analysis
        """
        try:
            update_data = {
                "$set": {
                    "processed": True,
                    "processed_at": time.time(),
                }
            }

            # Add summary if provided
            if summary:
                update_data["$set"]["telegram_summary"] = summary

            self.collection.update_one(
                {"_id": ObjectId(article_id)}, update_data
            )
            self.logger.info(f"Marked article {article_id} as processed")
        except Exception as e:
            self.logger.error(f"Error marking article as processed: {e}")

    def process_single_article(self, article: Dict) -> Optional[str]:
        """Process single article: analyze with LLM and send to Telegram.

        Args:
            article: MongoDB document with article data

        Returns:
            Summary text if successful, None otherwise
        """
        try:
            article_id = str(article["_id"])
            title = article.get("title", "Unknown")

            self.logger.info(f"Processing article: {title}")

            # Create prompt and call Yandex AI
            prompt = self.create_analysis_prompt(article)
            summary = self.call_yandexgpt(prompt)

            if not summary:
                self.logger.error(f"Empty analysis for article {article_id}")
                return None

            # Send to Telegram
            if self.send_to_telegram(summary):
                # Mark as processed
                self.mark_article_processed(article_id, summary)
                self.logger.info(
                    f"✅ Successfully processed and sent article {article_id}"
                )
                return summary
            else:
                self.logger.error(
                    f"Failed to send article {article_id} to Telegram"
                )
                # Still mark as processed to avoid retry loops
                self.mark_article_processed(article_id, summary)
                return summary

        except Exception as e:
            self.logger.error(f"Error processing article: {e}")
            return None

    def process_batch(self, batch_size: int = None, delay: int = None) -> int:
        """Process batch of unprocessed articles.

        Args:
            batch_size: Number of articles to process (default: Config.BATCH_SIZE)
            delay: Delay between requests in seconds (default: Config.DELAY_BETWEEN_REQUESTS)

        Returns:
            Number of successfully processed articles
        """
        if batch_size is None:
            batch_size = Config.BATCH_SIZE
        if delay is None:
            delay = Config.DELAY_BETWEEN_REQUESTS

        self.logger.info(
            f"Starting batch processing (batch_size={batch_size}, delay={delay}s)"
        )

        # Get unprocessed articles
        articles = self.get_unprocessed_articles(limit=batch_size)

        if not articles:
            self.logger.info("No unprocessed articles found.")
            return 0

        # Process articles with progress bar
        successful = 0
        with tqdm(articles, desc="Processing articles", unit="article") as bar:
            for article in bar:
                bar.set_description(
                    f"Processing: {article.get('title', 'Unknown')[:40]}..."
                )

                if self.process_single_article(article):
                    successful += 1
                    bar.set_postfix(successful=successful, total=len(articles))

                # Delay between requests
                time.sleep(delay)

        self.logger.info(
            f"Batch complete: {successful}/{len(articles)} successful"
        )
        return successful

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics.

        Returns:
            Dictionary with statistics
        """
        try:
            total_articles = self.collection.count_documents({})
            processed_articles = self.collection.count_documents({"processed": True})
            unprocessed_articles = self.collection.count_documents({"processed": {"$ne": True}})

            return {
                "total_articles": total_articles,
                "processed_articles": processed_articles,
                "unprocessed_articles": unprocessed_articles,
                "processing_rate": f"{(processed_articles / total_articles * 100):.1f}%"
                if total_articles > 0
                else "0%",
            }
        except Exception as e:
            self.logger.error(f"Error getting processing stats: {e}")
            return {
                "total_articles": 0,
                "processed_articles": 0,
                "unprocessed_articles": 0,
                "processing_rate": "N/A",
            }


def main():
    """Main entry point for the agent."""
    print("\n" + "=" * 60)
    print("MongoDB → Yandex AI → Telegram Pipeline")
    print("=" * 60)

    # Validate configuration
    if not Config.validate():
        print("\n❌ Configuration validation failed")
        return

    # Display configuration
    Config.print_config()

    try:
        # Initialize agent
        agent = MongoYandexTelegramAgent()

        # Display initial stats
        stats = agent.get_processing_stats()
        print("\n" + "=" * 60)
        print("Initial Statistics:")
        print("=" * 60)
        for key, value in stats.items():
            print(f"  {key}: {value}")
        print("=" * 60 + "\n")

        # Process batch
        successful = agent.process_batch()

        # Display final stats
        stats = agent.get_processing_stats()
        print("\n" + "=" * 60)
        print("Final Statistics:")
        print("=" * 60)
        for key, value in stats.items():
            print(f"  {key}: {value}")
        print("=" * 60)
        print(f"\n✅ Successfully processed {successful} articles\n")

    except KeyboardInterrupt:
        print("\n\n⚠️  Processing interrupted by user\n")
    except Exception as e:
        print(f"\n\n❌ Error: {e}\n")
        print("Please check:")
        print("  1. MongoDB is running and accessible")
        print("  2. Credentials are correct")
        print("  3. Database and collection exist")
        print("  4. Yandex AI token is valid")
        print("  5. Telegram bot token and channel ID are correct\n")


if __name__ == "__main__":
    main()
