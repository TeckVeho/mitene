from typing import Optional

from pydantic import BaseModel, Field, field_validator

_ALLOWED_VIDEO_LANGUAGES = frozenset({"ja", "vi"})
_LANGUAGE_ORDER = ("ja", "vi")


class WikiSyncDirectoryRequest(BaseModel):
    path: Optional[str] = ""
    paths: Optional[list[str]] = None
    languages: list[str] = Field(default_factory=lambda: ["ja", "vi"])

    @field_validator("languages", mode="before")
    @classmethod
    def validate_languages(cls, value: object) -> list[str]:
        if value is None:
            return ["ja", "vi"]
        if not isinstance(value, list):
            raise ValueError("languages must be a list")
        if len(value) == 0:
            raise ValueError("言語を1つ以上選択してください")
        seen: set[str] = set()
        for lang in value:
            if not isinstance(lang, str) or lang not in _ALLOWED_VIDEO_LANGUAGES:
                raise ValueError(f"Unsupported language: {lang!r}")
            seen.add(lang)
        return [lang for lang in _LANGUAGE_ORDER if lang in seen]
