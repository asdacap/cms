#!/usr/bin/python
# -*- coding: utf-8 -*-

# Programming contest management system
# Copyright © 2010-2011 Giovanni Mascellani <mascellani@poisson.phc.unipi.it>
# Copyright © 2010-2011 Stefano Maggiolo <s.maggiolo@gmail.com>
# Copyright © 2010-2011 Matteo Boscariol <boscarim@hotmail.com>
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

"""This file defines a class built on top of Service in order to
provide facilities to build a service that does test a production
service.

"""

import time

from AsyncLibrary import Service, logger
from cms.async import ServiceCoord


class TestService(Service):
    """Runs automatically a suite of tests defined on the subclass.

    """
    def __init__(self, shard):
        Service.__init__(self, shard)

        self.start = 0
        self.total_time = 0
        self.ok = 0
        self.current = -1
        self.ongoing = False
        self.failed = False
        self.warned = False
        self.add_timeout(self.test, None, 0.2, immediately=True)

    def test(self):
        """Runs the test suite.

        """
        if self.ongoing:
            return True
        elif self.current >= 0 and not self.failed:
            self.total_time += self.delta
            logger.info("Test #%03d performed in %.2lf seconds." %
                        (self.current, self.delta))

        self.current += 1
        if self.ok != self.current:
            self.failed = True

        try:
            method = getattr(self, "test_%03d" % self.current)
        except AttributeError as e:
            total = self.current
            if total == 0:
                logger.info("Test suite completed.")
                return False
            else:
                logger.info(("Test suite completed in %.2f seconds. " +
                             "Result: %d/%d (%.2f%%).") %
                            (self.total_time, self.ok, total,
                             self.ok * 100.0 / total))
                self.exit()
                return False

        if not self.failed:
            self.ongoing = True
            logger.info("Performing Test #%03d..." % self.current)
            self.start = time.time()
            method()
        else:
            logger.info("Not performing Test #%03d." % self.current)
        return True

    def test_end(self, success, message=None):
        """This method is to be called when finishing a test.

        success (bool): True if the test was successful

        """
        if message != None:
            if success:
                logger.info("  " + message)
            else:
                logger.error("  " + message)
        self.ongoing = False
        if success:
            self.ok += 1
        self.delta = time.time() - self.start

