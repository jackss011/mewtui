from mewtui import _crop_line, _layout, _sanitize


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


# _layout(text, x, y, width, height, wrap) -> (pieces, cursor), on a 10x5 window.


def layout(text, x, y, wrap):
    return _layout(text, x, y, 10, 5, wrap)


def test_no_wrap_uses_first_line_only():
    assert layout("abc\ndef", 2, 1, False) == ([(2, 1, "abc")], (5, 1))


def test_no_wrap_crop_leaves_cursor_at_edge():
    assert layout("hello", 8, 0, False) == ([(8, 0, "he")], (10, 0))


def test_nothing_visible_gives_no_cursor():
    assert layout("hello", 10, 0, False) == ([], None)
    assert layout("hello", 0, 5, False) == ([], None)
    assert layout("", 0, 0, True) == ([], None)


def test_wrap_on_newline_keeps_start_column():
    assert layout("ab\ncd", 3, 1, True) == ([(3, 1, "ab"), (3, 2, "cd")], (5, 2))


def test_wrap_at_right_edge():
    assert layout("abcdefgh", 6, 0, True) == (
        [(6, 0, "abcd"), (6, 1, "efgh")],
        (10, 1),
    )


def test_wrap_line_ending_at_edge_keeps_cursor_on_that_row():
    assert layout("abcd", 6, 0, True) == ([(6, 0, "abcd")], (10, 0))


def test_wrap_empty_line_takes_a_row():
    assert layout("a\n\nb", 0, 0, True) == ([(0, 0, "a"), (0, 2, "b")], (1, 2))


def test_wrap_trailing_newline_leaves_cursor_after_last_character():
    assert layout("ab\n", 0, 0, True) == ([(0, 0, "ab")], (2, 0))


def test_wrap_drops_lines_past_the_bottom():
    pieces, cursor = layout("1\n2\n3\n4", 0, 3, True)
    assert pieces == [(0, 3, "1"), (0, 4, "2")]
    assert cursor == (1, 4)


def test_wrap_skips_rows_above_the_window():
    assert layout("1\n2\n3", 0, -2, True) == ([(0, 0, "3")], (1, 0))


def test_wrap_from_left_of_the_window():
    # Each row spans 12 columns from x=-2; the first 2 are off-screen.
    assert layout("abcdefghijklmno", -2, 0, True) == (
        [(0, 0, "cdefghijkl"), (0, 1, "o")],
        (1, 1),
    )


def test_wrap_sanitizes_but_keeps_newlines():
    assert layout("a\tb\nc", 0, 0, True) == (
        [(0, 0, "a�b"), (0, 1, "c")],
        (1, 1),
    )
