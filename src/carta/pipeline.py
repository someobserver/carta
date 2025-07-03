"""
Integrated pipeline for processing ChatGPT conversations.

This provides the main Pipeline class orchestrating the processing 
workflow: (1) parsing ChatGPT JSON exports into conversation trees,
(2) generating semantic embeddings, (3 optional) storing results in PostgreSQL.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from .parser import CartaParser
from .embedder import CartaEmbedder
from .db import DatabaseClient
from .config import Config

logger = logging.getLogger(__name__)


class Pipeline:
    """Conversation tree integration pipeline."""

    def __init__(self,
                 config: Optional[Config] = None,
                 store_to_database: bool = True,
                 output_dir: Optional[str] = None):
        """Initialize the pipeline.

        Args:
            config: Configuration object. If None, creates a new Config instance.
            store_to_database: Whether to store results to database
            output_dir: Optional output directory for JSON files
        """
        self.config = config or Config()
        self.store_to_database = store_to_database

        # Validate configuration requirements
        if not self.config.validate():
            missing = self.config.get_missing_config()
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

        if self.store_to_database and not self.config.validate_database():
            missing = self.config.get_missing_database_config()
            raise ValueError(f"Missing database configuration: {', '.join(missing)}")

        # Initialize processing components
        self.parser = CartaParser(output_dir=output_dir)
        self.embedder = CartaEmbedder(
            api_key=self.config.openai_api_key,
            model=self.config.default_embedding_model
        )

        if self.store_to_database:
            self.db_client = DatabaseClient(self.config)

            # Test database connection
            if not self.db_client.test_connection():
                raise ConnectionError("Failed to connect to database")
            logger.info("Database connection verified")
        else:
            self.db_client = None
            logger.info("No database connection configured, running in file-only mode")

    def process_file(self, file_path: str, save_intermediates: bool = False) -> List[str]:
        """Process a single ChatGPT JSON export file.

        Args:
            file_path: export file path
            save_intermediates: save intermediate JSON files to disk

        Returns:
            List of conversation IDs
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")

        logger.info(f"Processing file: {file_path}")

        # Step 1: Parse conversation tree structure
        logger.info("Parsing conversation tree...")
        conversations = self.parser.parse_file(str(file_path))

        if not conversations:
            logger.error("Failed to parse conversation")
            return []

        logger.info(f"Parsed {len(conversations)} conversations")

        # Save intermediate parsed data if requested
        if save_intermediates:
            parsed_file = file_path.stem + '_parsed.json'
            saved_path = self.parser.save_to_json(conversations, parsed_file)
            logger.info(f"Saved parsed data to {saved_path}")

        # Step 2: Generate semantic embeddings
        logger.info("Generating semantic embeddings...")
        enriched_conversations = []

        for i, conversation in enumerate(conversations):
            logger.info(f"Embedding conversation {i+1}/{len(conversations)}")
            enriched = self.embedder.process_conversation(conversation)
            enriched_conversations.append(enriched)

        logger.info("Embeddings generation complete")

        # Save intermediate embedded data if requested
        if save_intermediates:
            embedded_file = file_path.stem + '_embedded.json'
            self.embedder.save_to_json(enriched_conversations, embedded_file)
            logger.info(f"Saved embedded data to {embedded_file}")

        # Step 3: Store to database (if configured)
        conversation_ids = []
        if self.store_to_database:
            logger.info("Storing to database...")

            for i, conversation in enumerate(enriched_conversations):
                logger.info(f"Storing conversation {i+1}/{len(enriched_conversations)}")
                try:
                    conversation_id = self.db_client.store_conversation(conversation)
                    conversation_ids.append(conversation_id)
                    logger.info(f"Stored conversation {conversation_id}")
                except Exception as e:
                    logger.error(f"Failed to store conversation {i+1}: {e}")

            logger.info(f"Database storage complete. Stored {len(conversation_ids)} conversations")
        else:
            for conversation in enriched_conversations:
                conv_id = conversation.get('conversation', {}).get('id', 'unknown')
                conversation_ids.append(conv_id)

        logger.info(f"Pipeline complete. Processed {len(conversation_ids)} conversations")
        return conversation_ids

    def process_files(self, file_paths: List[str], save_intermediates: bool = False) -> Dict[str, List[str]]:
        """Process multiple ChatGPT JSON export files.

        Args:
            file_paths: List of paths to ChatGPT JSON export files
            save_intermediates: save intermediate JSON files to disk

        Returns:
            Dictionary mapping file paths to lists of conversation IDs
        """
        results = {}

        for file_path in file_paths:
            try:
                conversation_ids = self.process_file(file_path, save_intermediates)
                results[file_path] = conversation_ids
                logger.info(f"Successfully processed {file_path}: {len(conversation_ids)} conversations")
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                results[file_path] = []

        total_conversations = sum(len(conv_ids) for conv_ids in results.values())
        logger.info(f"Batch processing complete. Total conversations processed: {total_conversations}")

        return results

    def get_conversation_summary(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of a stored conversation.

        Args:
            conversation_id: The conversation ID to summarize

        Returns:
            Dictionary with conversation summary or None if not found
        """
        if not self.db_client:
            logger.warning("No database client available for summary retrieval")
            return None

        return self.db_client.get_conversation_summary(conversation_id)
