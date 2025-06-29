import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from sweflow_bench.utils.run_evaluation import (
    EvaluationError,
    EvaluationResult,
    evaluate_instance,
    run_evaluation,
    GIT_APPLY_COMMANDS,
)
from sweflow_bench.utils.data import SWEFlowTestInstance


class TestEvaluationError:

    def test_evaluation_error_creation(self):
        error = EvaluationError("test-001", 1, "Error message")
        assert error.instance_id == "test-001"
        assert error.exit_code == 1
        assert error.output == "Error message"


class TestEvaluationResult:

    def test_evaluation_result_creation(self):
        result = EvaluationResult(instance_id="test-001", resolved=True, exit_code=0, test_log="Test passed")
        assert result.instance_id == "test-001"
        assert result.resolved is True
        assert result.exit_code == 0
        assert result.test_log == "Test passed"

    def test_evaluation_result_model_dump(self):
        result = EvaluationResult(instance_id="test-001", resolved=True, exit_code=0, test_log="Test passed")
        dumped = result.model_dump()
        assert dumped["instance_id"] == "test-001"
        assert dumped["resolved"] is True
        assert dumped["exit_code"] == 0
        assert dumped["test_log"] == "Test passed"


class TestEvaluateInstance:

    @patch('sweflow_bench.utils.run_evaluation.start_docker_container')
    @patch('sweflow_bench.utils.run_evaluation.exec_command_in_container')
    @patch('sweflow_bench.utils.run_evaluation.copy_file_to_container')
    @patch('sweflow_bench.utils.run_evaluation.stop_docker_container')
    @patch('sweflow_bench.utils.run_evaluation.remove_docker_container')
    @patch('tempfile.mktemp')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.unlink')
    def test_evaluate_instance_success(self, mock_unlink, mock_open, mock_mktemp, mock_remove, mock_stop, mock_copy, mock_exec, mock_start):
        # Setup mocks
        mock_container = MagicMock()
        mock_container.id = "test-container-id"
        mock_start.return_value = mock_container

        # Mock successful command executions
        mock_exec.side_effect = [
            (0, "Copy successful"),  # cp -r /testbed/. /workspace
            (0, "Checkout successful"),  # git checkout
            (0, "Apply successful"),  # git apply
            (0, "Test passed")  # eval script
        ]

        mock_mktemp.return_value = "/tmp/test-patch.diff"

        # Create test instance
        instance = SWEFlowTestInstance(instance_id="test-001",
                                       repo="test-repo",
                                       problem_statement="Fix the bug",
                                       base_commit="abc123",
                                       reference_commit="def456",
                                       patch="diff --git a/test.py b/test.py\nindex 123..456 100644\n--- a/test.py\n+++ b/test.py\n@@ -1,2 +1,2 @@\n-print('hello')\n+print('world')\n",
                                       docker_image="test-image:latest",
                                       FAIL_TO_PASS=["test_fail_to_pass"],
                                       PASS_TO_PASS=["test_pass_to_pass"],
                                       model="test-model")

        result = evaluate_instance(instance)

        # Verify result
        assert result.instance_id == "test-001"
        assert result.resolved is True
        assert result.exit_code == 0
        assert result.test_log == "Test passed"

        # Verify calls
        mock_start.assert_called_once()
        assert mock_exec.call_count == 4
        mock_copy.assert_called_once()
        mock_stop.assert_called_once_with(mock_container)
        mock_remove.assert_called_once_with(mock_container)
        mock_unlink.assert_called_once()

    @patch('sweflow_bench.utils.run_evaluation.start_docker_container')
    @patch('sweflow_bench.utils.run_evaluation.exec_command_in_container')
    @patch('sweflow_bench.utils.run_evaluation.stop_docker_container')
    @patch('sweflow_bench.utils.run_evaluation.remove_docker_container')
    def test_evaluate_instance_copy_failure(self, mock_remove, mock_stop, mock_exec, mock_start):
        # Setup mocks
        mock_container = MagicMock()
        mock_container.id = "test-container-id"
        mock_start.return_value = mock_container

        # Mock failed copy command
        mock_exec.return_value = (1, "Copy failed")

        # Create test instance
        instance = SWEFlowTestInstance(instance_id="test-001",
                                       repo="test-repo",
                                       problem_statement="Fix the bug",
                                       base_commit="abc123",
                                       reference_commit="def456",
                                       patch="diff --git a/test.py b/test.py\nindex 123..456 100644\n--- a/test.py\n+++ b/test.py\n@@ -1,2 +1,2 @@\n-print('hello')\n+print('world')\n",
                                       docker_image="test-image:latest",
                                       FAIL_TO_PASS=["test_fail_to_pass"],
                                       PASS_TO_PASS=["test_pass_to_pass"],
                                       model="test-model")

        with pytest.raises(EvaluationError) as exc_info:
            evaluate_instance(instance)

        assert exc_info.value.instance_id == "test-001"
        assert exc_info.value.exit_code == 1
        assert exc_info.value.output == "Copy failed"

        # Verify cleanup
        mock_stop.assert_called_once_with(mock_container)
        mock_remove.assert_called_once_with(mock_container)

    @patch('sweflow_bench.utils.run_evaluation.start_docker_container')
    @patch('sweflow_bench.utils.run_evaluation.exec_command_in_container')
    @patch('sweflow_bench.utils.run_evaluation.copy_file_to_container')
    @patch('sweflow_bench.utils.run_evaluation.stop_docker_container')
    @patch('sweflow_bench.utils.run_evaluation.remove_docker_container')
    @patch('tempfile.mktemp')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.unlink')
    def test_evaluate_instance_git_apply_fallback(self, mock_unlink, mock_open, mock_mktemp, mock_remove, mock_stop, mock_copy, mock_exec, mock_start):
        # Setup mocks
        mock_container = MagicMock()
        mock_container.id = "test-container-id"
        mock_start.return_value = mock_container

        # Mock command executions with first git apply failing
        mock_exec.side_effect = [
            (0, "Copy successful"),  # cp -r /testbed/. /workspace
            (0, "Checkout successful"),  # git checkout
            (1, "First apply failed"),  # first git apply
            (0, "Second apply successful"),  # second git apply with -p0
            (0, "Test passed")  # eval script
        ]

        mock_mktemp.return_value = "/tmp/test-patch.diff"

        # Create test instance
        instance = SWEFlowTestInstance(instance_id="test-001",
                                       repo="test-repo",
                                       problem_statement="Fix the bug",
                                       base_commit="abc123",
                                       reference_commit="def456",
                                       patch="diff --git a/test.py b/test.py\nindex 123..456 100644\n--- a/test.py\n+++ b/test.py\n@@ -1,2 +1,2 @@\n-print('hello')\n+print('world')\n",
                                       docker_image="test-image:latest",
                                       FAIL_TO_PASS=["test_fail_to_pass"],
                                       PASS_TO_PASS=["test_pass_to_pass"],
                                       model="test-model")

        result = evaluate_instance(instance)

        # Verify result
        assert result.instance_id == "test-001"
        assert result.resolved is True
        assert result.exit_code == 0
        assert result.test_log == "Test passed"

        # Verify git apply commands were called in order
        git_apply_calls = [call for call in mock_exec.call_args_list if any(cmd in str(call) for cmd in GIT_APPLY_COMMANDS)]
        assert len(git_apply_calls) == 2

    @patch('sweflow_bench.utils.run_evaluation.start_docker_container')
    @patch('sweflow_bench.utils.run_evaluation.exec_command_in_container')
    @patch('sweflow_bench.utils.run_evaluation.copy_file_to_container')
    @patch('sweflow_bench.utils.run_evaluation.stop_docker_container')
    @patch('sweflow_bench.utils.run_evaluation.remove_docker_container')
    @patch('tempfile.mktemp')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.unlink')
    def test_evaluate_instance_test_failure(self, mock_unlink, mock_open, mock_mktemp, mock_remove, mock_stop, mock_copy, mock_exec, mock_start):
        # Setup mocks
        mock_container = MagicMock()
        mock_container.id = "test-container-id"
        mock_start.return_value = mock_container

        # Mock successful setup but failed test
        mock_exec.side_effect = [
            (0, "Copy successful"),  # cp -r /testbed/. /workspace
            (0, "Checkout successful"),  # git checkout
            (0, "Apply successful"),  # git apply
            (1, "Test failed")  # eval script
        ]

        mock_mktemp.return_value = "/tmp/test-patch.diff"

        # Create test instance
        instance = SWEFlowTestInstance(instance_id="test-001",
                                       repo="test-repo",
                                       problem_statement="Fix the bug",
                                       base_commit="abc123",
                                       reference_commit="def456",
                                       patch="diff --git a/test.py b/test.py\nindex 123..456 100644\n--- a/test.py\n+++ b/test.py\n@@ -1,2 +1,2 @@\n-print('hello')\n+print('world')\n",
                                       docker_image="test-image:latest",
                                       FAIL_TO_PASS=["test_fail_to_pass"],
                                       PASS_TO_PASS=["test_pass_to_pass"],
                                       model="test-model")

        result = evaluate_instance(instance)

        # Verify result shows failure
        assert result.instance_id == "test-001"
        assert result.resolved is False
        assert result.exit_code == 1
        assert result.test_log == "Test failed"


