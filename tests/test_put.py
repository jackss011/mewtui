from mewtui import _crop_line, _sanitize


def test_crop_fits():
    assert _crop_line("hello", 2, 10) == (2, "hello")


def test_crop_right_edge():
    assert _crop_line("hello", 8, 10) == (8, "he")


def test_crop_left_edge():
    assert _crop_line("hello", -2, 10) == (0, "llo")


def test_crop_both_edges():
    assert _crop_line("abcdefgh", -2, 3) == (0, "cde")


def test_crop_fully_outside():
    assert _crop_line("hello", 10, 10) == (10, "")
    assert _crop_line("hello", -5, 10) == (0, "")


def test_sanitize_replaces_control_characters():
    assert _sanitize("a\tb\x1b[0mc\rd\x7fe\x9bf") == "a�b�[0mc�d�e�f"


def test_sanitize_keeps_normal_text():
    assert _sanitize("héllo 世界") == "héllo 世界"
