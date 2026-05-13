
import unittest
import tracemalloc
import os
from pathlib import Path
from unittest.mock import MagicMock
import numpy as np

# Mock Panda3D before importing SkyboxManager
import sys
from unittest.mock import MagicMock

class MockTexture:
    def __init__(self, name):
        self.name = name
    def setup2dTexture(self, *args): pass
    def setRamImage(self, *args): pass
    def setKeepRamImage(self, *args): pass
    def setMinfilter(self, *args): pass
    def setMagfilter(self, *args): pass
    def setMaxMipmapLevel(self, *args): pass
    def setWrapU(self, *args): pass
    def setWrapV(self, *args): pass

mock_panda3d = MagicMock()
mock_panda3d.core.Texture = MockTexture
mock_panda3d.core.SamplerState = MagicMock()
sys.modules['panda3d.core'] = mock_panda3d.core

from src.core.skybox import SkyboxManager

class TestSkyboxMemory(unittest.TestCase):
    def setUp(self):
        self.app = MagicMock()
        self.manager = SkyboxManager(self.app)
        self.test_hdr = Path("assets/textures/freight_station_2k.hdr")

    def test_load_hdr_peak_ram(self):
        """Measures peak RAM during HDR loading to ensure it stays within limits."""
        if not self.test_hdr.exists():
            self.skipTest("HDR asset missing for memory test")

        tracemalloc.start()
        
        # Load texture
        tex = self.manager._load_hdr_texture(str(self.test_hdr))
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        peak_mb = peak / (1024 * 1024)
        print(f"\n[Memory Test] Peak RAM: {peak_mb:.2f} MB")
        
        # 2K HDR (2048x1024) float32 is ~24MB. Peak RAM is f32(24MB)+f16(12MB)+overhead ~36MB.
        # Ceiling of 100MB is conservative and safe for CI environments.
        self.assertLess(peak_mb, 100, f"Peak RAM {peak_mb:.2f}MB exceeds limit!")

if __name__ == "__main__":
    unittest.main()
