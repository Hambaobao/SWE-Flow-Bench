import argparse
import logging

from sweflow_bench.utils.data import load_eval_instances

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=str, required=True, help="Dataset to evaluate.")
    parser.add_argument("--split", type=str, required=True, help="Split to evaluate.")
    parser.add_argument("--prediction-path", type=str, required=True, help="Path to the predictions.")
    parser.add_argument("--output-dir", type=str, required=True, help="Output directory to save the results.")
    parser.add_argument("--instance-ids", type=str, nargs="+", default=None, help="Instance IDs to evaluate.")

    args = parser.parse_args()

    return args


def main():
    args = parse_args()

    ds, predictions = load_eval_instances(
        args.dataset,
        args.split,
        args.prediction_path,
        args.instance_ids,
    )


if __name__ == "__main__":
    main()
