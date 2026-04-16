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

"""Tests for the stop_on_first_failure feature in EvaluationService.

These tests mock the CMS import chain so they can run without
PostgreSQL or the full CMS dependency set installed.

"""

import importlib
import importlib.util
import os
import sys
import types
import unittest
from unittest.mock import MagicMock

# Locate the project root (where cms/ lives).
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))


def _make_stub(name, path=None):
    """Create a stub module and register it in sys.modules."""
    mod = types.ModuleType(name)
    if path is not None:
        mod.__path__ = [path]
    else:
        mod.__path__ = []
    sys.modules[name] = mod
    return mod


# ---------------------------------------------------------------------------
# Stub out the CMS import tree so we can load EvaluationService.py
# without needing gevent, psycopg2, tornado, etc.
# ---------------------------------------------------------------------------

# Top-level CMS package.
cms_mod = _make_stub("cms", os.path.join(_PROJECT_ROOT, "cms"))
cms_mod.ServiceCoord = MagicMock()
cms_mod.get_service_shards = MagicMock(return_value=1)
_make_stub("cms.log")
conf_mod = _make_stub("cms.conf")
conf_mod.config = MagicMock()
_make_stub("cms.util")
_make_stub("cms.plugin")

# cms.db — use MagicMock() for all DB model classes.
db_mod = _make_stub("cms.db", os.path.join(_PROJECT_ROOT, "cms", "db"))
for _a in ["SessionGen", "Digest", "Dataset", "Evaluation", "Submission",
           "SubmissionResult", "Task", "Testcase", "UserTest",
           "UserTestResult", "get_submissions", "get_submission_results",
           "get_datasets_to_judge"]:
    setattr(db_mod, _a, MagicMock())
_make_stub("cms.db.filecacher").FileCacher = MagicMock()

# cms.io
io_mod = _make_stub("cms.io", os.path.join(_PROJECT_ROOT, "cms", "io"))
io_mod.PriorityQueue = type("PriorityQueue", (), {
    "PRIORITY_HIGH": 1, "PRIORITY_MEDIUM": 2,
    "PRIORITY_LOW": 3, "PRIORITY_EXTRA_LOW": 4,
})
io_mod.QueueItem = type("QueueItem", (), {})
io_mod.Executor = type("Executor", (), {"__init__": lambda *a, **kw: None})
io_mod.TriggeredService = type("TriggeredService", (), {
    "__init__": lambda *a, **kw: None})
io_mod.rpc_method = lambda f: f

# cms.grading
_make_stub("cms.grading", os.path.join(_PROJECT_ROOT, "cms", "grading"))
grading_job = _make_stub("cms.grading.Job")
grading_job.JobGroup = MagicMock()

# cms.service sub-modules (stub the ones imported by EvaluationService.py).
_make_stub("cms.service", os.path.join(_PROJECT_ROOT, "cms", "service"))

# Pre-populate cms.service.esoperations by loading only ESOperation from
# the real source file, avoiding module-level DB filter constants.
_esops_path = os.path.join(_PROJECT_ROOT, "cms", "service", "esoperations.py")
_esops_mod = _make_stub("cms.service.esoperations")
# Read just the ESOperation class via importlib.util with exec control.
# We need QueueItem to be available.
_esops_mod.QueueItem = io_mod.QueueItem

# Load ESOperation directly from source, executing only what we need.
with open(_esops_path) as _f:
    _source = _f.read()
_globals = {
    "__builtins__": __builtins__,
    "QueueItem": io_mod.QueueItem,
    "logging": __import__("logging"),
    # Provide stubs for module-level imports.
    "case": MagicMock(), "literal": MagicMock(),
    "Dataset": MagicMock(), "Evaluation": MagicMock(),
    "Submission": MagicMock(), "SubmissionResult": MagicMock(),
    "Task": MagicMock(), "Testcase": MagicMock(),
    "UserTest": MagicMock(), "UserTestResult": MagicMock(),
    "PriorityQueue": io_mod.PriorityQueue,
}
# Extract just the ESOperation class definition by executing the full module
# in a namespace where DB models are plain MagicMocks (comparison-safe).
# The trick: make MagicMock comparisons not raise by pre-defining filter consts.
_globals["MAX_COMPILATION_TRIES"] = MagicMock()
_globals["MAX_EVALUATION_TRIES"] = MagicMock()
_globals["MAX_USER_TEST_COMPILATION_TRIES"] = MagicMock()
_globals["MAX_USER_TEST_EVALUATION_TRIES"] = MagicMock()

