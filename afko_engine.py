#!/usr/bin/env python3
import argparse
import importlib.util
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from kismet_cloud_ingress import CloudDataIngressHub

SCRIPT_DIR = Path(__file__).resolve().parent
TPF_PATH = SCRIPT_DIR / "TPF"


def load_pipeline_module():
    if not TPF_PATH.exists():
        raise FileNotFoundError(f"Missing pipeline file: {TPF_PATH}")

    spec = importlib.util.spec_from_file_location("afko_tpf", TPF_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load pipeline module from {TPF_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dataclass
class EngineConfig:
    mode: str
    local_root: str
    query_limit: int
    start_runtime: bool
    boot_script: str
    log_file: str
    assess_only: bool


class AfkoEngine:
    def __init__(self, config: EngineConfig):
        self.config = config
        self.pipeline = load_pipeline_module()
        self.ingress = CloudDataIngressHub(db_name="kismet_cloud_vault.db")

    def discover_targets(self):
        logging.info("Discovering targets for mode=%s local_root=%s", self.config.mode, self.config.local_root)
        return self.pipeline.get_targets(mode=self.config.mode, local_root=self.config.local_root, query_limit=self.config.query_limit)

    def ingest_targets(self, targets):
        if not targets:
            logging.warning("No targets available for ingestion.")
            return

        for target in targets:
            local_dir = self.pipeline.ensure_local_repository(target)
            if not local_dir:
                logging.warning("Skipping ingestion for target %s because no local path is available.", target.get("name"))
                continue

            logging.info("Ingesting repository data for %s from %s", target.get("name"), local_dir)
            try:
                self.ingress.pull_repository_data(local_path=local_dir)
            except Exception as exc:
                logging.warning("Failed ingestion for %s: %s", target.get("name"), exc)

    def run_pipeline(self):
        logging.info("Running pipeline in mode=%s", self.config.mode)
        self.pipeline.run_pipeline(mode=self.config.mode, local_root=self.config.local_root, query_limit=self.config.query_limit)

    def start_runtime_service(self):
        if not self.config.start_runtime:
            logging.info("Runtime startup disabled.")
            return

        if not Path(self.config.boot_script).exists():
            logging.warning("Boot script not found: %s", self.config.boot_script)
            return

        logging.info("Starting runtime service using boot script: %s", self.config.boot_script)
        subprocess.run([self.config.boot_script], check=False)

    def run(self):
        targets = self.discover_targets()

        if not self.config.assess_only:
            self.ingest_targets(targets)
            self.run_pipeline()
        else:
            logging.info("Assess-only mode enabled; ingestion and pipeline are skipped.")

        self.start_runtime_service()


def parse_args():
    parser = argparse.ArgumentParser(description="AFKO execution engine for local-first repo processing.")
    parser.add_argument("--mode", choices=["local", "github", "mixed"], default=os.getenv("AFKO_PIPELINE_MODE", "mixed"))
    parser.add_argument("--local-root", default=os.getenv("AFKO_LOCAL_REPO_ROOT", "."))
    parser.add_argument("--query-limit", type=int, default=int(os.getenv("AFKO_QUERY_LIMIT", "2")))
    parser.add_argument("--start-runtime", action="store_true", default=os.getenv("AFKO_START_RUNTIME", "false").lower() in ("1", "true", "yes"))
    parser.add_argument("--boot-script", default=os.getenv("AFKO_BOOT_SCRIPT", str(SCRIPT_DIR / "kismet_boot.sh")))
    parser.add_argument("--log-file", default=os.getenv("AFKO_SERVICE_LOG", str(SCRIPT_DIR / "afko_service.log")))
    parser.add_argument("--assess-only", action="store_true")
    return parser.parse_args()


def setup_logging(log_file: str):
    log_path = Path(log_file).resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout),
        ],
    )

    logging.info("AFKO execution engine log initialized: %s", log_path)


def main():
    args = parse_args()
    setup_logging(args.log_file)

    config = EngineConfig(
        mode=args.mode,
        local_root=args.local_root,
        query_limit=args.query_limit,
        start_runtime=args.start_runtime,
        boot_script=args.boot_script,
        log_file=args.log_file,
        assess_only=args.assess_only,
    )

    engine = AfkoEngine(config)
    engine.run()


if __name__ == "__main__":
    main()
