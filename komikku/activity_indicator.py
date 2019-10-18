# -*- coding: utf-8 -*-

# Copyright (C) 2019 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gi.repository import Gtk


class ActivityIndicator(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(50, 50)

        self.pack_start(self.spinner, True, False, 0)

    def stop(self):
        self.spinner.stop()

    def start(self):
        self.spinner.start()
