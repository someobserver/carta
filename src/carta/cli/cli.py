"""
Command-line interface for CARTA conversation processing.

Provides CLI commands for parsing ChatGPT exports and generating
semantic embeddings from conversation trees.
"""

import argparse
import logging
import sys
from pathlib import Path

from ..parser import CartaParser
from ..embedder import CartaEmbedder
from ..config import Config

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    """Configure logging with specified level."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )


def parse_cli() -> None:
    """Parse ChatGPT JSON exports into conversation trees."""
    parser = argparse.ArgumentParser(
        description='Parse ChatGPT JSON exports into recursive conversation trees.'
    )
    parser.add_argument(
        'input_files',
        nargs='+',
        help='Input JSON files to parse'
    )
    parser.add_argument(
        '-o', '--output-dir',
        help='Output directory for parsed files'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Set logging level'
    )

    args = parser.parse_args()
    setup_logging(args.log_level)
    config = Config()

    carta_parser = CartaParser(
        output_dir=args.output_dir or str(config.default_output_dir)
    )

    for input_file in args.input_files:
        input_path = Path(input_file)
        if not input_path.exists():
            logger.error(f"Input file not found: {input_file}")
            continue

        parsed_data = carta_parser.parse_file(str(input_path))
        if parsed_data:
            output_path = carta_parser.save_to_json(
                parsed_data,
                f"{input_path.stem}_parsed.json"
            )
            logger.info(f"Saved parsed data to {output_path}")
        else:
            logger.error(f"Failed to parse {input_file}")

def embed_cli() -> None:
    """CLI command for generating embeddings from parsed conversation trees."""
    parser = argparse.ArgumentParser(
        description='Generate semantic embeddings for parsed conversation trees.'
    )
    parser.add_argument(
        'input_files',
        nargs='+',
        help='Input parsed JSON files to embed'
    )
    parser.add_argument(
        '-o', '--output-dir',
        help='Output directory for embedded files'
    )
    parser.add_argument(
        '--api-key',
        help='OpenAI API key (overrides OPENAI_API_KEY environment variable)'
    )
    parser.add_argument(
        '--model',
        default='text-embedding-3-large',
        help='OpenAI embedding model to use'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Set logging level'
    )

    args = parser.parse_args()
    setup_logging(args.log_level)

    config = Config()
    api_key = args.api_key or config.openai_api_key
    if not api_key:
        logger.error("No OpenAI API key provided")
        sys.exit(1)

    output_dir = Path(args.output_dir) if args.output_dir else config.default_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        embedder = CartaEmbedder(api_key=api_key, model=args.model)
    except Exception as e:
        logger.error(f"Embedder initialization failed: {e}")
        sys.exit(1)

    for input_file in args.input_files:
        input_path = Path(input_file)
        if not input_path.exists():
            logger.error(f"Input file not found: {input_file}")
            continue

        try:
            enriched_data = embedder.process_file(str(input_path))
            output_filename = input_path.stem.replace('_parsed', '') + '_embedded.json'
            output_path = output_dir / output_filename
            embedder.save_to_json(enriched_data, str(output_path))
            logger.info(f"Saved embeddings to {output_path}")
        except Exception as e:
            logger.error(f"Embedding failed for {input_file}: {e}")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'parse':
        sys.argv.pop(1)
        parse_cli()
    elif len(sys.argv) > 1 and sys.argv[1] == 'embed':
        sys.argv.pop(1)
        embed_cli()
    else:
        print("Usage: python -m carta.cli parse|embed [options]")
        sys.exit(1)
