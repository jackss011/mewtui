"""Show "hello" in the middle of the screen. Quit with q or Ctrl-C."""

import mewtui

with mewtui.screen() as ctx:
    ctx.cursor_visibility(False)
    width, height = ctx.size()

    message = "hello"
    ctx.cursor_set((width - len(message)) // 2, height // 2)
    ctx.put(message)

    hint = "press q or Ctrl-C to quit"
    ctx.cursor_set((width - len(hint)) // 2, height // 2 + 2)
    ctx.put(hint)
    ctx.flush()

    while True:
        match ctx.wait_event():
            case mewtui.Char("q") | mewtui.Char("c", ctrl=True):
                break
