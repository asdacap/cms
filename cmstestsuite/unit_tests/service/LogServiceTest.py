#!/usr/bin/env python3

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2013 Stefano Maggiolo <s.maggiolo@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Tests for the logger service.

"""

import logging
import os
import tempfile
import unittest
from unittest.mock import patch

from cms import Address
from cms.service.LogService import LogService


class TestLogService(unittest.TestCase):

    MSG = "Random message"
    SERVICE_NAME = "RandomService"
    SERVICE_SHARD = 0
    OPERATION = "Random operation"
    CREATED = 1_234_567_890.123
    EXC_TEXT = "Random exception"

    def setUp(self):
        self._tmp_log_dir = tempfile.mkdtemp()

        def simple_mkdir(path):
            os.makedirs(path, exist_ok=True)
            return True

        patcher_addr = patch("cms.io.service.get_service_address")
        self.get_service_address = patcher_addr.start()
        self.get_service_address.return_value = Address('127.0.0.1', '12345')
        self.addCleanup(patcher_addr.stop)

        patcher_mkdir = patch("cms.service.LogService.mkdir", side_effect=simple_mkdir)
        patcher_mkdir.start()
        self.addCleanup(patcher_mkdir.stop)

        patcher_config = patch("cms.service.LogService.config")
        mock_config = patcher_config.start()
        mock_config.log_dir = self._tmp_log_dir
        self.addCleanup(patcher_config.stop)

        patcher_io_mkdir = patch("cms.io.service.mkdir", side_effect=simple_mkdir)
        patcher_io_mkdir.start()
        self.addCleanup(patcher_io_mkdir.stop)

        patcher_io_config = patch("cms.io.service.config")
        mock_io_config = patcher_io_config.start()
        mock_io_config.log_dir = self._tmp_log_dir
        mock_io_config.file_log_debug = False
        mock_io_config.backdoor = False
        self.addCleanup(patcher_io_config.stop)

        import shutil
        self.addCleanup(lambda: shutil.rmtree(self._tmp_log_dir, ignore_errors=True))

        self.service = LogService(0)

    def test_last_messages(self):
        for severity in ["CRITICAL",
                         "ERROR",
                         "WARNING"]:
            self.helper_test_last_messages(severity)
        for severity in ["INFO",
                         "DEBUG"]:
            self.helper_test_last_messages(severity, saved=False)

    def helper_test_last_messages(self, severity, saved=True):
        self.service.Log(
            msg=TestLogService.MSG + severity,
            levelname=severity,
            levelno=getattr(logging, severity),
            created=TestLogService.CREATED,
            service_name=TestLogService.SERVICE_NAME + severity,
            service_shard=TestLogService.SERVICE_SHARD,
            operation=TestLogService.OPERATION + severity,
            exc_text=TestLogService.EXC_TEXT + severity)
        last_message = self.service.last_messages()[-1]
        if saved:
            self.assertEqual(last_message["message"],
                              TestLogService.MSG + severity)
            self.assertEqual(last_message["coord"],
                              TestLogService.SERVICE_NAME + severity +
                              "," + ("%d" % TestLogService.SERVICE_SHARD))
            self.assertEqual(last_message["operation"],
                              TestLogService.OPERATION + severity)
            self.assertEqual(last_message["severity"],
                              severity)
            self.assertEqual(last_message["timestamp"],
                              TestLogService.CREATED)
            self.assertEqual(last_message["exc_text"],
                              TestLogService.EXC_TEXT + severity)
        else:
            self.assertNotEqual(last_message["severity"], severity)


if __name__ == "__main__":
    unittest.main()
