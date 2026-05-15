"""
TerrainManager module using multiple GeoMipTerrain instances for true chunk loading.
Blocks outside load distance are completely removed from RAM/GPU.

Island system: only chunks whose (cx, cy) key is present in ISLAND_CHUNKS receive
full GeoMipTerrain geometry.  All other chunks become cheap flat water quads.
Four CollisionPlane walls at the island perimeter act as hard physical barriers.
"""
import math
import logging
import random
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from panda3d.core import (
    CardMaker,
    CollisionNode,
    CollisionPlane,
    Geom,
    Shader,
    GeomNode,
    GeomTristrips,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    GeoMipTerrain,
    NodePath,
    Filename,
    Plane,
    PNMImage,
    Point3,
    SamplerState,
    Texture,
    TextureStage,
    TransparencyAttrib,
    Vec3,
)
from src.core.config import Config

logger = logging.getLogger("Scrapyard.Terrain")

# ---------------------------------------------------------------------------
# Island definition
# ---------------------------------------------------------------------------
# 5×5 square centred on the origin chunk.  Using a frozenset allows future
# irregular island shapes (e.g. L-shape, archipelago) without any logic change.
ISLAND_CHUNKS: FrozenSet[Tuple[int, int]] = frozenset(
    (cx, cy) for cx in range(-5, 6) for cy in range(-5, 6)
)

# ---------------------------------------------------------------------------
# Tile model registry
# ---------------------------------------------------------------------------
# Panda3D's ModelPool (invoked by loader.loadModel) caches geometry and texture
# data keyed by filename.  Multiple loadModel() calls on the same path share
# the underlying Geom / Texture objects via reference counting — RAM cost is
# O(1) per unique path regardless of how many chunks instance the model.
_TILE_MODEL_PATHS: Tuple[str, ...] = (
    "assets/models/tiles/tile_of_cracked_asphalt.glb",
    "assets/models/tiles/tile_of_muddy_ground.glb",
    "assets/models/tiles/tile_of_rusted_metal_plates.glb",
)

