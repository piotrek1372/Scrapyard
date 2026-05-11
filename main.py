import logging
from src.core.app import ScrapyardApp
from src.core.config import Config
from src.ui.launcher import run_launcher

# Configure root logger
logging.basicConfig(level=logging.INFO)

def main():
    config = Config()
    
    # Run configuration launcher
    if run_launcher(config):
        # Start the actual game with verified config
        app = ScrapyardApp(config)
        app.run()
    else:
        print("Game startup cancelled by user.")

if __name__ == "__main__":
    main()