class Terrain:
    def __init__(
        self,
        type: str,
        color: str,
        visibility_score: int,
        elevation: int,
        travel_cost: float = 1.0,
    ):
        if travel_cost <= 0:
            raise ValueError("travel_cost must be greater than 0")

        self.type = type
        self.color = color
        self.visibility_score = visibility_score
        self.elevation = elevation
        self.travel_cost = float(travel_cost)

    def to_dict(self):
        return {
            "type": self.type,
            "color": self.color,
            "visibility_score": self.visibility_score,
            "elevation": self.elevation,
            "travel_cost": self.travel_cost,
        }
