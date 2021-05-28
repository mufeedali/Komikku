# Copyright (C) 2019-2021 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _


class ServerException(Exception):
    def __init__(self, message):
            self.message = _('Error: {}').format(message)
            super().__init__(self.message)


class NotFoundError(ServerException):
    def __init__(self):
            super().__init__(_('No longer exists.'))
