import Item


class Inventory:
    def __init__(self, capacity) -> None:
        """Initializes inventory class which represents player's items set"""
        self.items: list[object] = []
        self.capacity: int = capacity
        self.free_space: int = self.capacity - len(self.items)

    def add_object(self, _object: object) -> None:
        """Adds item taken up by player to inventory"""
        self.items.append(_object)
        self.get_free_space()
        
    def remove_object(self, _object: object) -> None:
        """removes item taken out by player from inventory"""
        self.items.remove(_object)
        self.get_free_space()
    
    @property
    def free_space(self) -> int:
        """Returns free space in inventory"""
        self.free_space = self.capacity - len(self.items)
        return self.free_space