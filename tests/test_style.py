from mewtui import Ansi, Indexed, Rgb, Style, _sgr


def test_default_style_is_a_plain_reset():
    assert _sgr(Style()) == "\x1b[0m"


def test_bold_red_example_from_the_spec():
    assert _sgr(Style(fg=Rgb(255, 0, 0), bold=True)) == "\x1b[0;1;38;2;255;0;0m"


def test_all_attributes():
    style = Style(
        bold=True,
        dim=True,
        italic=True,
        underline=True,
        reverse=True,
        strikethrough=True,
    )
    assert _sgr(style) == "\x1b[0;1;2;3;4;7;9m"


def test_ansi_colors():
    assert _sgr(Style(fg=Ansi(1), bg=Ansi(7))) == "\x1b[0;31;47m"
    assert _sgr(Style(fg=Ansi(9), bg=Ansi(15))) == "\x1b[0;91;107m"


def test_indexed_and_rgb_colors():
    assert (
        _sgr(Style(fg=Indexed(208), bg=Rgb(1, 2, 3))) == "\x1b[0;38;5;208;48;2;1;2;3m"
    )
