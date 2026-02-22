#!/usr/bin/env python3
"""
Compliance Engine - Main Entry Point
=====================================
Scalable compliance engine for cross-border data transfer evaluation.

Usage:
    python main.py                    # Run the API server
    python main.py --build-graph      # Build the rules graph
    python main.py --upload-data FILE # Upload data from JSON file
    python main.py --test            # Run tests
"""

import argparse
import logging
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings


def setup_logging():
    """Configure logging"""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def run_server():
    """Run the API server"""
    from api.main import run
    run()


def build_graph(incremental: bool = False):
    """Build the rules graph"""
    from utils.graph_builder import build_rules_graph
    build_rules_graph(clear_existing=not incremental)


def upload_data(file_path: str, clear: bool = False):
    """Upload data from JSON file"""
    from utils.data_uploader import upload_data as do_upload
    do_upload(file_path, clear_existing=clear)


def run_tests():
    """Run the test suite"""
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v"],
        cwd=str(Path(__file__).parent)
    )
    sys.exit(result.returncode)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Compliance Engine - Scalable data transfer compliance evaluation"
    )

    parser.add_argument(
        "--build-graph",
        action="store_true",
        help="Build the RulesGraph from dictionaries"
    )

    parser.add_argument(
        "--upload-data",
        metavar="FILE",
        help="Upload data from a JSON file"
    )

    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Build graph incrementally (MERGE, no clear) instead of full rebuild"
    )

    parser.add_argument(
        "--clear-data",
        action="store_true",
        help="Clear existing data before upload"
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Run the test suite"
    )

    parser.add_argument(
        "--host",
        default=settings.api.host,
        help=f"API host (default: {settings.api.host})"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=settings.api.port,
        help=f"API port (default: {settings.api.port})"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run in debug mode"
    )

    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger(__name__)

    if args.build_graph:
        mode = "incremental" if args.incremental else "full"
        logger.info(f"Building RulesGraph ({mode} mode)...")
        build_graph(incremental=args.incremental)
        logger.info("RulesGraph build complete!")

    elif args.upload_data:
        logger.info(f"Uploading data from {args.upload_data}...")
        upload_data(args.upload_data, args.clear_data)
        logger.info("Data upload complete!")

    elif args.test:
        logger.info("Running tests...")
        run_tests()

    else:
        # Update settings if command line args provided
        if args.debug:
            settings.api.debug = True
            settings.api.reload = True

        logger.info(f"Starting Compliance Engine v{settings.app_version}")
        logger.info(f"Server: http://{args.host}:{args.port}")
        logger.info(f"Docs: http://{args.host}:{args.port}/docs")

        run_server()


if __name__ == "__main__":
    main()
