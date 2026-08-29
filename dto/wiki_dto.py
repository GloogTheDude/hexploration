from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExpeditionReportCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    publish_knowledge: bool = True


class ExpeditionReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    expedition_id: int
    published_game_minute: int
    title: str
    content: str
    created_at: datetime


class WikiRevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    page_id: int
    revision: int
    effective_from_game_minute: int
    source_report_id: int | None
    content: str
    created_at: datetime


class WikiPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    slug: str
    title: str
    category: str | None


class WikiPageStateResponse(BaseModel):
    page: WikiPageResponse
    as_of_game_minute: int | None
    revision: WikiRevisionResponse


class CampaignWikiResponse(BaseModel):
    campaign_id: int
    as_of_game_minute: int | None
    pages: list[WikiPageStateResponse]


class ExpeditionReportPublishResponse(BaseModel):
    report: ExpeditionReportResponse
    published_pages: list[WikiPageStateResponse]


class RecallRequest(BaseModel):
    character_id: int = Field(gt=0)
    page_id: int = Field(gt=0)


class RecallRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    expedition_id: int
    character_id: int
    page_id: int
    knowledge_cutoff_game_minute: int
    recalled_at_game_minute: int


class RecalledPageResponse(BaseModel):
    recall: RecallRecordResponse
    page: WikiPageResponse
    revision: WikiRevisionResponse


class RecallStatusResponse(BaseModel):
    character_id: int
    expedition_id: int
    limit: int
    used: int
    remaining: int
    knowledge_cutoff_game_minute: int


class RecallSearchResponse(BaseModel):
    expedition_id: int
    character_id: int
    knowledge_cutoff_game_minute: int
    results: list[WikiPageStateResponse]


class ExpeditionRecallLibraryResponse(BaseModel):
    expedition_id: int
    pages: list[RecalledPageResponse]
