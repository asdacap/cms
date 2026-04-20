#!/usr/bin/env python3

# Contest Management System - http://cms-dev.github.io/
# Copyright © 2018 Stefano Maggiolo <s.maggiolo@gmail.com>
# Copyright © 2025 Contributors
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

"""Tests for the ACMICPCApproximate score type."""

import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from cms.grading.scoretypes.ACMICPCApproximate import ACMICPCApproximate


class TestACMICPCApproximate(unittest.TestCase):
    """Test the ACMICPCApproximate score type."""

    def setUp(self):
        super().setUp()
        self._public_testcases = {
            "0": True,
            "1": True,
        }

    def test_parameters_defaults(self):
        """Test default parameters."""
        st = ACMICPCApproximate(10000, self._public_testcases)
        base, penalty, time_decay, count_ce_as_wrong = st.params()
        self.assertEqual(base, 10000)
        self.assertEqual(penalty, 20)
        self.assertEqual(time_decay, 1)
        self.assertTrue(count_ce_as_wrong)

    def test_parameters_custom(self):
        """Test custom parameters (3-element list keeps CE-as-wrong default)."""
        st = ACMICPCApproximate([5000, 50, 2], self._public_testcases)
        base, penalty, time_decay, count_ce_as_wrong = st.params()
        self.assertEqual(base, 5000)
        self.assertEqual(penalty, 50)
        self.assertEqual(time_decay, 2)
        self.assertTrue(count_ce_as_wrong)

    def test_parameters_count_ce_as_wrong_disabled(self):
        """Test 4-element parameter list disables counting CE as a wrong attempt."""
        st = ACMICPCApproximate(
            [5000, 50, 2, False], self._public_testcases)
        base, penalty, time_decay, count_ce_as_wrong = st.params()
        self.assertEqual(base, 5000)
        self.assertEqual(penalty, 50)
        self.assertEqual(time_decay, 2)
        self.assertFalse(count_ce_as_wrong)

    def test_max_scores(self):
        """Test max_scores returns correct values."""
        st = ACMICPCApproximate(10000, self._public_testcases)
        max_score, max_public_score, ranking_headers = st.max_scores()
        self.assertEqual(max_score, 10000)
        self.assertEqual(max_public_score, 10000)
        self.assertEqual(ranking_headers, ["Wrong Attempts", "Time Penalty"])

    def test_ranking_details_format_correct(self):
        """Test that ranking_details is a JSON string in a list."""
        st = ACMICPCApproximate(10000, self._public_testcases)

        sr = MagicMock()
        sr.evaluated.return_value = False
        sr.evaluations = []
        
        mock_submission = MagicMock()
        _base_time = datetime(2020, 1, 1, 0, 0, 0)
        mock_submission.timestamp = _base_time + timedelta(seconds=1000)
        mock_submission.task.contest.start = _base_time
        mock_submission.task_id = "task1"
        mock_submission.participation_id = 1
        sr.submission = mock_submission

        with patch('cms.grading.scoretypes.ACMICPCApproximate.SessionGen') as mock_session_gen:
            mock_session = MagicMock()
            mock_session.query.return_value.join.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.count.return_value = 0
            mock_session_gen.return_value.__enter__ = lambda s: mock_session
            mock_session_gen.return_value.__exit__ = lambda s, *args: None

            score, details, public_score, public_details, ranking_details = st.compute_score(sr)

        self.assertEqual(len(ranking_details), 1)
        self.assertIsInstance(ranking_details[0], str)
        
        parsed = json.loads(ranking_details[0])
        self.assertIn("wrong_attempt", parsed)
        self.assertIn("penalty", parsed)
        self.assertIn("second_elapsed", parsed)
        self.assertIn("time_penalty", parsed)
        self.assertEqual(parsed["wrong_attempt"], 1)

    def test_ranking_details_wrong_attempt_count(self):
        """Test that wrong_attempt count is correct with previous submissions."""
        st = ACMICPCApproximate(10000, self._public_testcases)

        sr = MagicMock()
        sr.evaluated.return_value = False
        sr.evaluations = []
        
        mock_submission = MagicMock()
        _base_time = datetime(2020, 1, 1, 0, 0, 0)
        mock_submission.timestamp = _base_time + timedelta(seconds=1000)
        mock_submission.task.contest.start = _base_time
        mock_submission.task_id = "task1"
        mock_submission.participation_id = 1
        sr.submission = mock_submission

        with patch('cms.grading.scoretypes.ACMICPCApproximate.SessionGen') as mock_session_gen:
            mock_session = MagicMock()
            mock_session.query.return_value.join.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.count.return_value = 3
            mock_session_gen.return_value.__enter__ = lambda s: mock_session
            mock_session_gen.return_value.__exit__ = lambda s, *args: None

            score, details, public_score, public_details, ranking_details = st.compute_score(sr)

        parsed = json.loads(ranking_details[0])
        self.assertEqual(parsed["wrong_attempt"], 4)

    def test_ranking_details_correct_submission(self):
        """Test ranking_details for correct submission (no wrong attempts from this submission)."""
        st = ACMICPCApproximate(10000, self._public_testcases)

        sr = MagicMock()
        sr.evaluated.return_value = True
        
        mock_eval = MagicMock()
        mock_eval.codename = "0"
        mock_eval.outcome = 1.0
        mock_eval.text = "OK"
        mock_eval.execution_time = 0.1
        mock_eval.execution_memory = 1024
        mock_eval2 = MagicMock()
        mock_eval2.codename = "1"
        mock_eval2.outcome = 1.0
        mock_eval2.text = "OK"
        mock_eval2.execution_time = 0.1
        mock_eval2.execution_memory = 1024
        sr.evaluations = [mock_eval, mock_eval2]
        
        mock_submission = MagicMock()
        _base_time = datetime(2020, 1, 1, 0, 0, 0)
        mock_submission.timestamp = _base_time + timedelta(seconds=1000)
        mock_submission.task.contest.start = _base_time
        mock_submission.task_id = "task1"
        mock_submission.participation_id = 1
        sr.submission = mock_submission

        with patch('cms.grading.scoretypes.ACMICPCApproximate.SessionGen') as mock_session_gen:
            mock_session = MagicMock()
            mock_session.query.return_value.join.return_value.filter.return_value.filter.return_value.filter.return_value.filter.return_value.count.return_value = 2
            mock_session_gen.return_value.__enter__ = lambda s: mock_session
            mock_session_gen.return_value.__exit__ = lambda s, *args: None

            score, details, public_score, public_details, ranking_details = st.compute_score(sr)

        parsed = json.loads(ranking_details[0])
        self.assertEqual(parsed["wrong_attempt"], 2)
        self.assertEqual(parsed["penalty"], 40)
        self.assertGreater(score, 0)

    def _make_failing_submission(self, compilation_failed):
        """Build a MagicMock submission_result for a failing submission."""
        sr = MagicMock()
        sr.evaluated.return_value = False
        sr.evaluations = []
        sr.compilation_failed.return_value = compilation_failed

        mock_submission = MagicMock()
        _base_time = datetime(2020, 1, 1, 0, 0, 0)
        mock_submission.timestamp = _base_time + timedelta(seconds=1000)
        mock_submission.task.contest.start = _base_time
        mock_submission.task_id = "task1"
        mock_submission.participation_id = 1
        sr.submission = mock_submission
        return sr

    @staticmethod
    def _patch_session_count(prior_count):
        """Patch SessionGen so that any chained .filter().count() returns prior_count."""
        patcher = patch(
            'cms.grading.scoretypes.ACMICPCApproximate.SessionGen')
        mock_session_gen = patcher.start()
        mock_session = MagicMock()
        # Make every chained .filter() return the same MagicMock so the leaf
        # .count() works regardless of how many filters were applied.
        chain = MagicMock()
        chain.filter.return_value = chain
        chain.count.return_value = prior_count
        mock_session.query.return_value.join.return_value = chain
        mock_session_gen.return_value.__enter__ = lambda s: mock_session
        mock_session_gen.return_value.__exit__ = lambda s, *args: None
        return patcher, mock_session

    def test_compilation_failed_default_counts_as_wrong(self):
        """CE with default config increments wrong_attempt and shows CE label."""
        st = ACMICPCApproximate(10000, self._public_testcases)
        sr = self._make_failing_submission(compilation_failed=True)
        patcher, _ = self._patch_session_count(prior_count=0)
        try:
            score, details, _, _, _ = st.compute_score(sr)
        finally:
            patcher.stop()

        self.assertEqual(score, 0)
        self.assertTrue(details["compilation_failed"])
        self.assertEqual(details["wrong_attempt"], 1)
        self.assertEqual(
            ACMICPCApproximate.format_score(score, 10000, details, 0),
            "Compilation failed")

    def test_compilation_failed_disabled_does_not_count(self):
        """CE with count_ce_as_wrong=False does not increment wrong_attempt."""
        st = ACMICPCApproximate(
            [10000, 20, 1, False], self._public_testcases)
        sr = self._make_failing_submission(compilation_failed=True)
        patcher, mock_session = self._patch_session_count(prior_count=0)
        try:
            score, details, _, _, _ = st.compute_score(sr)
        finally:
            patcher.stop()

        self.assertEqual(score, 0)
        self.assertTrue(details["compilation_failed"])
        # CE current submission did not increment, prior was 0 → 0
        self.assertEqual(details["wrong_attempt"], 0)
        # Verify the extra compilation_outcome filter was applied: with the
        # disabled flag the chain receives 5 filter() calls instead of 4.
        chain = mock_session.query.return_value.join.return_value
        self.assertGreaterEqual(chain.filter.call_count, 5)

    def test_wrong_answer_not_compilation_failed(self):
        """A wrong-answer (compiled OK but eval failed) sets compilation_failed=False."""
        st = ACMICPCApproximate(10000, self._public_testcases)

        sr = MagicMock()
        sr.evaluated.return_value = True
        sr.compilation_failed.return_value = False

        # First testcase fails, second passes → has_wrong=True, but not CE.
        ev0 = MagicMock()
        ev0.codename = "0"
        ev0.outcome = 0.0
        ev0.text = ["Wrong answer"]
        ev0.execution_time = 0.1
        ev0.execution_memory = 1024
        ev1 = MagicMock()
        ev1.codename = "1"
        ev1.outcome = 1.0
        ev1.text = ["OK"]
        ev1.execution_time = 0.1
        ev1.execution_memory = 1024
        sr.evaluations = [ev0, ev1]

        mock_submission = MagicMock()
        _base_time = datetime(2020, 1, 1, 0, 0, 0)
        mock_submission.timestamp = _base_time + timedelta(seconds=1000)
        mock_submission.task.contest.start = _base_time
        mock_submission.task_id = "task1"
        mock_submission.participation_id = 1
        sr.submission = mock_submission

        patcher, _ = self._patch_session_count(prior_count=0)
        try:
            score, details, _, _, _ = st.compute_score(sr)
        finally:
            patcher.stop()

        self.assertEqual(score, 0)
        self.assertFalse(details["compilation_failed"])
        # format_score should NOT return "Compilation failed" — it should
        # surface the failing testcase's status text instead.
        formatted = ACMICPCApproximate.format_score(
            score, 10000, details, 0)
        self.assertNotEqual(formatted, "Compilation failed")
        self.assertIn("Wrong answer", formatted)


if __name__ == "__main__":
    unittest.main()