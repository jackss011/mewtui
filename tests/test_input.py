import pytest

from mewtui import Char, Key, KeyName, _parse_input, _parse_leftover


def parse(text):
    """Parse text that is expected to be complete."""
    events, leftover = _parse_input(text)
    assert leftover == ""
    return events


def test_printable():
    assert parse("aé ") == [Char("a"), Char("é"), Char(" ")]


def test_ctrl_letters():
    assert parse("\x01\x03\x1a") == [
        Char("a", ctrl=True),
        Char("c", ctrl=True),
        Char("z", ctrl=True),
    ]


def test_ctrl_space():
    assert parse("\x00") == [Char(" ", ctrl=True)]


def test_enter_tab_backspace():
    assert parse("\r\t\x7f") == [
        Key(KeyName.ENTER),
        Key(KeyName.TAB),
        Key(KeyName.BACKSPACE),
    ]


def test_alt_combinations():
    assert parse("\x1bx\x1b\x03\x1b\r") == [
        Char("x", alt=True),
        Char("c", ctrl=True, alt=True),
        Key(KeyName.ENTER, alt=True),
    ]


@pytest.mark.parametrize(
    ("text", "name"),
    [
        ("\x1b[A", KeyName.UP),
        ("\x1b[B", KeyName.DOWN),
        ("\x1b[C", KeyName.RIGHT),
        ("\x1b[D", KeyName.LEFT),
        ("\x1bOA", KeyName.UP),
        ("\x1b[H", KeyName.HOME),
        ("\x1bOH", KeyName.HOME),
        ("\x1b[1~", KeyName.HOME),
        ("\x1b[7~", KeyName.HOME),
        ("\x1b[F", KeyName.END),
        ("\x1bOF", KeyName.END),
        ("\x1b[4~", KeyName.END),
        ("\x1b[8~", KeyName.END),
        ("\x1b[2~", KeyName.INSERT),
        ("\x1b[3~", KeyName.DELETE),
        ("\x1b[5~", KeyName.PAGE_UP),
        ("\x1b[6~", KeyName.PAGE_DOWN),
        ("\x1bOP", KeyName.F1),
        ("\x1bOS", KeyName.F4),
        ("\x1b[11~", KeyName.F1),
        ("\x1b[14~", KeyName.F4),
        ("\x1b[15~", KeyName.F5),
        ("\x1b[17~", KeyName.F6),
        ("\x1b[21~", KeyName.F10),
        ("\x1b[23~", KeyName.F11),
        ("\x1b[24~", KeyName.F12),
    ],
)
def test_named_keys(text, name):
    assert parse(text) == [Key(name)]


def test_shift_tab():
    assert parse("\x1b[Z") == [Key(KeyName.TAB, shift=True)]


def test_modifiers():
    assert parse("\x1b[1;5A\x1b[1;2B\x1b[1;3C\x1b[1;8D\x1b[3;5~") == [
        Key(KeyName.UP, ctrl=True),
        Key(KeyName.DOWN, shift=True),
        Key(KeyName.RIGHT, alt=True),
        Key(KeyName.LEFT, ctrl=True, alt=True, shift=True),
        Key(KeyName.DELETE, ctrl=True),
    ]


def test_unknown_sequences_are_dropped():
    # Unknown CSI final byte, CSI with intermediate byte, private CSI, unknown
    # tilde number, unknown SS3 key, invalid modifier.
    text = "\x1b[5n\x1b[1 q\x1b[?1u\x1b[99~\x1bOz\x1b[1;0A"
    assert parse(text + "a") == [Char("a")]


def test_several_events_in_one_read():
    assert parse("a\x1b[Ab") == [Char("a"), Key(KeyName.UP), Char("b")]


@pytest.mark.parametrize("tail", ["\x1b", "\x1b[", "\x1b[1;5", "\x1bO"])
def test_unfinished_sequence_is_left_over(tail):
    assert _parse_input("a" + tail) == ([Char("a")], tail)


def test_leftover_completed_by_next_read():
    assert _parse_input("\x1b[1;") == ([], "\x1b[1;")
    assert _parse_input("\x1b[1;" + "5A") == ([Key(KeyName.UP, ctrl=True)], "")


def test_lone_escape_after_timeout():
    assert _parse_leftover("\x1b") == [Key(KeyName.ESCAPE)]


def test_unfinished_sequence_dropped_after_timeout():
    assert _parse_leftover("\x1b[1;5") == []
