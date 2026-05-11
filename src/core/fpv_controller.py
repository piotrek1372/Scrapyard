"""
FPVController module for handling First Person View movement and camera control.
"""
from panda3d.core import (
    NodePath, WindowProperties, Vec3, Point3, 
    CollisionNode, CollisionSphere, CollisionRay, 
    CollisionTraverser, CollisionHandlerPusher, CollisionHandlerQueue
)
from direct.showbase.ShowBase import ShowBase

class FPVController:
    """Handles First Person View camera, movement, and collisions."""

    def __init__(self, base: ShowBase, start_pos: Vec3 = Vec3(0, 0, 5)) -> None:
        """Initializes the FPVController.
        
        Args:
            base: The ShowBase application instance.
            start_pos: Initial position of the player.
        """
        self.base = base
        
        # Player node setup
        self.player_np = self.base.render.attachNewNode("player")
        self.player_np.setPos(start_pos)
        
        # Attach camera to player
        self.base.camera.reparentTo(self.player_np)
        self.base.camera.setPos(0, 0, 1.7) # Camera at eye level
        
        # Movement and camera state
        self.speed = 10.0
        self.mouse_sensitivity = 0.1
        self.heading = 0.0
        self.pitch = 0.0
        self.velocity_z = 0.0
        self.gravity = -20.0
        
        self.key_map = {
            "forward": False,
            "backward": False,
            "left": False,
            "right": False
        }
        
        self._setup_input()
        self._setup_collisions()
        
        # Center mouse
        self._center_mouse()
        
        # Task for updating movement
        self.base.taskMgr.add(self._update_task, "fpv_update_task")

    def _setup_collisions(self) -> None:
        """Sets up the collision solids and handlers for the player."""
        # 1. Traverser
        if not hasattr(self.base, 'cTrav') or self.base.cTrav is None:
            self.base.cTrav = CollisionTraverser("base_traverser")
            # self.base.cTrav.showCollisions(self.base.render) # Debug
            
        # 2. Pusher for walls (horizontal collisions)
        self.pusher = CollisionHandlerPusher()
        
        c_node = CollisionNode("player_sphere")
        c_node.addSolid(CollisionSphere(0, 0, 1.0, 0.5)) # Sphere radius 0.5 at height 1.0
        # Player collides with mask 1 (walls and ground)
        c_node.setFromCollideMask(1)
        c_node.setIntoCollideMask(0) # Player isn't collided into by others (for now)
        
        self.player_c_np = self.player_np.attachNewNode(c_node)
        self.pusher.addCollider(self.player_c_np, self.player_np)
        self.base.cTrav.addCollider(self.player_c_np, self.pusher)

        # 3. Ray for ground detection (vertical collisions / gravity)
        self.ground_ray = CollisionRay()
        self.ground_ray.setOrigin(0, 0, 2.0) # Start from above the player
        self.ground_ray.setDirection(0, 0, -1) # Point straight down
        
        c_ray_node = CollisionNode("player_ray")
        c_ray_node.addSolid(self.ground_ray)
        c_ray_node.setFromCollideMask(1) # Ground mask
        c_ray_node.setIntoCollideMask(0)
        
        self.player_ray_np = self.player_np.attachNewNode(c_ray_node)
        
        self.ground_handler = CollisionHandlerQueue()
        self.base.cTrav.addCollider(self.player_ray_np, self.ground_handler)

    def _setup_input(self) -> None:
        """Sets up keyboard and mouse inputs."""
        # Keyboard
        self.base.accept("w", self._update_key_map, ["forward", True])
        self.base.accept("w-up", self._update_key_map, ["forward", False])
        self.base.accept("s", self._update_key_map, ["backward", True])
        self.base.accept("s-up", self._update_key_map, ["backward", False])
        self.base.accept("a", self._update_key_map, ["left", True])
        self.base.accept("a-up", self._update_key_map, ["left", False])
        self.base.accept("d", self._update_key_map, ["right", True])
        self.base.accept("d-up", self._update_key_map, ["right", False])
        
        # Hide mouse cursor and lock it
        props = WindowProperties()
        props.setCursorHidden(True)
        props.setMouseMode(WindowProperties.M_relative)
        self.base.win.requestProperties(props)

    def _update_key_map(self, key: str, value: bool) -> None:
        """Updates the state of a movement key."""
        self.key_map[key] = value

    def _center_mouse(self) -> None:
        """Centers the mouse in the window."""
        if self.base.win:
            win_x = self.base.win.getProperties().getXSize() // 2
            win_y = self.base.win.getProperties().getYSize() // 2
            self.base.win.movePointer(0, win_x, win_y)

    def _update_task(self, task) -> int:
        """Frame task for processing movement and camera rotation."""
        dt = self.base.taskMgr.globalClock.getDt()
        
        # ── Mouse Look ──
        if self.base.mouseWatcherNode.hasMouse() and self.base.win:
            md = self.base.win.getPointer(0)
            x = md.getX()
            y = md.getY()
            
            win_center_x = self.base.win.getProperties().getXSize() // 2
            win_center_y = self.base.win.getProperties().getYSize() // 2
            
            delta_x = x - win_center_x
            delta_y = y - win_center_y
            
            if delta_x != 0 or delta_y != 0:
                self.heading -= delta_x * self.mouse_sensitivity
                self.pitch -= delta_y * self.mouse_sensitivity
                
                self.pitch = max(-89.0, min(89.0, self.pitch))
                
                self.player_np.setH(self.heading)
                self.base.camera.setP(self.pitch)
                
                self._center_mouse()

        # ── Movement ──
        move_vec = Vec3(0, 0, 0)
        
        if self.key_map["forward"]:
            move_vec.y += 1.0
        if self.key_map["backward"]:
            move_vec.y -= 1.0
        if self.key_map["left"]:
            move_vec.x -= 1.0
        if self.key_map["right"]:
            move_vec.x += 1.0
            
        if move_vec.length() > 0:
            move_vec.normalize()
            move_vec *= self.speed * dt
            self.player_np.setPos(self.player_np, move_vec)
        
        # ── Gravity and Ground Snapping ──
        # Apply gravity
        self.velocity_z += self.gravity * dt
        self.player_np.setZ(self.player_np.getZ() + self.velocity_z * dt)
        
        # Check ground collisions
        if self.ground_handler.getNumEntries() > 0:
            self.ground_handler.sortEntries()
            # Find highest entry beneath the player
            for entry in self.ground_handler.getEntries():
                surface_point = entry.getSurfacePoint(self.base.render)
                if surface_point.z < self.player_np.getZ() + 1.0: # Only snap to things below knee level
                    self.player_np.setZ(surface_point.z)
                    self.velocity_z = 0.0
                    break
        else:
            # Fallback to prevent falling out of world forever
            if self.player_np.getZ() < -50:
                self.player_np.setZ(5)
                self.velocity_z = 0.0

        return task.cont

    def get_pos(self) -> Vec3:
        """Returns the current position of the player."""
        return self.player_np.getPos()