class TerrainChunk:
    """A single chunk of terrain managed by GeoMipTerrain.

    Island chunks receive full GeoMipTerrain geometry and a heightmap.
    Non-island (water) chunks contain only a flat quad at z = 0 and
    skip all heightmap / GeoMipTerrain allocation to save RAM and CPU.
    """

    # Vertical scale applied to the root node — must match setSz() below.
    _HEIGHT_SCALE: float = 20.0

    # Water surface colour — slightly muted to reduce harshness against fogged terrain.
    # setFogOff() on the quad keeps this value stable at all distances (see below).
    _WATER_COLOR: Tuple[float, float, float, float] = (0.15, 0.22, 0.35, 1.0)

    # Tile model world-unit scale. Model unscaled bounds span 2.0 units on X and Y axes.
    # A scale of 3.0 gives the model a span of 6.0 units (~3/16 of the chunk width).
    _TILE_SCALE: float = 1.8

    # Polar placement parameters for _spawn_tile_models.
    _TILE_SECTOR_ANGLES: Tuple[float, float, float, float] = (45.0, 135.0, 225.0, 315.0)
    _TILE_RADIUS_MIN: float = 1.2
    _TILE_RADIUS_MAX: float = 3.2
    _TILE_ANGLE_JITTER: float = 40.0

    def __init__(
        self,
        cx: int,
        cy: int,
        size: int,
        parent: NodePath,
        loader,
        is_island: bool = True,
        ground_texture: Optional[Texture] = None,
        tile_paths: Optional[Tuple[str, ...]] = None,
        manager = None,
    ) -> None:
        """Create a single terrain chunk at grid position (cx, cy).

        Args:
            cx: Chunk column index (world_x = cx * size).
            cy: Chunk row index   (world_y = cy * size).
            size: Chunk edge length in world units (also heightmap width-1).
            parent: NodePath to attach the visible root to when visible.
            loader: Panda3D loader (unused directly, kept for API symmetry).
            is_island: True  → generate GeoMipTerrain terrain geometry.
                       False → generate a flat water quad; no heightmap.
            ground_texture: Shared procedural dirt texture; applied only when
                            is_island is True.  None → no texture (grey mesh).
            tile_paths: Tuple of model file paths to spawn as surface tiles.
                        None or empty → no tile models spawned.
        """
        self.cx, self.cy = cx, cy
        self.size = size
        self.parent = parent
        self.loader = loader
        self.is_island = is_island
        self.manager = manager
        self.models: List[NodePath] = []
        self.grass_nodes: List[NodePath] = []
        self.spawned_positions: List[Tuple[float, float]] = []
        
        # Calculate island boundaries in world coordinates for heightmap blending.
        island_xs = {c[0] for c in ISLAND_CHUNKS}
        island_ys = {c[1] for c in ISLAND_CHUNKS}
        self.island_min_x: float = float(min(island_xs) * size)
        self.island_max_x: float = float((max(island_xs) + 1) * size)
        self.island_min_y: float = float(min(island_ys) * size)
        self.island_max_y: float = float((max(island_ys) + 1) * size)

        if is_island:
            # Island path: full heightmap + GeoMipTerrain geometry.
            self.img: Optional[PNMImage] = PNMImage(self.size + 1, self.size + 1)
            self.terrain: Optional[GeoMipTerrain] = GeoMipTerrain(
                f"chunk_{cx}_{cy}"
            )
            self._generate_heightmap()  # fills self.img, then calls generate()
            self.root: NodePath = self.terrain.getRoot()
            self.root.setPos(cx * size, cy * size, 0)
            self.root.setSz(self._HEIGHT_SCALE)
            if ground_texture is not None:
                self._build_terrain_mesh(ground_texture)
            # Force two-sided rendering on every GeomNode in the terrain tree.
            # setTwoSided on the root NodePath may be overridden by a CullFaceAttrib
            # that GeoMipTerrain sets directly on its generated child GeomNodes.
            # findAllMatches("**/+GeomNode") catches all geometry descendants.
            self.root.setTwoSided(True)  # root fallback
            for gn in self.root.findAllMatches("**/+GeomNode"):
                gn.setTwoSided(True)
            self._create_terrain_skirts()
            if tile_paths:
                self._spawn_tile_models(tile_paths)
            self._spawn_grass()
        else:
            # Water path: lightweight flat quad; no heightmap allocation.
            self.img = None
            self.terrain = None
            self.root = NodePath(f"water_chunk_{cx}_{cy}")
            self.root.setPos(cx * size, cy * size, 0)
            self._create_water_quad()
            self._create_sea_floor()

        self.is_visible = False
        
    def _create_terrain_skirts(self) -> None:
        """Attach four vertical side-walls and a bottom cap to each island chunk.

        GeoMipTerrain produces only the top surface mesh.  When an elevated
        area is viewed from the side the hollow interior is visible, making
        models on hills appear to float.  This method seals the four chunk
        edges and underside with CardMaker quads coloured to match the
        procedural dirt palette.

        Local-space geometry (self.root carries setSz=20.0):
          - Walls span local z ∈ [-DEPTH, 0]  →  world z ∈ [-3.0, 0]
          - Horizontal span equals self.size (8 world-units per edge)
          - setTwoSided makes each quad visible from both faces.
        """
        DEPTH: float = 0.5         # local z; × 20 = 10 world-units (deep abyss)
        DIRT = (0.05, 0.04, 0.03, 1.0)  # deep murky mud color
        sz: float = float(self.size)

        def _wall(name: str, pos_xyz, heading: float) -> None:
            """Create one vertical CardMaker quad attached to self.root."""
            cm = CardMaker(f"{name}_{self.cx}_{self.cy}")
            # Frame in CardMaker's local XZ plane: x ∈ [0, sz], z ∈ [-DEPTH, 0]
            cm.setFrame(0.0, sz, -DEPTH, 0.0)
            np: NodePath = self.root.attachNewNode(cm.generate())
            np.setPos(*pos_xyz)
            np.setH(heading)
            np.setTwoSided(True)
            np.setColor(*DIRT)
            np.setShaderOff()
            np.setMaterialOff()
            np.setLightOff()

        # CardMaker default: quad in XZ plane facing +Y.
        # H rotates around Z: 0°=+Y, 90°=+X, 180°=-Y, -90°/-270°=-X.
        # Only create walls on edges that border WATER to remove internal chunk strips.
        if (self.cx, self.cy - 1) not in ISLAND_CHUNKS:
            _wall("skirt_s", (0.0, 0.0, 0.0),  0.0)    # south edge y=0,  face +Y
        if (self.cx, self.cy + 1) not in ISLAND_CHUNKS:
            _wall("skirt_n", (sz,  sz,  0.0), 180.0)   # north edge y=sz, face -Y
        if (self.cx - 1, self.cy) not in ISLAND_CHUNKS:
            _wall("skirt_w", (0.0, sz,  0.0),  90.0)   # west  edge x=0,  face +X
        if (self.cx + 1, self.cy) not in ISLAND_CHUNKS:
            _wall("skirt_e", (sz,  0.0, 0.0), -90.0)   # east  edge x=sz, face -X

        # Bottom cap — flat quad at local z = -DEPTH.
        cm_bot = CardMaker(f"skirt_bot_{self.cx}_{self.cy}")
        cm_bot.setFrame(0.0, sz, 0.0, sz)
        bot_np: NodePath = self.root.attachNewNode(cm_bot.generate())
        bot_np.setP(-90.0)          # rotate XZ card → XY plane (flat)
        bot_np.setZ(-DEPTH)
        bot_np.setTwoSided(True)
        bot_np.setColor(0.02, 0.02, 0.02, 1.0) # Black bottom
        bot_np.setShaderOff()
        bot_np.setMaterialOff()
        bot_np.setLightOff()

    def _build_terrain_mesh(self, tex: Texture) -> None:
        """Build a custom triangle-mesh terrain from the heightmap.

        GeoMipTerrain.generate() produces correct geometry but the resulting
        GeomNode renders as invisible regardless of render-state configuration
        (confirmed: 81 verts, 1 geom, not hidden — but never drawn on screen).

        This method builds an equivalent mesh manually using GeomVertexWriter,
        which uses the SAME proven render path as CardMaker (water quads,
        skirts) that IS visible.  self.img is still used for height sampling
        in height_at() so collision/placement logic is unchanged.

        Layout: (size+1)×(size+1) vertices on a regular grid.  Heights come
        from self.img.get_gray(x, y).  UV coords span [0, 1] across the chunk
        so the tiled dirt texture repeats naturally.

        Render state mirrors water/skirt quads exactly:
          setShaderOff   — fixed-function pipeline (avoids simplepbr black bug)
          setMaterialOff — prevent PBR material override
          setLightOff    — prevent shadow-caster from making mesh black
          setColor       — explicit opaque dirt colour (vertex colour fallback)
          setTexture     — dirt texture for detail
        """
        n = self.size + 1           # vertex grid dimension (9 for size=8)
        fmt = GeomVertexFormat.getV3n3t2()
        vdata = GeomVertexData(
            f"terrain_{self.cx}_{self.cy}", fmt, Geom.UHStatic
        )
        vdata.setNumRows(n * n)

        vwriter = GeomVertexWriter(vdata, "vertex")
        nwriter = GeomVertexWriter(vdata, "normal")
        twriter = GeomVertexWriter(vdata, "texcoord")

        scale = float(self.size)
        for y in range(n):
            for x in range(n):
                h = self.img.get_gray(x, y)   # local Z in [0, 0.15]
                # Local XY goes 0..size; UV goes 0..1 (tiled by setTexScale)
                vwriter.addData3f(float(x), float(y), h)
                nwriter.addData3f(0.0, 0.0, 1.0)     # flat-up normal
                twriter.addData2f(x / scale, y / scale)

        # Triangle strips: one strip per row pair.
        prim = GeomTristrips(Geom.UHStatic)
        for row in range(self.size):
            for col in range(n):
                prim.addVertex(row * n + col)
                prim.addVertex((row + 1) * n + col)
            prim.closePrimitive()

        geom = Geom(vdata)
        geom.addPrimitive(prim)
        gnode = GeomNode(f"terrain_mesh_{self.cx}_{self.cy}")
        gnode.addGeom(geom)

        mesh_np: NodePath = self.root.attachNewNode(gnode)
        mesh_np.setTwoSided(True)
        mesh_np.setTexture(tex)
        mesh_np.setTexScale(TextureStage.getDefault(), 4.0, 4.0)
        
        # Add a detail stage for high-frequency grit/dirt
        ts_detail = TextureStage("detail")
        ts_detail.setMode(TextureStage.M_modulate)
        mesh_np.setTexture(ts_detail, tex)
        mesh_np.setTexScale(ts_detail, 32.0, 32.0)
        mesh_np.setShaderOff()
        mesh_np.setMaterialOff()
        mesh_np.setLightOff()
        mesh_np.setColor(0.3, 0.25, 0.18, 1.0) # Even darker, more saturated dirt
        mesh_np.setTransparency(TransparencyAttrib.MNone)
        # DepthOffset shifts the terrain's depth-buffer value slightly toward
        # the camera (equivalent to glPolygonOffset(-1, -1)).  At the shoreline,
        # terrain_mesh edge vertices sit at the same world z=0 as the water quad.
        # Without offset, the GPU cannot decide which surface wins → Z-fighting
        # (grey flash).  With offset=1, terrain always wins the depth test and
        # the water is cleanly occluded — no geometry is moved so no visual gaps.
        mesh_np.setDepthOffset(1)


    def _spawn_tile_models(
        self, tile_paths: Tuple[str, ...]
    ) -> None:
        """Place 2–4 tile models on this island chunk using deterministic RNG.

        Placement strategy (polar coordinates from chunk centre):
          • 4 angular sectors at 45°, 135°, 225°, 315° (NE/NW/SW/SE).
          • Each sector gets a random angle jitter ±30° and a random radius
            8–22 units — avoids chunk centre and edges, never forms a grid.
          • A random heading rotation gives each model a unique orientation.

        Z-placement:
          chunk.root has setSz(_HEIGHT_SCALE).  Children inherit that Z scale,
          so a child at local z=v maps to world z = v * _HEIGHT_SCALE.  The
          heightmap gray value v already equals the terrain local z, so:
              model.setZ(gray_value)  →  world_z = terrain_height  ✔
          setSz(1/_HEIGHT_SCALE) on the model counteracts the parent stretch
          so the model geometry is rendered at 1:1 scale.

        Args:
            tile_paths: Tuple of model file paths available for selection.
        """
        chunk_half: float = self.size / 2.0
        rng = random.Random(self.cx * 73856093 ^ self.cy * 19349663)
        
        # Sparse spawning: only 5% of island chunks receive models.
        if rng.random() > 0.05:
            return
            
        # Minimum density: exactly 1 model per selected chunk
        n_models: int = 1

        for i in range(n_models):
            # Try up to 8 times to find a non-overlapping spot
            for attempt in range(8):
                # Pick model path and load (ModelPool returns cached geometry).
                path = rng.choice(tile_paths)
                panda_path = Filename.fromOsSpecific(str(Path(path).resolve()))
                try:
                    model_np: NodePath = self.loader.loadModel(panda_path)
                except Exception as exc:
                    logger.warning("Tile model load failed (%s): %s", path, exc)
                    break # Failed to load, skip this model slot

                # Polar placement: sector i at base angle ± jitter, random radius.
                base_angle: float = self._TILE_SECTOR_ANGLES[i % 4]
                angle_deg: float = base_angle + rng.uniform(
                    -self._TILE_ANGLE_JITTER, self._TILE_ANGLE_JITTER
                )
                radius: float = rng.uniform(self._TILE_RADIUS_MIN, self._TILE_RADIUS_MAX)
                angle_rad: float = math.radians(angle_deg)
                lx: float = chunk_half + math.cos(angle_rad) * radius
                ly: float = chunk_half + math.sin(angle_rad) * radius

                # Sample heightmap for terrain surface z at this local position.
                px: int = int(max(0, min(self.size, lx)))
                py: int = int(max(0, min(self.size, ly)))
                gray: float = self.img.get_gray(px, py)

                model_np.reparentTo(self.parent)
                
                world_x = self.cx * self.size + lx
                world_y = self.cy * self.size + ly
                world_z = gray * self._HEIGHT_SCALE
                
                # Precise distance check against all currently spawned models
                s: float = self._TILE_SCALE
                # Minimum separation distance (model diameter is ~3.6, so 5.5 is very safe)
                MIN_DIST_SQ = 5.5 ** 2
                
                collision = False
                if self.manager:
                    for ox, oy in self.manager.model_positions:
                        dx = world_x - ox
                        dy = world_y - oy
                        if dx*dx + dy*dy < MIN_DIST_SQ:
                            collision = True
                            break
                
                if collision:
                    model_np.removeNode()
                    continue # Try another spot
                    
                if self.manager:
                    self.manager.model_positions.append((world_x, world_y))
                    self.spawned_positions.append((world_x, world_y))

                # Thin plate scale for the model
                model_np.setScale(s, 0.1, s)
                model_np.setHpr(rng.uniform(0.0, 360.0), -90.0, 0.0)
                
                # Place slightly above terrain surface (world_z)
                model_np.setPos(world_x, world_y, world_z + 0.02)
                
                self.models.append(model_np)
                break # Success, move to next model slot

        logger.debug(
            "Chunk (%d, %d): spawned %d tile models.", self.cx, self.cy, n_models
        )

    def _spawn_grass(self) -> None:
        """Spawn 15-30 grass billboards on island chunks.
        
        Density is higher on green 'grass' patches (determined by the same 
        noise as the ground texture).
        """
        rng = random.Random(self.cx * 982451653 ^ self.cy * 123456789)
        n_grass = rng.randint(15, 30)
        
        grass_tex = self.manager.grass_texture if self.manager else None
        if not grass_tex:
            return

        for _ in range(n_grass):
            lx = rng.uniform(0, self.size)
            ly = rng.uniform(0, self.size)
            
            # Use same noise logic as texture to find green spots
            nx = lx / self.size
            ny = ly / self.size
            v_grass = math.sin(nx * 4.2 + 0.5) * math.cos(ny * 3.7 + 1.2)
            
            # If not a green spot, lower chance of spawning
            if v_grass <= 0.15 and rng.random() > 0.2:
                continue

            px, py = int(lx), int(ly)
            gray = self.img.get_gray(px, py)
            world_z = gray * self._HEIGHT_SCALE
            
            # Create a simple X-quad (two crossed planes)
            grass_root = self.root.attachNewNode("grass_tuft")
            cm = CardMaker("grass_card")
            cm.setFrame(-0.5, 0.5, 0, 1.0)
            
            # Plane 1
            p1 = grass_root.attachNewNode(cm.generate())
            # Plane 2 (rotated 90 deg)
            p2 = grass_root.attachNewNode(cm.generate())
            p2.setH(90)
            
            grass_root.setPos(lx, ly, gray) # local z
            # COMPENSATE for parent _HEIGHT_SCALE=20.0
            # Target world size: width ~0.5, height ~0.3
            s_w = rng.uniform(0.4, 0.8)
            s_h = rng.uniform(0.25, 0.45) / self._HEIGHT_SCALE
            grass_root.setScale(s_w, s_w, s_h)
            grass_root.setH(rng.uniform(0, 360))
            
            grass_root.setTexture(grass_tex)
            grass_root.setTransparency(TransparencyAttrib.MAlpha)
            grass_root.setTwoSided(True)
            grass_root.setShaderOff()
            grass_root.setLightOff()
            
            self.grass_nodes.append(grass_root)

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
        MARGIN = 24.0
        for x in range(self.size + 1):
            for y in range(self.size + 1):
                # World coordinates
                world_x = float(self.cx * self.size + x)
                world_y = float(self.cy * self.size + y)
                
                wx = world_x * 0.05
                wy = world_y * 0.05
                
                # Calculate distance to the nearest island boundary.
                dist_x = min(world_x - self.island_min_x, self.island_max_x - world_x)
                dist_y = min(world_y - self.island_min_y, self.island_max_y - world_y)
                dist_to_edge = min(dist_x, dist_y)
                
                # Mask is 1.0 inland, smoothstep only on the edges.
                # Shifted down slightly to ensure shoreline is 'under' Z=0
                if dist_to_edge >= MARGIN:
                    mask = 1.0
                else:
                    t = dist_to_edge / MARGIN
                    mask = t * t * (3.0 - 2.0 * t)
                
                # Height in [ -0.02, 0.15 ] to avoid the white 'gap' at Z=0
                self.img.set_gray(x, y, 0.15 * mask - 0.01)

        self.terrain.setHeightfield(self.img)
        self.terrain.setBlockSize(self.size)   # Must precede generate().
        self.terrain.setNear(self.size * 2)    # LOD near distance.
        self.terrain.setFar(self.size * 4)     # LOD far distance.
        self.terrain.generate()
        
        # Physically detach all engine-generated gray geometry nodes.
        # We replace them entirely with our custom textured mesh in _build_terrain_mesh.
        for gn in self.terrain.getRoot().findAllMatches("**/+GeomNode"):
            gn.detachNode()
        # Diagnostic: log geom count to confirm geometry was produced.
        root = self.terrain.getRoot()
        for gn in root.findAllMatches("**/+GeomNode"):
            n_geoms = gn.node().getNumGeoms()
            logger.debug(
                "GeoMipTerrain (%d,%d) block %s: %d geoms",
                self.cx, self.cy, gn.getName(), n_geoms,
            )

    def _create_water_quad(self) -> None:
        """Build a subdivided mesh for water to allow vertex-based waves.
        
        Uses a regular grid of vertices (17x17 for size 16) and applies
         the custom water shader from TerrainManager.
        """
        res = 16 # vertices per chunk edge
        n = res + 1
        fmt = GeomVertexFormat.getV3n3t2()
        vdata = GeomVertexData(f"water_{self.cx}_{self.cy}", fmt, Geom.UHStatic)
        vdata.setNumRows(n * n)

        vwriter = GeomVertexWriter(vdata, "vertex")
        twriter = GeomVertexWriter(vdata, "texcoord")

        scale = float(self.size)
        for y in range(n):
            for x in range(n):
                # Local XY goes 0..size
                vwriter.addData3f(x * (scale/res), y * (scale/res), 0.0)
                twriter.addData2f(x / float(res), y / float(res))

        prim = GeomTristrips(Geom.UHStatic)
        for row in range(res):
            for col in range(n):
                prim.addVertex(row * n + col)
                prim.addVertex((row + 1) * n + col)
            prim.closePrimitive()

        geom = Geom(vdata)
        geom.addPrimitive(prim)
        gnode = GeomNode(f"water_mesh_{self.cx}_{self.cy}")
        gnode.addGeom(geom)

        water_np: NodePath = self.root.attachNewNode(gnode)
        water_np.setTwoSided(True)
        
        if self.manager and self.manager.water_shader:
            water_np.setShader(self.manager.water_shader)
        else:
            water_np.setColor(*self._WATER_COLOR)
            water_np.setShaderOff()
            
        water_np.setMaterialOff()
        water_np.setLightOff() # Shader handles its own 'lighting'
        water_np.setFogOff()

    def get_height(self, local_x: float, local_y: float) -> float:
        """Return world-space terrain height at chunk-local coordinates.

        Returns 0.0 immediately for water chunks (no heightmap available).
        For island chunks, samples the GeoMipTerrain heightfield and
        scales it by _HEIGHT_SCALE (20.0).
        """
        if not hasattr(self, "terrain"):
            return 0.0

        # local_x, local_y in [0, size] -> indices in [0, size]
        px: int = int(max(0, min(self.size, local_x)))
        py: int = int(max(0, min(self.size, local_y)))
        gray: float = self.img.get_gray(px, py)
        return gray * self._HEIGHT_SCALE

    def _create_sea_floor(self) -> None:
        """Add a flat textured quad below the water to act as sea floor.
        
        This prevents the background fog from being visible through the gap
        created when waves move the water surface upwards.
        """
        sz: float = float(self.size)
        cm = CardMaker(f"sea_floor_{self.cx}_{self.cy}")
        cm.setFrame(0.0, sz, 0.0, sz)
        floor_np: NodePath = self.root.attachNewNode(cm.generate())
        floor_np.setP(-90.0) # Flatten to XY plane
        # Place it slightly below the deepest possible wave trough
        floor_np.setZ(-1.5) # ~1.5 units deep
        
        if self.manager:
            floor_np.setTexture(self.manager.ground_texture)
            floor_np.setTexScale(TextureStage.getDefault(), 4.0, 4.0)
            
        floor_np.setShaderOff()
        floor_np.setMaterialOff()
        floor_np.setLightOff()
        floor_np.setColor(0.2, 0.15, 0.1, 1.0) # Dark muddy tone
        """Return world-space terrain height at chunk-local coordinates.

        Returns 0.0 immediately for water chunks (no heightmap available).
        For island chunks, samples self.img (PNMImage grayscale, 0–1) and
        applies the same vertical scale used by the root node's setSz().
        Nearest-pixel lookup — sufficient for character ground-snapping.

        Args:
            local_x: X position within this chunk (0 .. self.size).
            local_y: Y position within this chunk (0 .. self.size).

        Returns:
            Height in world units, or 0.0 for water chunks.
        """
        if not self.is_island:
            return 0.0
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
            for model in self.models:
                model.reparentTo(self.parent)
            self.is_visible = True
        elif not visible and self.is_visible:
            self.root.detachNode()
            for model in self.models:
                model.detachNode()
            for g in self.grass_nodes:
                g.detachNode()
            self.is_visible = False

    def destroy(self) -> None:
        """Remove geometry from the scene graph and free the node."""
        self.root.removeNode()
        for model in self.models:
            model.removeNode()
        self.models.clear()
        for g in self.grass_nodes:
            g.removeNode()
        self.grass_nodes.clear()
        
        if self.manager:
            for pos in self.spawned_positions:
                if pos in self.manager.model_positions:
                    self.manager.model_positions.remove(pos)
        self.spawned_positions.clear()
        # GeoMipTerrain will be garbage-collected with this chunk.

