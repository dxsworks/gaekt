from types import SimpleNamespace

import pytest

import solver
from config import Config
from solver import SolverError, parse_response


def test_parses_numeric_labels():
    assert parse_response('{"correct": ["1", "3", "4"]}') == ["1", "3", "4"]


def test_sorts_numeric_labels_and_dedupes():
    assert parse_response('{"correct": ["4", "1", "3", "1"]}') == ["1", "3", "4"]


def test_normalizes_circled_numbers_and_ints():
    assert parse_response('{"correct": ["①", "③", 5]}') == ["1", "3", "5"]


def test_parses_and_sorts_jamo_labels():
    assert parse_response('{"correct": ["ㄷ", "ㄱ"]}') == ["ㄱ", "ㄷ"]


def test_parses_and_sorts_alpha_labels():
    assert parse_response('{"correct": ["e", "b.", "C"]}') == ["b", "C", "e"]


def test_rejects_multi_letter_alpha():
    with pytest.raises(SolverError):
        parse_response('{"correct": ["ab"]}')


def test_empty_list_is_valid():
    assert parse_response('{"correct": []}') == []


def test_strips_markdown_fence():
    assert parse_response('```json\n{"correct": ["2"]}\n```') == ["2"]


def test_strips_label_decorations():
    assert parse_response('{"correct": ["1.", "(3)", "ㄱ)"]}') == ["1", "3", "ㄱ"]


@pytest.mark.parametrize("bad", [
    "not json",
    '{"answer": ["1"]}',
    '{"correct": "1"}',
    '{"correct": [{"a": 1}]}',
    '{"correct": ["hello"]}',
    "",
    '{"correct": [""]}',
    '{"correct": ["ㄱㄴ"]}',
    '{"correct": [true]}',
    '{"correct": ["²"]}',
    '{"correct": ["0"]}',
    '{"correct": ["999"]}',
])
def test_rejects_malformed(bad):
    with pytest.raises(SolverError):
        parse_response(bad)


def test_solve_sends_image_and_prompt_and_parses(monkeypatch):
    captured = {}

    class FakeModels:
        def generate_content(self, *, model, contents, config):
            captured["model"] = model
            captured["contents"] = contents
            captured["config"] = config
            return SimpleNamespace(text='{"correct": ["2", "5"]}')

    class FakeClient:
        def __init__(self, *, api_key, **kwargs):
            captured["api_key"] = api_key
            captured["http_options"] = kwargs.get("http_options")
            self.models = FakeModels()

    monkeypatch.setattr(solver.genai, "Client", FakeClient)

    result = solver.solve(b"\x89PNG-fake", Config(api_key="k", model="m"))

    assert result == ["2", "5"]
    assert captured["api_key"] == "k"
    assert captured["model"] == "m"
    assert captured["http_options"].timeout == 60_000
    assert captured["config"].response_mime_type == "application/json"
    assert captured["config"].temperature == 0
    image_part, prompt = captured["contents"]
    assert image_part.inline_data.mime_type == "image/png"
    assert image_part.inline_data.data == b"\x89PNG-fake"
    assert prompt == solver.PROMPT


def test_solve_wraps_api_errors(monkeypatch):
    def boom(**kw):
        raise RuntimeError("boom")

    class FakeClient:
        def __init__(self, *, api_key, **kwargs):
            self.models = SimpleNamespace(generate_content=boom)

    monkeypatch.setattr(solver.genai, "Client", FakeClient)
    with pytest.raises(solver.SolverError, match="boom"):
        solver.solve(b"png", Config(api_key="k"))


def test_describe_429_with_retry_delay():
    msg = ("429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'Quota exceeded. "
           "Please retry in 33.12674579s.', 'details': [{'retryDelay': '33s'}]}}")
    out = solver._describe_api_error(RuntimeError(msg))
    assert out == "API 요청 한도 초과: 33초 후 다시 클릭하세요"


def test_describe_503():
    assert "503" in solver._describe_api_error(RuntimeError("503 UNAVAILABLE. high demand"))


def test_describe_other_error_is_truncated():
    out = solver._describe_api_error(RuntimeError("x" * 500))
    assert out.startswith("Gemini 호출 실패: ") and len(out) < 230