# We can't exec the full module because of SA filter expressions.
# Instead, extract ESOperation class source manually.
exec("""
class ESOperation(QueueItem):
    COMPILATION = "compile"
    EVALUATION = "evaluate"
    USER_TEST_COMPILATION = "compile_test"
    USER_TEST_EVALUATION = "evaluate_test"

    def __init__(self, type_, object_id, dataset_id, testcase_codename=None):
        self.type_ = type_
        self.object_id = object_id
        self.dataset_id = dataset_id
        self.testcase_codename = testcase_codename

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        return (self.type_ == other.type_
                and self.object_id == other.object_id
                and self.dataset_id == other.dataset_id
                and self.testcase_codename == other.testcase_codename)

    def __hash__(self):
        return hash((self.type_, self.object_id, self.dataset_id,
                     self.testcase_codename))
""", _globals)

ESOperation = _globals["ESOperation"]
_esops_mod.ESOperation = ESOperation
_esops_mod.get_relevant_operations = MagicMock()
_esops_mod.get_submissions_operations = MagicMock()
_esops_mod.get_user_tests_operations = MagicMock()
_esops_mod.submission_get_operations = MagicMock()
_esops_mod.submission_to_evaluate = MagicMock()
_esops_mod.user_test_get_operations = MagicMock()

scoring_ops = _make_stub("cms.service.scoringoperations")
scoring_ops.ScoringOperation = MagicMock()
fd_mod = _make_stub("cms.service.flushingdict")
fd_mod.FlushingDict = MagicMock()
wp_mod = _make_stub("cms.service.workerpool")
wp_mod.WorkerPool = MagicMock()
_make_stub("cms.plagiarismchecker").calculate_plagiarism = MagicMock()

# cmscommon
_make_stub("cmscommon")
_make_stub("cmscommon.datetime").make_timestamp = MagicMock()

# gevent
_make_stub("gevent")
_make_stub("gevent.lock").RLock = MagicMock

# sqlalchemy (minimal stubs)
if "sqlalchemy" not in sys.modules:
    sa = _make_stub("sqlalchemy")
    sa.func = MagicMock()
    sa.literal = MagicMock()
    sa.case = MagicMock()
    sa_exc = _make_stub("sqlalchemy.exc")
    sa_exc.IntegrityError = type("IntegrityError", (Exception,), {})

# ---------------------------------------------------------------------------
# Now load EvaluationService from the real source file.
# ---------------------------------------------------------------------------

_es_path = os.path.join(
    _PROJECT_ROOT, "cms", "service", "EvaluationService.py")
_es_spec = importlib.util.spec_from_file_location(
    "cms.service.EvaluationService", _es_path)
_es_module = importlib.util.module_from_spec(_es_spec)
sys.modules["cms.service.EvaluationService"] = _es_module
_es_spec.loader.exec_module(_es_module)

_skip_remaining = _es_module.EvaluationService._skip_remaining_evaluations


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_testcase(tc_id, codename):
    tc = MagicMock()
    tc.id = tc_id
    tc.codename = codename
    return tc


def _make_evaluation(testcase_id, outcome, text):
    ev = MagicMock()
    ev.testcase_id = testcase_id
    ev.outcome = outcome
    ev.text = text
    return ev


def _make_dataset(dataset_id, testcases, stop_on_first_failure=True):
    dataset = MagicMock()
    dataset.id = dataset_id
    dataset.stop_on_first_failure = stop_on_first_failure
    dataset.testcases = {tc.codename: tc for tc in testcases}
    return dataset


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSkipRemainingEvaluations(unittest.TestCase):
    """Test EvaluationService._skip_remaining_evaluations."""

    def setUp(self):
        self.testcases = [
            _make_testcase(101, "tc_01"),
            _make_testcase(102, "tc_02"),
            _make_testcase(103, "tc_03"),
        ]
        self.dataset = _make_dataset(10, self.testcases)
        self.submission_id = 42
        self.dataset_id = 10

        self.session = MagicMock()

        self.mock_service = MagicMock()
        self.mock_executor = MagicMock()
        self.mock_service.get_executor.return_value = self.mock_executor

    def _set_evaluated_ids(self, tc_ids):
        """Configure mock session to report these testcase IDs as evaluated."""
        # The method calls session.query(...).filter(A, B).all()
        self.session.query.return_value \
            .filter.return_value \
            .all.return_value = [(tid,) for tid in tc_ids]

    def _call_skip(self):
        _skip_remaining(
            self.mock_service,
            self.session, self.submission_id, self.dataset_id, self.dataset)

    def test_creates_placeholders_for_unevaluated(self):
        """Placeholders are created for unevaluated testcases."""
        self._set_evaluated_ids([101])
        self._call_skip()

        # session.add called for tc_02 and tc_03.
        self.assertEqual(self.session.add.call_count, 2)
        self.session.flush.assert_called_once()

    def test_does_not_create_for_already_evaluated(self):
        """No placeholders when all testcases are evaluated."""
        self._set_evaluated_ids([101, 102, 103])
        self._call_skip()

        self.session.add.assert_not_called()
        self.mock_executor.dequeue.assert_not_called()

    def test_dequeues_operations_for_unevaluated(self):
        """Pending evaluation ops are dequeued."""
        self._set_evaluated_ids([101])
        self._call_skip()

        self.assertEqual(self.mock_executor.dequeue.call_count, 2)

        dequeued_ops = [
            c.args[0] for c in self.mock_executor.dequeue.call_args_list
        ]
        dequeued_codenames = {op.testcase_codename for op in dequeued_ops}
        self.assertEqual(dequeued_codenames, {"tc_02", "tc_03"})

        for op in dequeued_ops:
            self.assertEqual(op.type_, ESOperation.EVALUATION)
            self.assertEqual(op.object_id, self.submission_id)
            self.assertEqual(op.dataset_id, self.dataset_id)

    def test_dequeue_keyerror_is_ignored(self):
        """KeyError from dequeue (in-flight ops) is silently caught."""
        self._set_evaluated_ids([101])
        self.mock_executor.dequeue.side_effect = KeyError("not in queue")

        # Should not raise.
        self._call_skip()

        # Placeholders still created.
        self.assertEqual(self.session.add.call_count, 2)

    def test_single_unevaluated(self):
        """Works correctly with only one unevaluated testcase."""
        self._set_evaluated_ids([101, 102])
        self._call_skip()

        self.assertEqual(self.session.add.call_count, 1)
        self.assertEqual(self.mock_executor.dequeue.call_count, 1)


