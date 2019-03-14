from gi.repository import GLib, Gio

setting = Gio.Settings.new("com.gitlab.valos.MangaScan")

dark_theme = "dark-theme"
first_start_screen = "first-start-screen"
window_size = "window-size"
sort_order = "sort-order"
development_backup_mode = "development-backup-mode"


def get_dark_theme():
    return setting.get_boolean(dark_theme)


def set_dark_theme(value):
    setting.set_boolean(dark_theme, value)


def get_window_size():
    return setting.get_value(window_size)


def set_window_size(list):
    g_variant = GLib.Variant('ai', list)
    setting.set_value(window_size, g_variant)


def get_sort_order():
    value = setting.get_enum(sort_order)
    if value == 0:
        return "A-Z"
    elif value == 1:
        return "Z-A"
    elif value == 2:
        return "last_added"


def set_sort_order(value):
    if value == "A-Z":
        setting.set_enum(sort_order, 0)
    elif value == "Z-A":
        setting.set_enum(sort_order, 1)
    elif value == "last_added":
        setting.set_enum(sort_order, 2)


def get_development_backup_mode():
    return setting.get_boolean(development_backup_mode)


def set_development_backup_mode(value):
    setting.set_boolean(development_backup_mode, value)