class TerrainManager:
    """Manages a grid of TerrainChunks based on player distance."""

    def __init__(self, app) -> None:
        self.app = app
        self.config: Config = app.game_config
        self.render = app.render
        self.loader = app.loader
        
        # Settings
        self.chunk_size = 8
        self.render_dist = int(self.config.get("graphics.render_distance", 15))
        self.load_dist = int(self.render_dist + 2)
        self.update_threshold = int(self.config.get("graphics.chunk_update_threshold", 2))
        
        self.occupied_cells: set = set()
        self.model_positions: List[Tuple[float, float]] = []
        self.macro_models: Dict[Tuple[int, int], Optional[Tuple[NodePath, list]]] = {}
        self.MACRO_SIZE = 48  # jednostki świata
        
        # Helper terrain for native coordinate calculations
        self.helper_terrain = GeoMipTerrain("helper")
        self.helper_terrain.setBlockSize(self.chunk_size)
        self.helper_terrain.getRoot().detachNode()
        
        self.chunks: Dict[Tuple[int, int], TerrainChunk] = {}
        self.last_chunk_pos = (999, 999) # Force initial update
        
        self.terrain_root = self.render.attachNewNode("terrain_root")
        
        # Load custom shaders
        self.water_shader = Shader.load(
            Shader.SL_GLSL,
            "shaders/water.vert",
            "shaders/water.frag"
        )

        # Build the shared procedural ground texture (one GPU upload for all chunks).
        self.ground_texture: Texture = self._build_ground_texture()
        self.grass_texture: Texture = self._build_grass_texture()

        # Place hard collision walls around the island perimeter.
        self._setup_island_walls()

        # Initial update — must come after walls so chunks see the full scene.
        self.update()

    def update(self) -> None:
        """Periodic update check."""
        cam_pos = self.app.camera.getPos(self.render)
        self._update_macro_models(cam_pos)
        
        # Use native Panda3D method as requested
        cx, cy = self.helper_terrain.get_block_from_pos(cam_pos.x, cam_pos.y)
        
        dx = cx - self.last_chunk_pos[0]
        dy = cy - self.last_chunk_pos[1]
        if math.sqrt(dx*dx + dy*dy) >= self.update_threshold:
            self._update_chunks(cx, cy)
            self.last_chunk_pos = (cx, cy)

    def _update_chunks(self, center_x: int, center_y: int) -> None:
        """Implement UNLOADED → LOADED → VISIBLE chunk state transitions.

        Non-island positions receive water chunks (cheap flat quads);
        island positions receive full GeoMipTerrain geometry.

        Args:
            center_x: Camera chunk column index.
            center_y: Camera chunk row index.
        """
        center_x, center_y = int(center_x), int(center_y)
        needed_load: Set[Tuple[int, int]] = set()
        needed_visible: Set[Tuple[int, int]] = set()

        for x in range(center_x - self.load_dist, center_x + self.load_dist + 1):
            for y in range(center_y - self.load_dist, center_y + self.load_dist + 1):
                dist = math.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
                if dist <= self.load_dist:
                    needed_load.add((x, y))
                    if dist <= self.render_dist:
                        needed_visible.add((x, y))

        # 1. Unload chunks that are too far.
        to_remove = [pos for pos in self.chunks if pos not in needed_load]
        for pos in to_remove:
            self.chunks[pos].destroy()
            del self.chunks[pos]

        # 2. Load / update visibility for needed chunks.
        for pos in needed_load:
            if pos not in self.chunks:
                # UNLOADED → LOADED (island vs. water determined by ISLAND_CHUNKS)
                self.chunks[pos] = TerrainChunk(
                    pos[0],
                    pos[1],
                    self.chunk_size,
                    self.terrain_root,
                    self.loader,
                    is_island=(pos in ISLAND_CHUNKS),
                    ground_texture=self.ground_texture,
                    tile_paths=(
                        _TILE_MODEL_PATHS if pos in ISLAND_CHUNKS else None
                    ),
                    manager=self,
                )

            # LOADED ↔ VISIBLE
            self.chunks[pos].set_visible(pos in needed_visible)

        logger.info(
            "Terrain updated: %d chunks in RAM, %d visible.",
            len(self.chunks),
            len(needed_visible),
        )

    def _update_macro_models(self, cam_pos) -> None:
        import math
        import random
        from panda3d.core import Filename
        from pathlib import Path
        
        island_xs = {c[0] for c in ISLAND_CHUNKS}
        island_ys = {c[1] for c in ISLAND_CHUNKS}
        island_min_x = min(island_xs) * self.chunk_size
        island_max_x = (max(island_xs) + 1) * self.chunk_size
        island_min_y = min(island_ys) * self.chunk_size
        island_max_y = (max(island_ys) + 1) * self.chunk_size

        cam_macro_x = int(math.floor(cam_pos.x / self.MACRO_SIZE))
        cam_macro_y = int(math.floor(cam_pos.y / self.MACRO_SIZE))
        macro_dist = int(math.ceil((self.render_dist * self.chunk_size) / self.MACRO_SIZE)) + 1
        
        visible_macros = set()
        for mx in range(cam_macro_x - macro_dist, cam_macro_x + macro_dist + 1):
            for my in range(cam_macro_y - macro_dist, cam_macro_y + macro_dist + 1):
                macro_key = (mx, my)
                visible_macros.add(macro_key)
                
                # Macro spawning logic removed in favour of uniform per-chunk spawning in TerrainChunk.
                pass

                    
        for macro_key in list(self.macro_models.keys()):
            if macro_key not in visible_macros:
                data = self.macro_models.pop(macro_key)
                if data is not None:
                    model_np, cells = data
                    model_np.removeNode()
                    for cell in cells:
                        self.occupied_cells.discard(cell)

    def _build_ground_texture(self) -> Texture:
        """Generate a procedural dirt/ground texture from a PNMImage.

        Resolution: 128×128 px (power-of-two for full mipmap chain, 7 levels).
        This single Texture object is shared by all island TerrainChunks —
        only one GPU upload regardless of island size (~48 KB VRAM total).

        Noise model: three sine-wave layers at different spatial frequencies
        approximate a hand-painted dirt/clay surface without any external libs:
          Layer 1 (low freq)  — large muddy patches (~8 cycles across texture)
          Layer 2 (mid freq)  — medium stones and clods (~23 cycles)
          Layer 3 (high freq) — fine grit/sand (~55 cycles)

        Palette: brownish-grey dirt, R∈[0.38, 0.56], G∈[0.33, 0.46], B∈[0.24, 0.32].
        """
        size = 128
        img = PNMImage(size, size, 3)  # RGB — no alpha needed for opaque terrain

        for y in range(size):
            for x in range(size):
                nx: float = x / size
                ny: float = y / size

                # Layer 1: large muddy patches
                v1 = math.sin(nx * 9.1 + 1.3) * math.cos(ny * 8.7 + 0.9) * 0.50
                # Layer 2: medium clods / stones
                v2 = math.sin(nx * 23.5 + ny * 19.3 + 0.4) * 0.30
                # Layer 3: fine grit / sand
                v3 = (
                    math.sin(nx * 55.2 + 2.1) * math.cos(ny * 53.9 + 1.8) * 0.20
                )
                # Layer 4: Low-frequency "biome" noise for grass patches
                v_grass = math.sin(nx * 4.2 + 0.5) * math.cos(ny * 3.7 + 1.2)

                # Combine layers; map (-1, 1) → (0, 1) then clamp.
                val: float = max(0.0, min(1.0, (v1 + v2 + v3 + 1.0) * 0.5))

                if v_grass > 0.15:
                    # Muted olive/grass palette (Scrapyard style)
                    img.setXel(x, y, 0.28 + val * 0.12, 0.34 + val * 0.14, 0.18 + val * 0.06)
                else:
                    # Classic brownish-grey dirt palette.
                    img.setXel(x, y, 0.38 + val * 0.18, 0.33 + val * 0.13, 0.24 + val * 0.08)

        tex = Texture("ground_dirt")
        tex.load(img)
        tex.setMinfilter(SamplerState.FT_linear_mipmap_linear)
        tex.setMagfilter(SamplerState.FT_linear)
        tex.setWrapU(SamplerState.WM_repeat)
        tex.setWrapV(SamplerState.WM_repeat)

        logger.info("Ground texture generated: %d\u00d7%d px (procedural dirt).", size, size)
        return tex

    def _build_grass_texture(self) -> Texture:
        """Generate a procedural grass blade texture (64x64 RGBA)."""
        size = 64
        img = PNMImage(size, size, 4)
        img.fill(0, 0, 0) # Fill RGB with black
        img.alpha_fill(0) # Fill alpha with 0 (transparent)
        
        for i in range(12): # Draw 12 blades of grass
            bx = random.uniform(10, 54)
            width = random.uniform(2, 5)
            height = random.uniform(30, 60)
            
            # Simple blade: triangle-ish
            for y in range(int(size - height), size):
                # Normalized y from bottom (0) to top (1)
                ty = (size - y) / height
                curr_w = width * (1.0 - ty * 0.8) # Taper at top
                start_x = int(bx - curr_w / 2)
                end_x = int(bx + curr_w / 2)
                for x in range(start_x, end_x + 1):
                    if 0 <= x < size:
                        # Color: dark green base to bright yellow-green tip
                        brightness = 0.5 + ty * 0.5
                        img.setXel(x, y, 0.05 * brightness, (0.2 + ty * 0.5) * brightness, 0.02)
                        img.setAlpha(x, y, 1.0)
                        
        tex = Texture("grass_billboard")
        tex.load(img)
        tex.setMagfilter(SamplerState.FT_linear)
        tex.setMinfilter(SamplerState.FT_linear_mipmap_linear)
        return tex

    def _setup_island_walls(self) -> None:
        """Place four inward-facing CollisionPlane walls at the island boundary.

        World-space extents are derived from ISLAND_CHUNKS at runtime so the
        walls auto-adapt when the frozenset changes shape in the future.

        Each wall's into-mask is set to 1 (= the player sphere's from-mask as
        configured in FPVController._setup_collisions) so CollisionHandlerPusher
        detects and resolves the contact, pushing the player back onto the island.

        Coordinate convention:
            min_x = min(cx) * chunk_size          (west edge)
            max_x = (max(cx) + 1) * chunk_size    (east edge)
            … same for Y.
        """
        xs = {cx for cx, _ in ISLAND_CHUNKS}
        ys = {cy for _, cy in ISLAND_CHUNKS}
        min_x: float = float(min(xs) * self.chunk_size)
        max_x: float = float((max(xs) + 1) * self.chunk_size)
        min_y: float = float(min(ys) * self.chunk_size)
        max_y: float = float((max(ys) + 1) * self.chunk_size)

        # (name, plane_normal, point_on_plane)
        wall_specs = [
            ("island_wall_west",  Vec3( 1,  0, 0), Point3(min_x, 0.0, 0.0)),
            ("island_wall_east",  Vec3(-1,  0, 0), Point3(max_x, 0.0, 0.0)),
            ("island_wall_south", Vec3( 0,  1, 0), Point3(0.0, min_y, 0.0)),
            ("island_wall_north", Vec3( 0, -1, 0), Point3(0.0, max_y, 0.0)),
        ]
        for name, normal, point in wall_specs:
            cn = CollisionNode(name)
            cn.addSolid(CollisionPlane(Plane(normal, point)))
            # into-mask 1 matches the player sphere's from-mask (see FPVController).
            cn.setIntoCollideMask(1)
            self.terrain_root.attachNewNode(cn)

        logger.info(
            "Island walls: x∈[%.0f, %.0f]  y∈[%.0f, %.0f].",
            min_x, max_x, min_y, max_y,
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
