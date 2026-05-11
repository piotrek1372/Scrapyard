
import tracemalloc
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Mock Panda3D
mock_panda3d = MagicMock()
sys.modules['panda3d.core'] = mock_panda3d.core
sys.modules['direct.showbase.ShowBase'] = MagicMock()

from src.core.terrain import TerrainManager

def test_terrain_init_memory():
    app = MagicMock()
    app.loader.loadModel.return_value = MagicMock() # Mock heavy model load
    
    tracemalloc.start()
    tm = TerrainManager(app)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    print(f"Current RAM: {current / 1024 / 1024:.2f} MB")
    print(f"Peak RAM: {peak / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    test_terrain_init_memory()
