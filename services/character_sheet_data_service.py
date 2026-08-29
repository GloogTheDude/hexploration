from __future__ import annotations

import re
from io import BytesIO

from pypdf import PdfReader, PdfWriter
from sqlalchemy.orm import Session

from db.models import Character, CharacterSheetDataVersion
from dto.character_sheet_data_dto import CharacterSheetForm
from repositories.character_sheet_data_repository import CharacterSheetDataRepository
from services.character_sheet_service import CharacterSheetService, CharacterSheetTemplateError


class CharacterSheetDataNotFoundError(Exception):
    pass


class CharacterSheetDataForbiddenError(Exception):
    pass


class CharacterSheetDataExportError(Exception):
    pass


# The 2014 Wizards sheet has historically shipped with small differences in
# field naming (spaces/casing). Aliases are normalized before matching so the
# exporter is resilient to those differences.
PDF_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "character_name": ("CharacterName", "Character Name", "CharacterName 2", "Character Name 2"),
    "character_class_level": ("ClassLevel", "Class & Level", "ClassLevel "),
    "background": ("Background",),
    "player_name": ("PlayerName", "Player Name"),
    "race": ("Race", "Race "),
    "alignment": ("Alignment",),
    "experience_points": ("XP", "ExperiencePoints", "Experience Points"),
    "strength": ("STR", "Strength"),
    "strength_mod": ("STRmod", "StrengthMod", "Strength Modifier"),
    "dexterity": ("DEX", "Dexterity"),
    "dexterity_mod": ("DEXmod", "DEXmod ", "DexterityMod", "Dexterity Modifier"),
    "constitution": ("CON", "Constitution"),
    "constitution_mod": ("CONmod", "ConstitutionMod", "Constitution Modifier"),
    "intelligence": ("INT", "Intelligence"),
    "intelligence_mod": ("INTmod", "IntelligenceMod", "Intelligence Modifier"),
    "wisdom": ("WIS", "Wisdom"),
    "wisdom_mod": ("WISmod", "WisdomMod", "Wisdom Modifier"),
    "charisma": ("CHA", "Charisma"),
    "charisma_mod": ("CHamod", "CHAmod", "CharismaMod", "Charisma Modifier"),
    "armor_class": ("AC", "ArmorClass", "Armor Class"),
    "initiative": ("Initiative",),
    "speed": ("Speed",),
    "proficiency_bonus": ("ProfBonus", "ProficiencyBonus", "Proficiency Bonus"),
    "max_hp": ("HPMax", "HitPointMaximum", "Hit Point Maximum"),
    "current_hp": ("HPCurrent", "CurrentHitPoints", "Current Hit Points"),
    "temp_hp": ("HPTemp", "TemporaryHitPoints", "Temporary Hit Points"),
    "hit_dice_total": ("HDTotal", "HitDiceTotal", "Hit Dice Total"),
    "hit_dice_current": ("HD", "HitDice", "Hit Dice"),
    "passive_perception": ("Passive", "PassivePerception", "Passive Wisdom Perception"),
    "personality_traits": ("PersonalityTraits", "PersonalityTraits ", "Personality Traits"),
    "ideals": ("Ideals",),
    "bonds": ("Bonds",),
    "flaws": ("Flaws",),
    "attacks_spellcasting": ("AttacksSpellcasting", "Attacks & Spellcasting", "Attacks and Spellcasting"),
    "equipment": ("Equipment",),
    "proficiencies_languages": ("ProficienciesLang", "OtherProficienciesLanguages", "Other Proficiencies & Languages"),
    "features_traits": ("Features and Traits", "FeaturesAndTraits", "Features & Traits"),
    "age": ("Age",),
    "height": ("Height",),
    "weight": ("Weight",),
    "eyes": ("Eyes",),
    "skin": ("Skin",),
    "hair": ("Hair",),
    "appearance": ("Character Appearance", "CharacterAppearance"),
    "allies_organizations": ("Allies", "Allies & Organizations", "AlliesOrganizations"),
    "backstory": ("Backstory", "Character Backstory", "CharacterBackstory"),
    "additional_features_traits": ("Feat+Traits", "Additional Features & Traits", "AdditionalFeaturesTraits"),
    "treasure": ("Treasure",),
}


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _ability_mod(score: int) -> int:
    return (score - 10) // 2


def _signed(value: int | None) -> str:
    if value is None:
        return ""
    return f"{value:+d}"