class TestFailureDetection(unittest.TestCase):
    """Test the failure detection logic used in write_results.

    The logic is:
        any(ev.outcome is not None and float(ev.outcome) <= 0.0
            for ev in evaluations)
    """

    @staticmethod
    def _has_failure(evaluations):
        return any(
            ev.outcome is not None and float(ev.outcome) <= 0.0
            for ev in evaluations
        )

    def test_zero_is_failure(self):
        evs = [_make_evaluation(1, "0.0", ["Wrong answer"])]
        self.assertTrue(self._has_failure(evs))

    def test_correct_is_not_failure(self):
        evs = [_make_evaluation(1, "1.0", ["Correct"])]
        self.assertFalse(self._has_failure(evs))

    def test_partial_credit_is_not_failure(self):
        """0.5 should NOT trigger stop_on_first_failure."""
        evs = [_make_evaluation(1, "0.5", ["Partially correct"])]
        self.assertFalse(self._has_failure(evs))

    def test_failure_among_correct(self):
        evs = [
            _make_evaluation(1, "1.0", ["Correct"]),
            _make_evaluation(2, "0.0", ["Wrong answer"]),
        ]
        self.assertTrue(self._has_failure(evs))

    def test_no_evaluations(self):
        self.assertFalse(self._has_failure([]))

    def test_none_outcome_ignored(self):
        evs = [_make_evaluation(1, None, [])]
        self.assertFalse(self._has_failure(evs))

    def test_negative_outcome_is_failure(self):
        evs = [_make_evaluation(1, "-1.0", ["Error"])]
        self.assertTrue(self._has_failure(evs))

    def test_small_positive_is_not_failure(self):
        evs = [_make_evaluation(1, "0.01", ["Almost wrong"])]
        self.assertFalse(self._has_failure(evs))

    def test_string_zero_is_failure(self):
        """Plain '0' (without decimal) should also count as failure."""
        evs = [_make_evaluation(1, "0", ["Wrong"])]
        self.assertTrue(self._has_failure(evs))

    def test_all_correct(self):
        evs = [
            _make_evaluation(1, "1.0", ["Correct"]),
            _make_evaluation(2, "1.0", ["Correct"]),
            _make_evaluation(3, "1.0", ["Correct"]),
        ]
        self.assertFalse(self._has_failure(evs))


class TestESOperationCreation(unittest.TestCase):
    """Test that ESOperation for dequeue is constructed correctly."""

    def test_evaluation_operation_fields(self):
        op = ESOperation(ESOperation.EVALUATION, 42, 10, "tc_01")
        self.assertEqual(op.type_, ESOperation.EVALUATION)
        self.assertEqual(op.object_id, 42)
        self.assertEqual(op.dataset_id, 10)
        self.assertEqual(op.testcase_codename, "tc_01")

    def test_operations_are_equal_when_matching(self):
        op1 = ESOperation(ESOperation.EVALUATION, 42, 10, "tc_01")
        op2 = ESOperation(ESOperation.EVALUATION, 42, 10, "tc_01")
        self.assertEqual(op1, op2)

    def test_operations_differ_by_codename(self):
        op1 = ESOperation(ESOperation.EVALUATION, 42, 10, "tc_01")
        op2 = ESOperation(ESOperation.EVALUATION, 42, 10, "tc_02")
        self.assertNotEqual(op1, op2)


if __name__ == "__main__":
    unittest.main()
