import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from sweflow_bench.utils.data import (
    Prediction,
    SWEFlowInstance,
    SWEFlowTestInstance,
    _load_dataset,
    _load_predictions,
    load_eval_instances,
)


class TestPrediction:

    def test_prediction_creation(self):
        prediction = Prediction(instance_id="test-001", patch="diff --git a/test.py b/test.py\nindex 123..456 100644\n--- a/test.py\n+++ b/test.py\n@@ -1,2 +1,2 @@\n-print('hello')\n+print('world')\n", model="test-model")
        assert prediction.instance_id == "test-001"
        assert prediction.patch.startswith("diff --git")
        assert prediction.model == "test-model"


class TestSWEFlowInstance:

    def test_sweflow_instance_creation(self):
        instance = SWEFlowInstance(instance_id="test-001",
                                   repo="test-repo",
                                   problem_statement="Fix the bug",
                                   base_commit="abc123",
                                   reference_commit="def456",
                                   patch="diff --git a/test.py b/test.py\nindex 123..456 100644\n--- a/test.py\n+++ b/test.py\n@@ -1,2 +1,2 @@\n-print('hello')\n+print('world')\n",
                                   docker_image="test-image:latest",
                                   FAIL_TO_PASS=["test_fail_to_pass"],
                                   PASS_TO_PASS=["test_pass_to_pass"])
        assert instance.instance_id == "test-001"
        assert instance.repo == "test-repo"
        assert instance.problem_statement == "Fix the bug"
        assert instance.base_commit == "abc123"
        assert instance.reference_commit == "def456"
        assert instance.docker_image == "test-image:latest"
        assert instance.FAIL_TO_PASS == ["test_fail_to_pass"]
        assert instance.PASS_TO_PASS == ["test_pass_to_pass"]


class TestSWEFlowTestInstance:

    def test_sweflow_test_instance_creation(self):
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
        assert instance.instance_id == "test-001"
        assert instance.model == "test-model"

    def test_get_eval_script(self):
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
        eval_script = instance.get_eval_script()
        expected_script = "python -m pytest -v test_fail_to_pass test_pass_to_pass"
        assert eval_script == expected_script

    def test_get_eval_script_empty_tests(self):
        instance = SWEFlowTestInstance(instance_id="test-001",
                                       repo="test-repo",
                                       problem_statement="Fix the bug",
                                       base_commit="abc123",
                                       reference_commit="def456",
                                       patch="diff --git a/test.py b/test.py\nindex 123..456 100644\n--- a/test.py\n+++ b/test.py\n@@ -1,2 +1,2 @@\n-print('hello')\n+print('world')\n",
                                       docker_image="test-image:latest",
                                       FAIL_TO_PASS=[],
                                       PASS_TO_PASS=[],
                                       model="test-model")
        eval_script = instance.get_eval_script()
        expected_script = "python -m pytest -v "
        assert eval_script == expected_script


class TestLoadDataset:

    @patch('sweflow_bench.utils.data.load_dataset')
    def test_load_dataset(self, mock_load_dataset):
        # Mock dataset data
        mock_data = [{
            "instance_id": "test-001",
            "repo": "test-repo",
            "problem_statement": "Fix the bug",
            "base_commit": "abc123",
            "reference_commit": "def456",
            "patch": "diff --git a/test.py b/test.py\nindex 123..456 100644\n--- a/test.py\n+++ b/test.py\n@@ -1,2 +1,2 @@\n-print('hello')\n+print('world')\n",
            "docker_image": "test-image:latest",
            "FAIL_TO_PASS": ["test_fail_to_pass"],
            "PASS_TO_PASS": ["test_pass_to_pass"]
        }]

        mock_dataset = MagicMock()
        mock_dataset.__iter__ = lambda x: iter(mock_data)
        mock_load_dataset.return_value = mock_dataset

        result = _load_dataset("test-dataset", "train")

        assert "test-001" in result
        assert isinstance(result["test-001"], SWEFlowInstance)
        assert result["test-001"].instance_id == "test-001"
        assert result["test-001"].repo == "test-repo"


