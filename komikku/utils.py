# Copyright (C) 2019-2020 Valéry Febvre
# SPDX-License-Identifier: GPL-3.0-only or GPL-3.0-or-later
# Author: Valéry Febvre <vfebvre@easter-eggs.com>

from gettext import gettext as _
import logging
import requests
import subprocess
import traceback

logger = logging.getLogger()


def folder_size(path):
    res = subprocess.run(['du', '-sh', path], stdout=subprocess.PIPE, check=False)

    return res.stdout.split()[0].decode()


def log_error_traceback(e):
    if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
        return _('No Internet connection or server down')

    logger.info(traceback.format_exc())

    return None
