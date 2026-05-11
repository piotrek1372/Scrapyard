"""
EnvironmentManager module for managing the skybox and lighting.
"""
from panda3d.core import NodePath, AmbientLight, DirectionalLight, PointLight, LVector4, Filename, Fog

class EnvironmentManager:
    """Manages skybox and lighting setup for the scene."""

    def __init__(self, app) -> None:
        """Initializes the EnvironmentManager.
        
        Args:
            app: The main application instance.
        """
        self.app = app
        self.render = app.render
        self.loader = app.loader
        
        self._setup_lighting()
        self._setup_fog()

    def _setup_fog(self) -> None:
        """Sets up exponential fog to hide the missing background."""
        self.fog = Fog("muddy_fog")
        # Brownish-grey color matching a scrapyard
        self.fog.setColor(0.35, 0.32, 0.30)
        self.fog.setExpDensity(0.015)
        self.render.setFog(self.fog)

    def _setup_lighting(self) -> None:
        """Sets up ambient, directional, and point lighting for the scene."""
        # Ambient
        ambient = AmbientLight("ambient")
        ambient.setColor(LVector4(0.3, 0.3, 0.35, 1))
        self.render.setLight(self.render.attachNewNode(ambient))

        # Key light (directional)
        key = DirectionalLight("key_light")
        key.setColor(LVector4(0.9, 0.85, 0.8, 1))
        key.setShadowCaster(True, 1024, 1024)
        key_np = self.render.attachNewNode(key)
        key_np.setHpr(45, -45, 0)
        self.render.setLight(key_np)

        # Fill light (point)
        fill = PointLight("fill_light")
        fill.setColor(LVector4(0.4, 0.45, 0.6, 1))
        fill.setAttenuation((1, 0.05, 0.01))
        fill_np = self.render.attachNewNode(fill)
        fill_np.setPos(-10, -10, 8)
        self.render.setLight(fill_np)

    def update(self, camera_pos) -> None:
        """Updates environmental effects."""
        pass
