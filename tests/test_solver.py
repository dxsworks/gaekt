import pytest

from solver import SolverError, parse_response


def test_parses_numeric_labels():
    assert parse_response('{"correct": ["1", "3", "4"]}') == ["1", "3", "4"]


def test_sorts_numeric_labels_and_dedupes():
    assert parse_response('{"correct": ["4", "1", "3", "1"]}') == ["1", "3", "4"]


def test_normalizes_circled_numbers_and_ints():
    assert parse_response('{"correct": ["①", "③", 5]}') == ["1", "3", "5"]


def test_parses_and_sorts_jamo_labels():
    assert parse_response('{"correct": ["ㄷ", "ㄱ"]}') == ["ㄱ", "ㄷ"]


def test_empty_list_is_valid():
    assert parse_response('{"correct": []}') == []


def test_strips_markdown_fence():
    assert parse_response('```json\n{"correct": ["2"]}\n```') == ["2"]


@pytest.mark.parametrize("bad", [
    "not json",
    '{"answer": ["1"]}',
    '{"correct": "1"}',
    '{"correct": [{"a": 1}]}',
    '{"correct": ["hello"]}',
    "",
])
def test_rejects_malformed(bad):
    with pytest.raises(SolverError):
        parse_response(bad)
