import pytest

from mewtui import _CSS_NAMES, Ansi, Indexed, Rgb, _parse_color


def test_default():
    assert _parse_color("default") is None
    assert _parse_color(" Default ") is None


def test_terminal_colors_pass_through():
    assert _parse_color(Ansi(3)) == Ansi(3)
    assert _parse_color(Indexed(200)) == Indexed(200)
    assert _parse_color(Rgb(1, 2, 3)) == Rgb(1, 2, 3)


@pytest.mark.parametrize(
    ("text", "rgb"),
    [
        ("#f80", Rgb(255, 136, 0)),
        ("#FF8800", Rgb(255, 136, 0)),
        ("#000", Rgb(0, 0, 0)),
        ("rgb(10, 20, 30)", Rgb(10, 20, 30)),
        ("RGB( 255,0 , 7 )", Rgb(255, 0, 7)),
        ("  red  ", Rgb(255, 0, 0)),
        ("RebeccaPurple", Rgb(102, 51, 153)),
        ("gray", Rgb(128, 128, 128)),
        ("grey", Rgb(128, 128, 128)),
        ("darkslategrey", Rgb(47, 79, 79)),
    ],
)
def test_css_colors(text, rgb):
    assert _parse_color(text) == rgb


def test_all_148_css_names():
    assert len(_CSS_NAMES) == 148
    for name in _CSS_NAMES:
        assert isinstance(_parse_color(name), Rgb)


@pytest.mark.parametrize(
    "text",
    [
        "transparent",
        "#ff88",
        "#ff880000",
        "#ggg",
        "rgb(256, 0, 0)",
        "rgb(10%, 0, 0)",
        "rgb(1, 2)",
        "rgba(1, 2, 3, 0.5)",
        "hsl(0, 100%, 50%)",
        "notacolor",
        "",
    ],
)
def test_invalid_css_raises(text):
    with pytest.raises(ValueError):
        _parse_color(text)


@pytest.mark.parametrize(
    "make",
    [lambda: Ansi(16), lambda: Ansi(-1), lambda: Indexed(256), lambda: Rgb(0, 0, 300)],
)
def test_out_of_range_raises(make):
    with pytest.raises(ValueError):
        make()
