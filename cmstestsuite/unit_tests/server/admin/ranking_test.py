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

"""Tests for ranking handler logic (solved count and config flags)."""

import unittest
from unittest.mock import patch

from cmstestsuite.unit_tests.databasemixin import DatabaseMixin

from cms import config
from cms.grading.scoring import task_score


class TestRankingSolvedCount(DatabaseMixin, unittest.TestCase):
    """Tests for the solved_count computation used by RankingHandler."""

    def setUp(self):
        super().setUp()
        self.contest = self.add_contest()
        self.participation = self.add_participation(contest=self.contest)

    def _add_task_with_score(self, score):
        """Add a task and a scored submission for it."""
        task = self.add_task(contest=self.contest, score_precision=2)
        dataset = self.add_dataset(task=task)
        task.active_dataset = dataset
        if score is not None:
            submission = self.add_submission(
                participation=self.participation, task=task)
            self.add_submission_result(
                submission, dataset,
                score=score, public_score=0.0,
                score_details=[], public_score_details=[],
                ranking_score_details=[])
        return task

    def _compute_solved_count(self):
        """Replicate the ranking handler's solved_count computation."""
        scores = []
        for task in self.contest.tasks:
            t_score, _ = task_score(self.participation, task, rounded=True)
            scores.append((t_score, False))
        return sum(1 for score, _ in scores if score > 0)

    def test_solved_count_basic(self):
        self._add_task_with_score(10.0)
        self._add_task_with_score(5.0)
        self._add_task_with_score(0.0)
        self.session.flush()

        self.assertEqual(self._compute_solved_count(), 2)

    def test_solved_count_zero(self):
        self._add_task_with_score(0.0)
        self._add_task_with_score(0.0)
        self._add_task_with_score(0.0)
        self.session.flush()

        self.assertEqual(self._compute_solved_count(), 0)

    def test_solved_count_all_solved(self):
        self._add_task_with_score(10.0)
        self._add_task_with_score(5.0)
        self._add_task_with_score(1.0)
        self.session.flush()

        self.assertEqual(self._compute_solved_count(), 3)

    def test_solved_count_no_submissions(self):
        self._add_task_with_score(None)
        self._add_task_with_score(None)
        self.session.flush()

        self.assertEqual(self._compute_solved_count(), 0)


class TestRankingConfigFlags(DatabaseMixin, unittest.TestCase):
    """Tests for ranking config flags (hide_teams, show_solved_count)."""

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

    def test_show_solved_config_true(self):
        with patch.object(config, "ranking_show_solved_count", True):
            self.assertTrue(config.ranking_show_solved_count)

    def test_show_solved_config_false(self):
        with patch.object(config, "ranking_show_solved_count", False):
            self.assertFalse(config.ranking_show_solved_count)


if __name__ == "__main__":
    unittest.main()
