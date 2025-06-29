import json
import logging
from pathlib import Path
from typing import List, Dict
from datasets import load_dataset
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Prediction(BaseModel):
    instance_id: str
    patch: str
    model: str


class SWEFlowInstance(BaseModel):
    instance_id: str
    repo: str
    problem_statement: str
    base_commit: str
    reference_commit: str
    patch: str
    docker_image: str
    FAIL_TO_PASS: List[str]
    PASS_TO_PASS: List[str]


class SWEFlowTestInstance(SWEFlowInstance):
    model: str

    def get_eval_script(self) -> str:
        """
        Get the eval script for the instance.
        """
        script = "python -m pytest -v"
        test_ids = self.FAIL_TO_PASS + self.PASS_TO_PASS
        return f"{script} {' '.join(test_ids)}"


def _load_dataset(dataset: str, split: str) -> Dict[str, SWEFlowInstance]:
    # TODO: Upload local datasets to HF hub
    # return load_dataset(dataset, split=split)

    logger.info(f"Loading dataset {dataset} from {Path(__file__).parent.parent.parent / 'data' / f'{dataset}.jsonl'}")

    ds = load_dataset(
        "json",
        data_files=[
            str(Path(__file__).parent.parent.parent / "data" / f"{dataset}.jsonl"),
        ],
        split="train",  # local datasets are always in train split
    )
    return {item["instance_id"]: SWEFlowInstance(**item) for item in ds}


def _load_predictions(dataset: str, split: str, predictions_path: str) -> Dict[str, Prediction]:

    if predictions_path == "gold":
        logger.info(f"Loading gold predictions for {dataset} {split}")
        ds = _load_dataset(dataset, split)
        return {
            instance_id: Prediction(
                instance_id=item.instance_id,
                patch=item.patch,
                model="gold",
            ) for instance_id, item in ds.items()
        }

    if not predictions_path.endswith(".jsonl"):
        logger.error(f"Invalid predictions path: {predictions_path}")
        raise ValueError(f"Invalid predictions path: {predictions_path}")
    logger.info(f"Loading predictions from {predictions_path} for {dataset} {split}")
    with open(predictions_path, "r") as f:
        predictions = [Prediction(**json.loads(line)) for line in f]
        return {item.instance_id: item for item in predictions}


def load_eval_instances(
    dataset: str,
    split: str,
    predictions_path: str,
    instance_ids: List[str] | None = None,
) -> List[SWEFlowTestInstance]:
    """
    Load evaluation instances from the dataset and predictions.
    """

    ds = _load_dataset(dataset, split)
    predictions = _load_predictions(dataset, split, predictions_path)

    if instance_ids is not None:
        all_instance_ids = [instance_id for instance_id in ds.keys() if instance_id in instance_ids]
        logger.info(f"Filtering dataset and predictions to only include instance IDs: {all_instance_ids}")
    else:
        all_instance_ids = list(ds.keys())

    test_instances = []
    for instance_id in all_instance_ids:
        instance_attrs = ds[instance_id].model_dump()
        # update instance attrs with predictions
        instance_attrs.update(predictions[instance_id].model_dump())
        test_instances.append(SWEFlowTestInstance(**instance_attrs))

    logger.info(f"Loaded {len(test_instances)} test instances")

    return test_instances
