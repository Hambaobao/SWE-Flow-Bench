from typing import Dict, Any

from sweflow_bench.utils.docker import (
    start_docker_container,
    stop_docker_container,
    remove_docker_container,
    read_file_from_container,
    copy_file_to_container,
    exec_command_in_container,
)


def run_evaluation(
    ds: Dict[str, Dict[str, Any]],
    predictions: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    pass
