"""
SkyboxManager module for high-performance HDR rendering in Panda3D.
Optimized for RAM efficiency (< 100MB) using float16 and immediate buffer release.
"""
import os
import math
import logging
from pathlib import Path
from panda3d.core import (
    NodePath, Texture, SamplerState, Filename, 
    Shader, TransparencyAttrib, Vec3,
    Geom, GeomNode, GeomTriangles, GeomVertexData,
    GeomVertexFormat, GeomVertexWriter
)

# Configure logger
logger = logging.getLogger("Scrapyard.Skybox")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

class SkyboxManager:
    """Manages high-performance HDR skyboxes with equirectangular mapping.
    
    This manager handles procedural mesh generation for the sky dome,
    optimized HDR texture loading using imageio/float16, and GLSL shaders.
    """

    def __init__(self, app) -> None:
        """Initializes the SkyboxManager.
        
        Args:
            app: The main application instance (ShowBase).
        """
        self.app = app
        self.render = app.render
        self.loader = app.loader
        
        self.skybox: NodePath = None
        self._setup_skybox()

    def _setup_skybox(self) -> None:
        """Creates the skydome and loads HDR texture with peak efficiency."""
        try:
            # 1. Procedural Sky Dome (Inverted UV Sphere)
            self.skybox = self._make_skydome(segments=48)
            self.skybox.reparentTo(self.render)
            self.skybox.setScale(900)  # Large enough to avoid clipping
            self.skybox.setBin("background", 0)
            self.skybox.setDepthWrite(False)
            self.skybox.setDepthTest(False)   # Eliminate Z-fighting at terrain edge
            self.skybox.setLightOff()
            self.skybox.setFogOff()
            self.skybox.setMaterialOff()      # Block simplepbr material override

            # 2. Single 2K asset — replaces multi-resolution 4K/8K/16K set.
            # 2K (2048x1024) cuts VRAM from 24 MB to 12 MB (float16).
            tex_res = "2k"
            tex_path = Path(f"assets/textures/freight_station_{tex_res}.hdr")

            if not tex_path.exists():
                raise FileNotFoundError(f"Required 2K HDR asset missing: {tex_path}")

            logger.info(f"Loading 2K HDR: {tex_path}")

            # 3. Optimized HDR Loading
            sky_tex = self._load_hdr_texture(str(tex_path))
            if sky_tex:
                self.skybox.setTexture(sky_tex)
            
            # 4. Apply GLSL Shaders
            shader_dir = Path("shaders")
            try:
                sky_shader = Shader.load(
                    Shader.SL_GLSL,
                    vertex=str(shader_dir / "sky.vert"),
                    fragment=str(shader_dir / "sky.frag")
                )
                self.skybox.setShader(sky_shader, 1) # Priority 1 to override simplepbr
            except Exception as e:
                logger.error(f"Shader load failed: {e}")

        except Exception as e:
            logger.error(f"Initialization error: {e}")

    def _load_hdr_texture(self, path: str) -> Texture:
        """Loads an .hdr image as a Panda3D Texture with memory optimizations.
        
        Uses float16 to reduce RAM/VRAM footprint by 50% compared to float32.
        Explicitly releases CPU RAM after GPU upload.

        Args:
            path: String path to the .hdr file.

        Returns:
            A Panda3D Texture object uploaded to GPU.
        """
        try:
            import numpy as np
            import imageio.v3 as iio
            import imageio_freeimage
            import imageio.plugins.freeimage
            
            # Ensure FreeImage binary is available
            try:
                imageio.plugins.freeimage.download()
            except Exception:
                pass # Already exists or no internet
            
            logger.info(f"Loading HDR (float16): {path}")
            
            # Load as float32 first (native imageio behavior)
            # Result: (H, W, 3) float32 (~96MB for 4K)
            hdr_f32 = iio.imread(path)
            
            # Convert to float16 immediately
            # Peak RAM: [f32 (~96MB) + f16 (~48MB)] = ~144MB
            hdr_f16 = hdr_f32.astype(np.float16)
            
            # FIX 2: Release f32 buffer immediately after conversion
            del hdr_f32
            
            h, w, _ = hdr_f16.shape
            
            tex = Texture("hdr_sky")
            # FRgb16 maps to GL_RGB16F
            tex.setup2dTexture(w, h, Texture.T_float, Texture.F_rgb16)
            
            # FIX 1: Pass numpy array directly to avoid tobytes() copy
            # Panda3D setRamImage accepts objects supporting buffer protocol
            tex.setRamImage(hdr_f16)
            
            # FIX 2 cont: release CPU-side RAM after GPU upload
            tex.setKeepRamImage(False)
            
            # Explicit free of f16 numpy buffer
            del hdr_f16
            
            # Texture settings
            tex.setMinfilter(SamplerState.FT_linear_mipmap_linear)
            tex.setMagfilter(SamplerState.FT_linear)
            tex.setMaxMipmapLevel(8)
            tex.setWrapU(SamplerState.WM_repeat)
            tex.setWrapV(SamplerState.WM_clamp)
            
            return tex
            
        except Exception as e:
            logger.error(f"HDR load failed: {e}")
            # Native fallback if imageio/freeimage fails
            tex = self.loader.loadTexture(path)
            if tex:
                tex.setKeepRamImage(False)
            return tex

    def _make_skydome(self, segments: int = 32) -> NodePath:
        """Creates an inverted UV sphere for equirectangular sky rendering.

        Args:
            segments: Resolution of the sphere.

        Returns:
            NodePath containing the procedural geometry.
        """
        format = GeomVertexFormat.getV3()
        vdata = GeomVertexData("sky_sphere", format, Geom.UHStatic)
        
        vertex = GeomVertexWriter(vdata, "vertex")
        
        # Build vertices
        for i in range(segments + 1):
            lat = math.pi * i / segments - math.pi / 2.0
            for j in range(segments + 1):
                lon = 2.0 * math.pi * j / segments
                
                x = math.cos(lat) * math.cos(lon)
                y = math.cos(lat) * math.sin(lon)
                z = math.sin(lat)
                
                vertex.addData3(x, y, z)
        
        # Build triangles (inverted for inside view)
        tris = GeomTriangles(Geom.UHStatic)
        for i in range(segments):
            for j in range(segments):
                v1 = i * (segments + 1) + j
                v2 = v1 + 1
                v3 = (i + 1) * (segments + 1) + j
                v4 = v3 + 1
                
                # Reverse winding for interior visibility
                tris.addVertices(v1, v3, v2)
                tris.addVertices(v2, v3, v4)
        
        geom = Geom(vdata)
        geom.addPrimitive(tris)
        
        node = GeomNode("sky_dome_node")
        node.addGeom(geom)
        
        return NodePath(node)

    def update(self, camera_pos: Vec3) -> None:
        """Keeps the skybox centered on the camera.
        
        Args:
            camera_pos: Current position of the camera in world space.
        """
        if self.skybox:
            self.skybox.setPos(camera_pos)
