# -*- coding: utf-8 -*-
"""Setup logging."""

from __future__ import absolute_import, unicode_literals

import logging
import logging.config
import logging.handlers

logger = logging.getLogger(__name__)

try:
    from colorlog import ColoredFormatter
    from gettext import gettext as _  # noqa
    """Return a logger with a default ColoredFormatter."""
    formatter = ColoredFormatter(
        "(%(threadName)-9s) %(log_color)s%(levelname)-8s%(reset)s (%(funcName)-5s) %(message_log_color)s%(message)s",  # noqa
        datefmt=None,
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
            'TRACE': 'purple'
        },
        secondary_log_colors={
            'message': {
                'ERROR': 'red',
                'CRITICAL': 'red',
                'DEBUG': 'yellow',
                'INFO': 'yellow,bg_blue'
            }
        },
        style='%'
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
except ImportError:
    # No color available, use default config
    logging.basicConfig(format='%(levelname)s: %(message)s')
    logger.warn("Disabling color, you really want to install colorlog.")
