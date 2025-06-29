import docker
import subprocess

from docker.models.containers import Container


class DockerError(Exception):

    def __init__(
        self,
        message: str,
        container: Container = None,
    ):
        self.message = message
        self.container = container
        super().__init__(self.message)


def get_docker_client():
    return docker.from_env()


def start_docker_container(
    image_name: str,
    container_name: str,
) -> Container:
    client = get_docker_client()
    try:
        container = client.containers.run(
            image=image_name,
            name=container_name,
            detach=True,
        )
        return container
    except docker.errors.APIError as e:
        raise DockerError(f"Error starting container: {e}")


def stop_docker_container(container: Container):
    try:
        container.stop()
    except docker.errors.APIError as e:
        raise DockerError(f"Error stopping container: {e}")


def remove_docker_container(container: Container):
    try:
        container.remove()
    except docker.errors.APIError as e:
        raise DockerError(f"Error removing container: {e}")


def exec_command_in_container(
    container: Container,
    command: str,
    timeout: int | None = None,
    workdir: str | None = None,
):
    try:
        if timeout is not None:
            # wrap command with timeout tool and execute through bash
            command = f"bash -c 'timeout {timeout}s {command}'"
        else:
            # execute command through bash
            command = f"bash -c '{command}'"
        exec_result = container.exec_run(command, workdir=workdir)
        return exec_result.exit_code, exec_result.output.decode("utf-8")
    except docker.errors.APIError as e:
        raise DockerError(f"Error executing command in container: {e}")


def copy_file_to_container(
    container: Container,
    local_path: str,
    container_path: str,
) -> bool:
    try:
        result = subprocess.run(
            ["docker", "cp", local_path, f"{container.id}:{container_path}"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise DockerError(f"Error copying file to container: {e.stderr}")


def read_file_from_container(
    container: Container,
    container_path: str,
) -> str:
    try:
        result = subprocess.run(
            ["docker", "exec", container.id, "cat", container_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise DockerError(f"Error reading file from container: {e.stderr}")
