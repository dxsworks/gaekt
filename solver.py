"""Gemini에게 캡처 이미지를 보내 옳은 선지 라벨을 받아온다."""
import json
import re

from google import genai
from google.genai import types

from config import Config

PROMPT = """화면 캡처에는 문제 지문 없이 선지(보기)만 있다.
각 선지는 독립된 서술문이다. 각 서술문이 참인지 거짓인지 스스로 판단해서
참인 선지만 골라라. 참인 선지가 여러 개일 수 있고, 하나도 없을 수도 있다.

선지에 오타나 띄어쓰기 오류가 있을 수 있다. 글자 그대로가 아니라 문맥상 명백히 의도된 의미로 해석해서 판단하라.

선지는 대부분 자바(Java) 프로그래밍 관련 서술문이다. 자바 언어 명세와 표준 교과서 기준으로 엄밀하게 판단하라.
한 단어만 바뀌어도 거짓이 되는 함정 선지(예: '클래스 수만큼'을 'public 클래스 수만큼'으로 바꾼 것)에 주의하라.
선지 옆의 체크박스나 표시 상태는 정답과 무관하니 무시하고 문장 내용만으로 판단하라.

라벨은 화면에 표시된 그대로 사용한다:
- 숫자 라벨(1, 2, 3, ... 또는 ①, ②, ③, ...)은 "1", "2", "3" 형식으로
- 한글 자모 라벨(ㄱ, ㄴ, ㄷ, ㄹ, ...)은 "ㄱ", "ㄴ" 형식으로
- 알파벳 라벨(a, b, c, ... 또는 A, B, C, ...)은 화면에 보이는 대소문자 그대로 "a", "b" 형식으로
라벨이 화면에 "1.", "1)", "(1)", "ㄱ." 처럼 꾸밈 기호와 함께 표시되어도
반환할 때는 꾸밈 기호를 뺀 "1", "ㄱ" 형식으로 반환한다.
버튼, 타이머, 메뉴 등 선지가 아닌 화면 텍스트는 무시한다.

출력은 다음 JSON 객체 하나만, 다른 텍스트 없이:
{"correct": ["1", "3"]}
"""

_CIRCLED = {c: str(i + 1) for i, c in enumerate("①②③④⑤⑥⑦⑧⑨⑩")}
_JAMO_ORDER = "ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ"
_JAMO = frozenset(_JAMO_ORDER)
_DIGITS = re.compile(r"[1-9][0-9]?")
_ALPHA = re.compile(r"[A-Za-z]")
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class SolverError(Exception):
    pass


def _normalize(label) -> str:
    if isinstance(label, bool) or not isinstance(label, (str, int)):
        raise SolverError(f"라벨 형식 오류: {label!r}")
    s = str(label).strip().strip(".)(）（")
    s = _CIRCLED.get(s, s)
    if _DIGITS.fullmatch(s) or s in _JAMO or _ALPHA.fullmatch(s):
        return s
    raise SolverError(f"알 수 없는 라벨: {label!r}")


def _sort_key(label: str):
    if label.isdigit():
        return (0, int(label))
    if label in _JAMO:
        return (1, _JAMO_ORDER.index(label))
    return (2, label.lower())


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


_RETRY_SECS = re.compile(r"retry in ([0-9.]+)s|retryDelay['\"]?\s*:\s*['\"]?([0-9.]+)s")


def _describe_api_error(e: Exception) -> str:
    """SDK 예외를 툴팁에 넣을 만한 한 줄로 요약한다."""
    text = str(e)
    code = getattr(e, "code", None)
    if code == 429 or "RESOURCE_EXHAUSTED" in text:
        m = _RETRY_SECS.search(text)
        secs = next((g for g in (m.groups() if m else ()) if g), None)
        wait = f" {float(secs):.0f}초 후" if secs else " 잠시 후"
        return f"API 요청 한도 초과:{wait} 다시 클릭하세요"
    if code == 503 or "UNAVAILABLE" in text:
        return "Gemini 서버 과부하(503): 잠시 후 다시 클릭하세요"
    return f"Gemini 호출 실패: {text[:200]}"


def solve(png_bytes: bytes, cfg: Config) -> list[str]:
    """캡처 PNG를 Gemini에 보내 옳은 선지 라벨 리스트를 반환. 실패 시 SolverError."""
    try:
        client = genai.Client(api_key=cfg.api_key, http_options=types.HttpOptions(timeout=60_000))
        response = client.models.generate_content(
            model=cfg.model,
            contents=[
                types.Part.from_bytes(data=png_bytes, mime_type="image/png"),
                PROMPT,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0,
            ),
        )
    except Exception as e:
        raise SolverError(_describe_api_error(e)) from e
    if not response.text:
        raise SolverError(f"빈 응답: {getattr(response, 'prompt_feedback', None)}")
    return parse_response(response.text)
