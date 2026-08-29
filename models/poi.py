class POI:
    def __init__(
        self,
        name: str,
        is_landmark: bool = False,
        discovery_dc: int | None = None,
        skill: str | None = None,
        description: str | None = None,
    ):
        self.name = name
        self.is_landmark = is_landmark
        self.discovery_dc = discovery_dc
        self.skill = skill
        self.description = description
