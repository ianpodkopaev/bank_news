#!/usr/bin/env python3
"""
Main entry point for Bank News pipeline.
Runs the MongoDB → Yandex AI → Telegram processing.
"""

from mongo_yandex_telegram import main

if __name__ == "__main__":
    main()
