"""Gemini에게 캡처 이미지를 보내 옳은 선지 라벨을 받아온다."""
import json
import re

from config import Config

PROMPT = """화면 캡처에는 문제 지문 없이 선지(보기)만 있다.
각 선지는 독립된 서술문이다. 각 서술문이 참인지 거짓인지 스스로 판단해서
참인 선지만 골라라. 참인 선지가 여러 개일 수 있고, 하나도 없을 수도 있다.

라벨은 화면에 표시된 그대로 사용한다:
- 숫자 라벨(1, 2, 3, ... 또는 ①, ②, ③, ...)은 "1", "2", "3" 형식으로
- 한글 자모 라벨(ㄱ, ㄴ, ㄷ, ㄹ, ...)은 "ㄱ", "ㄴ" 형식으로

출력은 다음 JSON 객체 하나만, 다른 텍스트 없이:
{"correct": ["1", "3"]}
"""

_CIRCLED = {c: str(i + 1) for i, c in enumerate("①②③④⑤⑥⑦⑧⑨⑩")}
_JAMO_ORDER = "ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ"
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class SolverError(Exception):
    pass


def _normalize(label) -> str:
    if isinstance(label, bool) or not isinstance(label, (str, int)):
        raise SolverError(f"라벨 형식 오류: {label!r}")
    s = str(label).strip()
    s = _CIRCLED.get(s, s)
    if s.isdigit() or s in _JAMO_ORDER:
        return s
    raise SolverError(f"알 수 없는 라벨: {label!r}")


def _sort_key(label: str):
    if label.isdigit():
        return (0, int(label))
    return (1, _JAMO_ORDER.index(label))


def parse_response(text: str) -> list[str]:
    """Gemini 응답 텍스트 → 정렬·중복제거된 라벨 리스트. 형식이 어긋나면 SolverError."""
    cleaned = _FENCE.sub("", (text or "").strip()).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise SolverError(f"JSON 아님: {cleaned[:80]!r}") from e
    if not isinstance(data, dict) or not isinstance(data.get("correct"), list):
        raise SolverError(f"'correct' 리스트 없음: {cleaned[:80]!r}")
    labels = {_normalize(x) for x in data["correct"]}
    return sorted(labels, key=_sort_key)
