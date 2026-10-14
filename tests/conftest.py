import pytest

from mewtui import Context


@pytest.fixture
def ctx():
    """A 10x5 Context not connected to a terminal, for inspecting its buffer."""
    context = Context()
    context._width, context._height = 10, 5
    return context
