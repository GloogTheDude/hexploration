class Player:
    def __init__(self, player_id: str, name: str, q: int = 0, r: int = 0):
        self.player_id = player_id
        self.name = name
        self.q = q
        self.r = r

    def move_player_to(self, q:int, r:int):
        self.q = q
        self.r = r
    