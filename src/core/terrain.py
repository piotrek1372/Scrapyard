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
    # Vertical scale applied to the root node — must match setSz() below.
    _HEIGHT_SCALE: float = 20.0

    def __init__(self, cx: int, cy: int, size: int, parent: NodePath, loader) -> None:
        """Create a single terrain chunk at grid position (cx, cy).

        Args:
            cx: Chunk column index (world_x = cx * size).
            cy: Chunk row index   (world_y = cy * size).
            size: Chunk edge length in world units (also heightmap width-1).
            parent: NodePath to attach the visible root to when visible.
            loader: Panda3D loader (unused directly, kept for API symmetry).
        """
        self.cx, self.cy = cx, cy
        self.size = size
        self.parent = parent
        self.loader = loader

        # Heightmap image stored for direct height sampling (no collision mesh).
        self.img: PNMImage = PNMImage(self.size + 1, self.size + 1)

        self.terrain = GeoMipTerrain(f"chunk_{cx}_{cy}")
        self._generate_heightmap()  # fills self.img, then calls generate()

        self.root: NodePath = self.terrain.getRoot()
        self.root.setPos(cx * size, cy * size, 0)
        self.root.setSz(self._HEIGHT_SCALE)

        self.is_visible = False
        
    def _generate_heightmap(self) -> None:
        """Fill self.img with a procedural heightmap and call generate().

        Configuration order is mandatory: setHeightfield → setBlockSize
        → setNear → setFar → generate(). Calling generate() before
        setBlockSize silently uses the default block size (producing
        16 sub-blocks instead of 1), which breaks per-chunk tiling.

        self.img is kept alive after generate() so that get_height()
        can sample it at O(1) cost without any collision geometry.
        """
        # Procedural sine-wave heightmap for visual terrain variation.
        for x in range(self.size + 1):
            for y in range(self.size + 1):
                wx = (self.cx * self.size + x) * 0.05
                wy = (self.cy * self.size + y) * 0.05
                val = (math.sin(wx) * math.cos(wy) + 1.0) * 0.5
                self.img.set_gray(x, y, val * 0.2 + 0.1)

        self.terrain.setHeightfield(self.img)
        self.terrain.setBlockSize(self.size)   # Must precede generate().
        self.terrain.setNear(self.size * 2)    # LOD near distance.
        self.terrain.setFar(self.size * 4)     # LOD far distance.
        self.terrain.generate()

    def get_height(self, local_x: float, local_y: float) -> float:
        """Return world-space terrain height at chunk-local coordinates.

        Samples self.img (the raw PNMImage grayscale, range 0-1) and
        applies the same vertical scale used by the root node's setSz().
        Nearest-pixel lookup — sufficient for character ground-snapping.

        Args:
            local_x: X position within this chunk (0 .. self.size).
            local_y: Y position within this chunk (0 .. self.size).

        Returns:
            Height in world units.
        """
        px: int = int(max(0, min(self.size, local_x)))
        py: int = int(max(0, min(self.size, local_y)))
        return self.img.get_gray(px, py) * self._HEIGHT_SCALE

    def set_visible(self, visible: bool) -> None:
        """Attach or detach the chunk root from the scene graph.

        Args:
            visible: True to show, False to hide.
        """
        if visible and not self.is_visible:
            self.root.reparentTo(self.parent)
            self.is_visible = True
        elif not visible and self.is_visible:
            self.root.detachNode()
            self.is_visible = False

    def destroy(self) -> None:
        """Remove geometry from the scene graph and free the node."""
        self.root.removeNode()
        # GeoMipTerrain will be garbage-collected with this chunk.

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
            
        logger.info(
            "Terrain updated: %d chunks in RAM, %d visible.",
            len(self.chunks), len(needed_visible),
        )

    def get_height_at(self, world_x: float, world_y: float) -> float:
        """Return terrain height at world-space coordinates.

        Finds the chunk that owns (world_x, world_y) and delegates to
        TerrainChunk.get_height().  Returns 0.0 if no chunk is loaded
        at that position (e.g. player is beyond the loaded border).

        Args:
            world_x: World X coordinate.
            world_y: World Y coordinate.

        Returns:
            Height in world units, or 0.0 if the chunk is not loaded.
        """
        cx: int = int(math.floor(world_x / self.chunk_size))
        cy: int = int(math.floor(world_y / self.chunk_size))
        chunk = self.chunks.get((cx, cy))
        if chunk is None:
            return 0.0
        local_x: float = world_x - cx * self.chunk_size
        local_y: float = world_y - cy * self.chunk_size
        return chunk.get_height(local_x, local_y)
