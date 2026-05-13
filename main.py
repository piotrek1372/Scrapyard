"""
Scrapyard — entry point.

Creates and runs the single ScrapyardApp ShowBase instance which manages
all game states internally (main menu, settings, profile, saves, playing).
"""
import logging

logging.basicConfig(level=logging.INFO)

from src.core.app import ScrapyardApp


def main() -> None:
    """Application entry point."""
    app = ScrapyardApp()
    app.run()


if __name__ == "__main__":
    main()