class TestRunEvaluation:

    @patch('sweflow_bench.utils.run_evaluation.evaluate_instance')
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.write_text')
    def test_run_evaluation_success(self, mock_write_text, mock_mkdir, mock_evaluate):
        # Setup mock evaluation result
        mock_result = EvaluationResult(instance_id="test-001", resolved=True, exit_code=0, test_log="Test passed")
        mock_evaluate.return_value = mock_result

        # Create test instances
        instances = [
            SWEFlowTestInstance(instance_id="test-001",
                                repo="test-repo",
                                problem_statement="Fix the bug",
                                base_commit="abc123",
                                reference_commit="def456",
                                patch="diff --git a/test.py b/test.py\nindex 123..456 100644\n--- a/test.py\n+++ b/test.py\n@@ -1,2 +1,2 @@\n-print('hello')\n+print('world')\n",
                                docker_image="test-image:latest",
                                FAIL_TO_PASS=["test_fail_to_pass"],
                                PASS_TO_PASS=["test_pass_to_pass"],
                                model="test-model")
        ]

        results = run_evaluation(instances, "/tmp/output")

        # Verify results
        assert len(results) == 1
        assert results[0].instance_id == "test-001"
        assert results[0].resolved is True

        # Verify output directory creation
        mock_mkdir.assert_called()

        # Verify file writing
        assert mock_write_text.call_count == 2  # report.json and test_output.log

    @patch('sweflow_bench.utils.run_evaluation.evaluate_instance')
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.write_text')
    def test_run_evaluation_with_error(self, mock_write_text, mock_mkdir, mock_evaluate):
        # Setup mock to raise EvaluationError
        mock_evaluate.side_effect = EvaluationError("test-001", 1, "Evaluation failed")

        # Create test instances
        instances = [
            SWEFlowTestInstance(instance_id="test-001",
                                repo="test-repo",
                                problem_statement="Fix the bug",
                                base_commit="abc123",
                                reference_commit="def456",
                                patch="diff --git a/test.py b/test.py\nindex 123..456 100644\n--- a/test.py\n+++ b/test.py\n@@ -1,2 +1,2 @@\n-print('hello')\n+print('world')\n",
                                docker_image="test-image:latest",
                                FAIL_TO_PASS=["test_fail_to_pass"],
                                PASS_TO_PASS=["test_pass_to_pass"],
                                model="test-model")
        ]

        results = run_evaluation(instances, "/tmp/output")

        # Verify results show failure
        assert len(results) == 1
        assert results[0].instance_id == "test-001"
        assert results[0].resolved is False
        assert results[0].exit_code == 1
        assert results[0].test_log == "Evaluation failed"

        # Verify output directory creation
        mock_mkdir.assert_called()

        # Verify file writing
        assert mock_write_text.call_count == 2  # report.json and test_output.log

    @patch('sweflow_bench.utils.run_evaluation.evaluate_instance')
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.write_text')
    def test_run_evaluation_multiple_instances(self, mock_write_text, mock_mkdir, mock_evaluate):
        # Setup mock evaluation results
        mock_evaluate.side_effect = [EvaluationResult(instance_id="test-001", resolved=True, exit_code=0, test_log="Test 1 passed"), EvaluationResult(instance_id="test-002", resolved=False, exit_code=1, test_log="Test 2 failed")]

        # Create test instances
        instances = [
            SWEFlowTestInstance(instance_id="test-001",
                                repo="test-repo",
                                problem_statement="Fix the bug",
                                base_commit="abc123",
                                reference_commit="def456",
                                patch="diff --git a/test.py b/test.py\nindex 123..456 100644\n--- a/test.py\n+++ b/test.py\n@@ -1,2 +1,2 @@\n-print('hello')\n+print('world')\n",
                                docker_image="test-image:latest",
                                FAIL_TO_PASS=["test_fail_to_pass"],
                                PASS_TO_PASS=["test_pass_to_pass"],
                                model="test-model"),
            SWEFlowTestInstance(instance_id="test-002",
                                repo="test-repo",
                                problem_statement="Fix another bug",
                                base_commit="abc123",
                                reference_commit="def456",
                                patch="diff --git a/test2.py b/test2.py\nindex 123..456 100644\n--- a/test2.py\n+++ b/test2.py\n@@ -1,2 +1,2 @@\n-print('hello')\n+print('world')\n",
                                docker_image="test-image:latest",
                                FAIL_TO_PASS=["test_fail_to_pass2"],
                                PASS_TO_PASS=["test_pass_to_pass2"],
                                model="test-model")
        ]

        results = run_evaluation(instances, "/tmp/output")

        # Verify results
        assert len(results) == 2
        assert results[0].instance_id == "test-001"
        assert results[0].resolved is True
        assert results[1].instance_id == "test-002"
        assert results[1].resolved is False

        # Verify output directory creation
        mock_mkdir.assert_called()

        # Verify file writing (2 instances * 2 files each)
        assert mock_write_text.call_count == 4
