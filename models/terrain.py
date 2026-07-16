class Terrain:
    def __init__(self, type:str,color: str, visibility_score:int,elevation:int):
        self.type = type
        self.color = color
        self.visibility_score = visibility_score
        self.elevation = elevation
    
    def to_dict(self):
        return {
            "type": self.type,
            "color": self.color,
            "visibility_score": self.visibility_score,
            "elevation": self.elevation
        }