class TestLoadPredictions:

    def test_load_predictions_gold(self):
        with patch('sweflow_bench.utils.data._load_dataset') as mock_load_dataset:
            # Mock dataset data
            mock_instance = SWEFlowInstance(instance_id="test-001",
                                            repo="test-repo",
                                            problem_statement="Fix the bug",
                                            base_commit="abc123",
                                            reference_commit="def456",
                                            patch="gold-patch",
                                            docker_image="test-image:latest",
                                            FAIL_TO_PASS=["test_fail_to_pass"],
                                            PASS_TO_PASS=["test_pass_to_pass"])
            mock_load_dataset.return_value = {"test-001": mock_instance}

            result = _load_predictions("test-dataset", "train", "gold")

            assert "test-001" in result
            assert isinstance(result["test-001"], Prediction)
            assert result["test-001"].instance_id == "test-001"
            assert result["test-001"].patch == "gold-patch"
            assert result["test-001"].model == "gold"

    def test_load_predictions_from_file(self):
        predictions_data = [{"instance_id": "test-001", "patch": "predicted-patch", "model": "test-model"}]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for pred in predictions_data:
                f.write(json.dumps(pred) + '\n')
            temp_file = f.name

        try:
            result = _load_predictions("test-dataset", "train", temp_file)

            assert "test-001" in result
            assert isinstance(result["test-001"], Prediction)
            assert result["test-001"].instance_id == "test-001"
            assert result["test-001"].patch == "predicted-patch"
            assert result["test-001"].model == "test-model"
        finally:
            Path(temp_file).unlink()

    def test_load_predictions_invalid_path(self):
        with pytest.raises(ValueError, match="Invalid predictions path"):
            _load_predictions("test-dataset", "train", "invalid.txt")


class TestLoadEvalInstances:

    @patch('sweflow_bench.utils.data._load_dataset')
    @patch('sweflow_bench.utils.data._load_predictions')
    def test_load_eval_instances(self, mock_load_predictions, mock_load_dataset):
        # Mock dataset data
        mock_instance = SWEFlowInstance(instance_id="test-001",
                                        repo="test-repo",
                                        problem_statement="Fix the bug",
                                        base_commit="abc123",
                                        reference_commit="def456",
                                        patch="original-patch",
                                        docker_image="test-image:latest",
                                        FAIL_TO_PASS=["test_fail_to_pass"],
                                        PASS_TO_PASS=["test_pass_to_pass"])
        mock_load_dataset.return_value = {"test-001": mock_instance}

        # Mock predictions data
        mock_prediction = Prediction(instance_id="test-001", patch="predicted-patch", model="test-model")
        mock_load_predictions.return_value = {"test-001": mock_prediction}

        result = load_eval_instances("test-dataset", "train", "predictions.jsonl")

        assert len(result) == 1
        assert isinstance(result[0], SWEFlowTestInstance)
        assert result[0].instance_id == "test-001"
        assert result[0].patch == "predicted-patch"  # Should use prediction patch
        assert result[0].model == "test-model"

    @patch('sweflow_bench.utils.data._load_dataset')
    @patch('sweflow_bench.utils.data._load_predictions')
    def test_load_eval_instances_with_filter(self, mock_load_predictions, mock_load_dataset):
        # Mock dataset data
        mock_instance = SWEFlowInstance(instance_id="test-001",
                                        repo="test-repo",
                                        problem_statement="Fix the bug",
                                        base_commit="abc123",
                                        reference_commit="def456",
                                        patch="original-patch",
                                        docker_image="test-image:latest",
                                        FAIL_TO_PASS=["test_fail_to_pass"],
                                        PASS_TO_PASS=["test_pass_to_pass"])
        mock_load_dataset.return_value = {"test-001": mock_instance}

        # Mock predictions data
        mock_prediction = Prediction(instance_id="test-001", patch="predicted-patch", model="test-model")
        mock_load_predictions.return_value = {"test-001": mock_prediction}

        result = load_eval_instances("test-dataset", "train", "predictions.jsonl", instance_ids=["test-001"])

        assert len(result) == 1
        assert result[0].instance_id == "test-001"

    @patch('sweflow_bench.utils.data._load_dataset')
    @patch('sweflow_bench.utils.data._load_predictions')
    def test_load_eval_instances_with_filter_no_match(self, mock_load_predictions, mock_load_dataset):
        # Mock dataset data
        mock_instance = SWEFlowInstance(instance_id="test-001",
                                        repo="test-repo",
                                        problem_statement="Fix the bug",
                                        base_commit="abc123",
                                        reference_commit="def456",
                                        patch="original-patch",
                                        docker_image="test-image:latest",
                                        FAIL_TO_PASS=["test_fail_to_pass"],
                                        PASS_TO_PASS=["test_pass_to_pass"])
        mock_load_dataset.return_value = {"test-001": mock_instance}

        # Mock predictions data
        mock_prediction = Prediction(instance_id="test-001", patch="predicted-patch", model="test-model")
        mock_load_predictions.return_value = {"test-001": mock_prediction}

        result = load_eval_instances("test-dataset", "train", "predictions.jsonl", instance_ids=["test-002"])

        assert len(result) == 0
