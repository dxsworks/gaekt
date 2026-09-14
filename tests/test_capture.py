from capture import capture_primary


def test_returns_png_bytes():
    data = capture_primary()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(data) > 1000
