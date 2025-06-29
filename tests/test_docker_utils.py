import pytest
import docker
import subprocess

from unittest.mock import patch, MagicMock
from docker.models.containers import Container

from sweflow_bench.utils import docker as docker_utils


def test_start_docker_container_success():
    with patch.object(docker_utils, "get_docker_client") as mock_client:
        mock_container = MagicMock(spec=Container)
        mock_client.return_value.containers.run.return_value = mock_container
        result = docker_utils.start_docker_container("busybox", "test")
        assert result == mock_container


def test_start_docker_container_error():
    with patch.object(docker_utils, "get_docker_client") as mock_client:
        mock_client.return_value.containers.run.side_effect = docker.errors.APIError("fail")
        with pytest.raises(docker_utils.DockerError):
            docker_utils.start_docker_container("busybox", "test")


def test_stop_docker_container_success():
    container = MagicMock(spec=Container)
    docker_utils.stop_docker_container(container)
    container.stop.assert_called_once()


def test_stop_docker_container_error():
    container = MagicMock(spec=Container)
    container.stop.side_effect = docker.errors.APIError("fail")
    with pytest.raises(docker_utils.DockerError):
        docker_utils.stop_docker_container(container)


def test_remove_docker_container_success():
    container = MagicMock(spec=Container)
    docker_utils.remove_docker_container(container)
    container.remove.assert_called_once()


def test_remove_docker_container_error():
    container = MagicMock(spec=Container)
    container.remove.side_effect = docker.errors.APIError("fail")
    with pytest.raises(docker_utils.DockerError):
        docker_utils.remove_docker_container(container)


def test_exec_command_in_container_success():
    container = MagicMock(spec=Container)
    container.exec_run.return_value = MagicMock(exit_code=0, output=b"hello")
    code, output = docker_utils.exec_command_in_container(container, "echo hello")
    assert code == 0
    assert output == b"hello"


def test_exec_command_in_container_with_timeout():
    container = MagicMock(spec=Container)
    container.exec_run.return_value = MagicMock(exit_code=0, output=b"timeout")
    code, output = docker_utils.exec_command_in_container(container, "echo timeout", timeout=1)
    assert code == 0
    assert output == b"timeout"


def test_exec_command_in_container_error():
    container = MagicMock(spec=Container)
    container.exec_run.side_effect = docker.errors.APIError("fail")
    with pytest.raises(docker_utils.DockerError):
        docker_utils.exec_command_in_container(container, "echo hello")


@patch("subprocess.run")
def test_copy_file_to_container_success(mock_run):
    mock_run.return_value = MagicMock()
    assert docker_utils.copy_file_to_container("cid", "/tmp/a", "/b") is None  # function returns None


@patch("subprocess.run")
def test_copy_file_to_container_error(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, "docker cp", "fail")
    with pytest.raises(docker_utils.DockerError):
        docker_utils.copy_file_to_container("cid", "/tmp/a", "/b")


@patch("subprocess.run")
def test_read_file_from_container_success(mock_run):
    mock_run.return_value = MagicMock(stdout="file content")
    assert docker_utils.read_file_from_container("cid", "/b") == "file content"


@patch("subprocess.run")
def test_read_file_from_container_error(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, "docker exec", "fail")
    with pytest.raises(docker_utils.DockerError):
        docker_utils.read_file_from_container("cid", "/b")
