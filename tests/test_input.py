from mewtui import Char, _parse_input


def test_printable():
    assert _parse_input("aé ") == [Char("a"), Char("é"), Char(" ")]


def test_ctrl_letters():
    assert _parse_input("\x01\x03\x1a") == [
        Char("a", ctrl=True),
        Char("c", ctrl=True),
        Char("z", ctrl=True),
    ]


def test_ctrl_space():
    assert _parse_input("\x00") == [Char(" ", ctrl=True)]


def test_not_yet_handled_input_is_dropped():
    assert _parse_input("\r\t\x7f\x1b") == []