class CharacterSheetDataService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CharacterSheetDataRepository(db)

    def require_owner(self, character_id: int, user_id: int) -> Character:
        character = self.db.get(Character, character_id)
        if character is None:
            raise CharacterSheetDataNotFoundError("Character not found")
        if character.owner_user_id != user_id:
            raise CharacterSheetDataForbiddenError("A player can only manage their own character sheet.")
        return character

    def initialize(self, character_id: int, user_id: int) -> CharacterSheetDataVersion:
        character = self.require_owner(character_id, user_id)
        current = self.repo.current(character_id)
        if current is not None:
            return current

        form = CharacterSheetForm(
            character_name=character.name,
            player_name=character.owner.username if character.owner else "",
            race=character.race or "",
            character_class=character.character_class or "",
            level=character.level or 1,
            notes=character.description or "",
        )
        return self._save(character, form)

    def save(self, character_id: int, user_id: int, form: CharacterSheetForm) -> CharacterSheetDataVersion:
        character = self.require_owner(character_id, user_id)
        return self._save(character, form)

    def _save(self, character: Character, form: CharacterSheetForm) -> CharacterSheetDataVersion:
        version_number = self.repo.next_version(character.id)
        self.repo.clear_current(character.id)
        version = CharacterSheetDataVersion(
            character_id=character.id,
            version=version_number,
            data=form.model_dump(mode="json"),
            campaign_game_minute=character.current_game_minute,
            is_current=True,
        )
        self.repo.add(version)

        # Keep the compact Character card synchronized with the authoritative
        # sheet identity fields.
        character.name = form.character_name.strip() or character.name
        character.race = form.race.strip() or None
        character.character_class = form.character_class.strip() or None
        character.level = form.level

        self.db.commit()
        self.db.refresh(version)
        return version

    def current(self, character_id: int, user_id: int) -> CharacterSheetDataVersion:
        self.require_owner(character_id, user_id)
        current = self.repo.current(character_id)
        if current is None:
            raise CharacterSheetDataNotFoundError("Character sheet has not been initialized")
        return current

    def history(self, character_id: int, user_id: int) -> list[CharacterSheetDataVersion]:
        self.require_owner(character_id, user_id)
        return self.repo.history(character_id)

    def by_version(self, character_id: int, version: int, user_id: int) -> CharacterSheetDataVersion:
        self.require_owner(character_id, user_id)
        item = self.repo.by_version(character_id, version)
        if item is None:
            raise CharacterSheetDataNotFoundError("Character sheet version not found")
        return item

    def export_pdf(self, item: CharacterSheetDataVersion) -> bytes:
        try:
            template = CharacterSheetService(self.db)._ensure_template()
            reader = PdfReader(str(template))
            writer = PdfWriter()
            writer.clone_document_from_reader(reader)
            fields = reader.get_fields() or {}
            pdf_values = self._pdf_values(CharacterSheetForm.model_validate(item.data))
            resolved = self._resolve_pdf_fields(fields.keys(), pdf_values)
            if not resolved:
                raise CharacterSheetDataExportError(
                    "The configured PDF template contains no recognized character-sheet fields."
                )
            writer.update_page_form_field_values(
                None,
                resolved,
                auto_regenerate=False,
                flatten=True,
            )
            out = BytesIO()
            writer.write(out)
            return out.getvalue()
        except CharacterSheetTemplateError:
            raise
        except CharacterSheetDataExportError:
            raise
        except Exception as exc:
            raise CharacterSheetDataExportError("Unable to generate the character-sheet PDF.") from exc

    @staticmethod
    def _pdf_values(form: CharacterSheetForm) -> dict[str, str]:
        class_level = " ".join(x for x in [form.character_class.strip(), f"{form.level}" if form.level else ""] if x)
        return {
            "character_name": form.character_name,
            "character_class_level": class_level,
            "background": form.background,
            "player_name": form.player_name,
            "race": form.race,
            "alignment": form.alignment,
            "experience_points": "" if form.experience_points is None else str(form.experience_points),
            "strength": str(form.strength), "strength_mod": _signed(_ability_mod(form.strength)),
            "dexterity": str(form.dexterity), "dexterity_mod": _signed(_ability_mod(form.dexterity)),
            "constitution": str(form.constitution), "constitution_mod": _signed(_ability_mod(form.constitution)),
            "intelligence": str(form.intelligence), "intelligence_mod": _signed(_ability_mod(form.intelligence)),
            "wisdom": str(form.wisdom), "wisdom_mod": _signed(_ability_mod(form.wisdom)),
            "charisma": str(form.charisma), "charisma_mod": _signed(_ability_mod(form.charisma)),
            "armor_class": "" if form.armor_class is None else str(form.armor_class),
            "initiative": _signed(form.initiative),
            "speed": form.speed,
            "proficiency_bonus": _signed(form.proficiency_bonus),
            "max_hp": "" if form.max_hp is None else str(form.max_hp),
            "current_hp": "" if form.current_hp is None else str(form.current_hp),
            "temp_hp": "" if form.temp_hp is None else str(form.temp_hp),
            "hit_dice_total": form.hit_dice_total,
            "hit_dice_current": form.hit_dice_current,
            "passive_perception": "" if form.passive_perception is None else str(form.passive_perception),
            "personality_traits": form.personality_traits,
            "ideals": form.ideals,
            "bonds": form.bonds,
            "flaws": form.flaws,
            "attacks_spellcasting": form.attacks_spellcasting,
            "equipment": form.equipment,
            "proficiencies_languages": form.proficiencies_languages,
            "features_traits": form.features_traits,
            "age": form.age, "height": form.height, "weight": form.weight,
            "eyes": form.eyes, "skin": form.skin, "hair": form.hair,
            "appearance": form.appearance,
            "allies_organizations": form.allies_organizations,
            "backstory": form.backstory,
            "additional_features_traits": form.additional_features_traits,
            "treasure": form.treasure,
        }

    @staticmethod
    def _resolve_pdf_fields(actual_names, logical_values: dict[str, str]) -> dict[str, str]:
        normalized_actual = {_norm(name): name for name in actual_names}
        resolved: dict[str, str] = {}
        for logical, value in logical_values.items():
            aliases = PDF_FIELD_ALIASES.get(logical, ())
            for alias in aliases:
                actual = normalized_actual.get(_norm(alias))
                if actual is not None:
                    resolved[actual] = value
        return resolved
