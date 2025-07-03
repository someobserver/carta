#!/usr/bin/env python3
"""Integration tests for Carta conversation processing pipeline."""

import os
import sys
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent))

from src.carta.pipeline import Pipeline
from src.carta.config.config import Config


def main() -> None:
    """Execute pipeline integration tests."""
    config = Config()
    if not config.validate():
        missing = config.get_missing_config()
        print(f"Missing required configuration: {', '.join(missing)}")
        return

    conversation_file = Path("2025-07-02_chatgpt_Short-form_Discussion_Request.json")
    if not conversation_file.exists():
        print(f"Test file not found: {conversation_file}")
        return

    pipeline = Pipeline(store_to_database=False)

    try:
        conversation_ids = pipeline.process_file(
            str(conversation_file),
            save_intermediates=True
        )
        print(f"Processed {len(conversation_ids)} conversations")
    except Exception as e:
        print(f"Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return

    try:
        results: Dict[str, List[str]] = pipeline.process_files([str(conversation_file)])
        total_conversations = sum(len(conv_ids) for conv_ids in results.values())
        print(f"Batch processed {total_conversations} conversations")
    except Exception as e:
        print(f"Batch processing failed: {e}")
        return

    output_dir = Path("output")
    if output_dir.exists():
        output_files = list(output_dir.glob("*"))
        print(f"Found {len(output_files)} output files")


if __name__ == "__main__":
    main()