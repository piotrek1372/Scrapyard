"""
TerrainManager module using multiple GeoMipTerrain instances for true chunk loading.
Blocks outside load distance are completely removed from RAM/GPU.
"""
import math
import logging
from pathlib import Path
from typing import Dict, Tuple, Set, Optional

from panda3d.core import (
    NodePath, Filename, GeoMipTerrain, PNMImage, 
    Vec3, Texture, SamplerState
)
from src.core.config import Config

logger = logging.getLogger("Scrapyard.Terrain")

class TerrainChunk:
    """A single chunk of terrain managed by GeoMipTerrain."""
    def __init__(self, cx: int, cy: int, size: int, parent: NodePath, loader):
        self.cx, self.cy = cx, cy
        self.size = size
        self.parent = parent
        self.loader = loader
        
        self.terrain = GeoMipTerrain(f"chunk_{cx}_{cy}")
        self._generate_heightmap()
        
        self.terrain.setBlockSize(size) # One block per chunk for simplicity in this model
        self.terrain.setNear(size * 2)
        self.terrain.setFar(size * 4)
        
        self.root: NodePath = self.terrain.getRoot()
        self.root.setPos(cx * size, cy * size, 0)
        self.root.setSz(20.0)
        
        self.is_visible = False
        
    def _generate_heightmap(self):
        """Generates a unique heightmap for this chunk."""
        # 65x65 is required for 64x64 terrain due to +1 stitching rule
        img = PNMImage(self.size + 1, self.size + 1)
        # Use simple sine waves for testing procedural terrain
        for x in range(self.size + 1):
            for y in range(self.size + 1):
                wx = (self.cx * self.size + x) * 0.05
                wy = (self.cy * self.size + y) * 0.05
                val = (math.sin(wx) * math.cos(wy) + 1.0) * 0.5
                img.set_gray(x, y, val * 0.2 + 0.1)
        
        self.terrain.setHeightfield(img)
        self.terrain.generate()

    def set_visible(self, visible: bool):
        if visible and not self.is_visible:
            self.root.reparentTo(self.parent)
            self.is_visible = True
        elif not visible and self.is_visible:
            self.root.detachNode()
            self.is_visible = False

    def destroy(self):
        self.root.removeNode()
        # GeoMipTerrain will be garbage collected

class TerrainManager:
    """Manages a grid of TerrainChunks based on player distance."""

    def __init__(self, app) -> None:
        self.app = app
        self.config: Config = app.game_config
        self.render = app.render
        self.loader = app.loader
        
        # Settings
        self.chunk_size = 64
        self.render_dist = int(self.config.get("graphics.render_distance", 15))
        self.load_dist = int(self.render_dist + 2)
        self.update_threshold = int(self.config.get("graphics.chunk_update_threshold", 2))
        
        # Helper terrain for native coordinate calculations
        self.helper_terrain = GeoMipTerrain("helper")
        self.helper_terrain.setBlockSize(self.chunk_size)
        
        self.chunks: Dict[Tuple[int, int], TerrainChunk] = {}
        self.last_chunk_pos = (999, 999) # Force initial update
        
        self.terrain_root = self.render.attachNewNode("terrain_root")
        
        # Initial update
        self.update()

    def update(self) -> None:
        """Periodic update check."""
        cam_pos = self.app.camera.getPos(self.render)
        # Use native Panda3D method as requested
        cx, cy = self.helper_terrain.get_block_from_pos(cam_pos.x, cam_pos.y)
        
        dx = cx - self.last_chunk_pos[0]
        dy = cy - self.last_chunk_pos[1]
        if math.sqrt(dx*dx + dy*dy) >= self.update_threshold:
            self._update_chunks(cx, cy)
            self.last_chunk_pos = (cx, cy)

    def _update_chunks(self, center_x: int, center_y: int):
        """Implements UNLOADED -> LOADED -> VISIBLE transitions."""
        center_x, center_y = int(center_x), int(center_y)
        needed_load: Set[Tuple[int, int]] = set()
        needed_visible: Set[Tuple[int, int]] = set()
        
        # Calculate what SHOULD be loaded/visible
        for x in range(center_x - self.load_dist, center_x + self.load_dist + 1):
            for y in range(center_y - self.load_dist, center_y + self.load_dist + 1):
                dist = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                if dist <= self.load_dist:
                    needed_load.add((x, y))
                    if dist <= self.render_dist:
                        needed_visible.add((x, y))
        
        # 1. Unload chunks that are too far
        to_remove = [pos for pos in self.chunks if pos not in needed_load]
        for pos in to_remove:
            self.chunks[pos].destroy()
            del self.chunks[pos]
            
        # 2. Load/Update visibility for needed chunks
        for pos in needed_load:
            if pos not in self.chunks:
                # UNLOADED -> LOADED
                self.chunks[pos] = TerrainChunk(
                    pos[0], pos[1], self.chunk_size, 
                    self.terrain_root, self.loader
                )
            
            # LOADED <-> VISIBLE
            self.chunks[pos].set_visible(pos in needed_visible)
            
        logger.info(f"Terrain updated: {len(self.chunks)} chunks in RAM, {len(needed_visible)} visible.")
