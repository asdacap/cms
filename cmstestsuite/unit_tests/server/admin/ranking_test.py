#!/usr/bin/env python3

# Contest Management System - http://cms-dev.github.io/
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

"""Tests for ranking handler logic (config flags)."""

import unittest
from unittest.mock import patch

from cmstestsuite.unit_tests.databasemixin import DatabaseMixin

from cms import config


class TestRankingConfigFlags(DatabaseMixin, unittest.TestCase):
    """Tests for ranking config flags (hide_teams)."""

    def setUp(self):
        super().setUp()
        self.contest = self.add_contest()

    def _make_participation_with_team(self):
        team = self.add_team()
        return self.add_participation(contest=self.contest, team=team)

    def _compute_show_teams(self):
        """Replicate the ranking handler's show_teams computation."""
        return not config.ranking_hide_teams and any(
            p.team_id for p in self.contest.participations)

    def test_show_teams_with_teams_default(self):
        self._make_participation_with_team()
        self.session.flush()

        with patch.object(config, "ranking_hide_teams", False):
            self.assertTrue(self._compute_show_teams())

    def test_show_teams_without_teams_default(self):
        self.add_participation(contest=self.contest)
        self.session.flush()

        with patch.object(config, "ranking_hide_teams", False):
            self.assertFalse(self._compute_show_teams())

    def test_show_teams_hidden_by_config(self):
        self._make_participation_with_team()
        self.session.flush()

        with patch.object(config, "ranking_hide_teams", True):
            self.assertFalse(self._compute_show_teams())


if __name__ == "__main__":
    unittest.main()
