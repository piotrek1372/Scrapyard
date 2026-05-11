from src.core.Inventory import Inventory

class Player:
    def __init__(self, name, balance, free_loots) -> None:
        """Initializes class Player which
        represents player's atributes and datas"""
        self.name: str = name | 'player'
        self.balance: int = balance | 0
        self.free_loots = free_loots | 5
        self.inventory: object = Inventory

    def _read_player(self) -> None:
        """Reads defaults or existing profile data,
        creates instance of player"""
