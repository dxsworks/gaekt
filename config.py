"""config.json 또는 환경변수에서 Gemini 설정을 읽는다."""
import json
import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "gemini-3.8-flash"
DEFAULT_PATH = Path(__file__).with_name("config.json")


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    api_key: str
    model: str = DEFAULT_MODEL


def load_config(path: Path | None = None) -> Config:
    """config.json(api_key, model) → 환경변수 GEMINI_API_KEY 순으로 읽는다."""
    path = DEFAULT_PATH if path is None else Path(path)
    data: dict = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ConfigError(f"{path.name} 파싱 실패: {e}") from e
        if not isinstance(data, dict):
            raise ConfigError(f"{path.name}은 JSON 객체여야 합니다")

    api_key = data.get("api_key") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ConfigError("API 키 없음: config.json의 api_key 또는 환경변수 GEMINI_API_KEY 필요")

    model = data.get("model") or DEFAULT_MODEL
    return Config(api_key=api_key, model=model)
