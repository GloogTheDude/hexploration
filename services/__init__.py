"""Service package.

Keep package import side effects minimal. Concrete services should normally be
imported from their module (``services.world_event_service`` etc.). The lazy
attributes below preserve the previous convenience imports without importing
optional dependencies such as the password hasher when an unrelated service is
loaded by tests or scripts.
"""

__all__ = ["UserService", "CampaignService", "CharacterService"]


def __getattr__(name: str):
    if name == "UserService":
        from .user_service import UserService

        return UserService
    if name == "CampaignService":
        from .campaign_service import CampaignService

        return CampaignService
    if name == "CharacterService":
        from .character_service import CharacterService

        return CharacterService
    raise AttributeError(name)
