from enum import Enum


class Keys(Enum):
    """Set of special keys codes."""

    NULL = ""
    CANCEL = "Cancel"  # ^break
    HELP = "Help"
    BACKSPACE = "Backspace"
    BACK_SPACE = BACKSPACE
    TAB = "Tab"
    CLEAR = "Clear"
    RETURN = "Enter"
    ENTER = RETURN
    SHIFT = "Shift"
    LEFT_SHIFT = SHIFT
    CONTROL = "Control"
    CTRL = CONTROL
    LEFT_CONTROL = CTRL
    ALT = "Alt"
    LEFT_ALT = ALT
    PAUSE = "Pause"
    ESCAPE = "Escape"
    ESC = ESCAPE
    SPACE = " "
    PAGE_UP = "PageUp"
    PAGE_DOWN = "PageDown"
    END = "End"
    HOME = "Home"
    LEFT = "ArrowLeft"
    ARROW_LEFT = LEFT
    UP = "ArrowUp"
    ARROW_UP = UP
    RIGHT = "ArrowRight"
    ARROW_RIGHT = RIGHT
    DOWN = "ArrowDown"
    ARROW_DOWN = DOWN
    INSERT = "Insert"
    DELETE = "Delete"
    SEMICOLON = ";"
    EQUALS = "="
    NUMPAD0 = "0"
    NUMPAD1 = "1"
    NUMPAD2 = "2"
    NUMPAD3 = "3"
    NUMPAD4 = "4"
    NUMPAD5 = "5"
    NUMPAD6 = "6"
    NUMPAD7 = "7"
    NUMPAD8 = "8"
    NUMPAD9 = "9"
    MULTIPLY = "Multiply"
    ADD = "Add"
    SEPARATOR = "Separator"
    SUBTRACT = "Subtract"
    DECIMAL = "Decimal"
    DIVIDE = "Divide"
    F1 = "F1"
    F2 = "F2"
    F3 = "F3"
    F4 = "F4"
    F5 = "F5"
    F6 = "F6"
    F7 = "F7"
    F8 = "F8"
    F9 = "F9"
    F10 = "F10"
    F11 = "F11"
    F12 = "F12"
    META = "Meta"
    COMMAND = META
    ZENKAKU_HANKAKU = "ZenkakuHanaku"
