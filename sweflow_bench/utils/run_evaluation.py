from typing import List
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel

from sweflow_bench.utils.docker import (
    start_docker_container,
    stop_docker_container,
    remove_docker_container,
    exec_command_in_container,
)
from sweflow_bench.utils.data import SWEFlowTestInstance


class EvaluationError(Exception):

    def __init__(self, instance_id: str, exit_code: int, output: str):
        self.instance_id = instance_id
        self.exit_code = exit_code
        self.output = output


class EvaluationResult(BaseModel):
    instance_id: str
    resolved: bool
    exit_code: int
    test_output: str


def evaluate_instance(instance: SWEFlowTestInstance) -> EvaluationResult:
    """
    Evaluate the given instance.
    """
    # step 1: start docker container
    container = start_docker_container(
        image_name=instance.docker_image,
        container_name=f"sweflow-bench-{instance.instance_id}-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}",
    )

    # step 2: move container:/testbed to container:/workspace
    exit_code, output = exec_command_in_container(
        container,
        "mv /testbed /workspace",
        timeout=30,  # 30 seconds
    )
    if exit_code != 0:
        raise EvaluationError(instance.instance_id, exit_code, output)

    # step 3: checkout to base_commit
    exit_code, output = exec_command_in_container(
        container,
        f"git checkout {instance.base_commit}",
        timeout=30,  # 30 seconds
    )
    if exit_code != 0:
        raise EvaluationError(instance.instance_id, exit_code, output)

    # step 4: write patch to container:/tmp/patch.diff
    exit_code, output = exec_command_in_container(
        container,
        f"echo '{instance.patch}' > /tmp/patch.diff",
        timeout=30,  # 30 seconds
    )
    if exit_code != 0:
        raise EvaluationError(instance.instance_id, exit_code, output)

    # step 5: apply patch
    exit_code, output = exec_command_in_container(
        container,
        f"git apply /tmp/patch.diff",
        timeout=30,  # 30 seconds
    )
    if exit_code != 0:
        raise EvaluationError(instance.instance_id, exit_code, output)

    # step 6: run eval script
    eval_script = instance.get_eval_script()
    exit_code, output = exec_command_in_container(
        container,
        eval_script,
        timeout=900,  # 15 minutes
    )

    evaluation_result = EvaluationResult(
        instance_id=instance.instance_id,
        resolved=exit_code == 0,
        exit_code=exit_code,
        test_output=output,
    )

    # step 7: stop and remove container
    stop_docker_container(container)
    remove_docker_container(container)

    return evaluation_result


def run_evaluation(
    instances: List[SWEFlowTestInstance],
    output_dir: str,
) -> List[EvaluationResult]:
    """
    Run evaluation for the given instances.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    results = []
    for instance in instances:
        # evaluate instance
        try:
            evaluation_result = evaluate_instance(instance)
        except EvaluationError as e:
            evaluation_result = EvaluationResult(
                instance_id=instance.instance_id,
                resolved=False,
                exit_code=e.exit_code,
                test_output=e.output,
            )

        # save evaluation results
        instance_report_path = Path(output_dir) / instance.instance_id / "report.json"
        instance_report_path.parent.mkdir(parents=True, exist_ok=True)
        instance_report_path.write_text(evaluation_result.model_dump_json(indent=4))

        results.append(evaluation_result)

    return results
