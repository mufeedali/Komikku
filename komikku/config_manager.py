from gi.repository import GLib, Gio

setting = Gio.Settings.new('info.febvre.Komikku')

dark_theme = 'dark-theme'
update_at_startup = 'update-at-startup'

background_color = 'background-color'
fullscreen = 'fullscreen'
reading_direction = 'reading-direction'
scaling = 'scaling'
window_size = 'window-size'


def get_background_color(nick=True):
    value = setting.get_enum(background_color)
    if not nick:
        return value

    if value == 0:
        return 'white'
    if value == 1:
        return 'black'


def set_background_color(value):
    if value == 'white':
        setting.set_enum(background_color, 0)
    elif value == 'black':
        setting.set_enum(background_color, 1)


def get_dark_theme():
    return setting.get_boolean(dark_theme)


def set_dark_theme(value):
    setting.set_boolean(dark_theme, value)


def get_fullscreen():
    return setting.get_boolean(fullscreen)


def set_fullscreen(value):
    setting.set_boolean(fullscreen, value)


def get_reading_direction(nick=True):
    value = setting.get_enum(reading_direction)
    if not nick:
        return value

    if value == 0:
        return 'right-to-left'
    if value == 1:
        return 'left-to-right'


def set_reading_direction(value):
    if value == 'right-to-left':
        setting.set_enum(reading_direction, 0)
    elif value == 'left-to-right':
        setting.set_enum(reading_direction, 1)


def get_scaling(nick=True):
    value = setting.get_enum(scaling)
    if not nick:
        return value

    if value == 0:
        return 'screen'
    if value == 1:
        return 'width'
    if value == 2:
        return 'height'


def set_scaling(value):
    if value == 'screen':
        setting.set_enum(scaling, 0)
    elif value == 'width':
        setting.set_enum(scaling, 1)
    elif value == 'height':
        setting.set_enum(scaling, 2)


def get_window_size():
    return setting.get_value(window_size)


def set_window_size(size):
    g_variant = GLib.Variant('ai', size)
    setting.set_value(window_size, g_variant)


def get_update_at_startup():
    return setting.get_boolean(update_at_startup)


def set_update_at_startup(value):
    setting.set_boolean(update_at_startup, value)
