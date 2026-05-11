
import time
import tracemalloc
import sys
from pathlib import Path

# Set up environment
sys.path.append(".")

from src.core.app import ScrapyardApp
from src.core.config import Config

def run_benchmark():
    config = Config()
    # Force some settings
    config.set("graphics.render_distance", 15)
    config.set("graphics.vsync", True)
    
    tracemalloc.start()
    
    print("Starting ScrapyardApp for benchmarking...")
    # Initialize app (this will create the window)
    # We might need to handle the fact that we can't see the window
    app = ScrapyardApp(config)
    
    start_time = time.time()
    frames = 0
    
    # Run for 10 seconds
    while time.time() - start_time < 10:
        app.taskMgr.step()
        frames += 1
        
    end_time = time.time()
    fps = frames / (end_time - start_time)
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    print(f"\n--- BENCHMARK RESULTS ---")
    print(f"FPS: {fps:.2f}")
    print(f"Peak RAM: {peak / 1024 / 1024:.2f} MB")
    print(f"Current RAM: {current / 1024 / 1024:.2f} MB")
    print(f"Total Frames: {frames}")
    print(f"-------------------------\n")
    
    app.destroy()

if __name__ == "__main__":
    run_benchmark()
