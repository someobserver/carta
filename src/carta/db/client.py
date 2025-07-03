"""PostgreSQL client for conversation data persistence."""

import logging
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import json

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import DictCursor, execute_values
import psycopg2.sql

from ..config import Config

logger = logging.getLogger(__name__)


class DatabaseClient:
    """PostgreSQL client for conversation data operations."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize database client with configuration."""
        self.config = config or Config()
        
        if not self.config.validate_database():
            missing = self.config.get_missing_database_config()
            raise ValueError(f"Missing database configuration: {', '.join(missing)}")
    
    def get_connection_params(self) -> Dict[str, Any]:
        """Return psycopg2 connection parameters."""
        return {
            'host': self.config.database_host,
            'port': self.config.database_port,
            'database': self.config.database_name,
            'user': self.config.database_user,
            'password': self.config.database_password,
            'cursor_factory': DictCursor
        }
    
    @contextmanager
    def get_connection(self):
        """Database connection context manager with error handling."""
        conn = None
        try:
            conn = psycopg2.connect(**self.get_connection_params())
            logger.debug("Database connection established")
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
                logger.debug("Database connection closed")
    
    @contextmanager
    def get_cursor(self, conn=None):
        """Database cursor context manager."""
        if conn:
            cursor = conn.cursor()
            try:
                yield cursor
            finally:
                cursor.close()
        else:
            with self.get_connection() as connection:
                with connection.cursor() as cursor:
                    yield cursor
    
    def test_connection(self) -> bool:
        """Test database connectivity."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    logger.info("Database connection test successful")
                    return result[0] == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def insert_conversation(self, conversation_data: Dict[str, Any], conn=None) -> str:
        """Insert conversation record, return conversation ID."""
        conversation = conversation_data.get('conversation', {})
        
        # Convert Unix timestamps to datetime objects
        create_time = None
        update_time = None
        
        if 'create_time' in conversation and conversation['create_time']:
            create_time = datetime.fromtimestamp(conversation['create_time'])
        
        if 'update_time' in conversation and conversation['update_time']:
            update_time = datetime.fromtimestamp(conversation['update_time'])
        
        if not create_time:
            create_time = datetime.now()
        if not update_time:
            update_time = datetime.now()
        
        conversation_id = conversation.get('id') or str(uuid.uuid4())
        
        insert_query = """
            INSERT INTO carta.conversations (
                id, title, create_time, update_time, default_model_slug,
                current_node, root_id, description, metadata, embedding_model_version
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                update_time = EXCLUDED.update_time,
                current_node = EXCLUDED.current_node,
                metadata = EXCLUDED.metadata
            RETURNING id
        """
        
        values = (
            conversation_id,
            conversation.get('title', 'Untitled Conversation'),
            create_time,
            update_time,
            conversation.get('default_model_slug'),
            conversation.get('current_node'),
            conversation.get('root_id'),
            conversation.get('description'),
            json.dumps(conversation.get('metadata', {})),
            self.config.default_embedding_model
        )
        
        if conn:
            with self.get_cursor(conn) as cursor:
                cursor.execute(insert_query, values)
                result = cursor.fetchone()
                return result['id']
        else:
            with self.get_connection() as connection:
                with self.get_cursor(connection) as cursor:
                    cursor.execute(insert_query, values)
                    result = cursor.fetchone()
                    connection.commit()
                    return result['id']
    
    def insert_nodes(self, conversation_id: str, nodes_data: Dict[str, Dict[str, Any]], conn=None) -> None:
        """Bulk insert conversation nodes."""
        if not nodes_data:
            logger.warning("No nodes to insert")
            return
        
        node_records = []
        for node_id, node in nodes_data.items():
            create_time = None
            if 'create_time' in node and node['create_time']:
                create_time = datetime.fromtimestamp(node['create_time'])
            else:
                create_time = datetime.now()
            
            derived = node.get('derived', {})
            
            embedding = node.get('embedding')
            embedding_generated_at = datetime.now() if embedding else None
            
            record = (
                node_id,
                conversation_id,
                node.get('parent_id'),
                node.get('role', 'unknown'),
                node.get('content', ''),
                node.get('content_type', 'text'),
                create_time,
                node.get('model_slug'),
                node.get('requested_model_slug'),
                node.get('is_visually_hidden', False),
                node.get('reasoning_status'),
                node.get('voice_mode_message', False),
                embedding,
                self.config.default_embedding_model if embedding else None,
                embedding_generated_at,
                derived.get('is_mainline', False),
                derived.get('is_terminal', False),
                derived.get('siblings_count', 0),
                derived.get('branch_depth', 0),
                json.dumps(derived.get('path_from_root', [])),
                derived.get('turn_number', 0),
                derived.get('generation_type', 'unknown'),
                derived.get('mainline_divergence_point'),
                derived.get('replaced_node_id'),
                derived.get('semantic_distance_from_parent'),
                derived.get('avg_sibling_semantic_distance'),
                derived.get('semantic_drift_since_root'),
                derived.get('semantic_acceleration'),
                derived.get('branch_entropy'),
                derived.get('seconds_since_parent'),
                derived.get('turn_density_ratio'),
                derived.get('sibling_lineage_continuation_rate'),
                derived.get('sibling_semantic_convergence_pattern'),
                derived.get('edit_chain_depth'),
                derived.get('cognitive_load_signature'),
                derived.get('node_spark_factor'),
                json.dumps(derived.get('children_ids', [])),
                json.dumps(node.get('additional_metadata', {}))
            )
            node_records.append(record)
        
        insert_query = """
            INSERT INTO carta.nodes (
                id, conversation_id, parent_id, role, content, content_type, create_time,
                model_slug, requested_model_slug, is_visually_hidden, reasoning_status,
                voice_mode_message, embedding, embedding_model_version, embedding_generated_at,
                is_mainline, is_terminal, siblings_count, branch_depth, path_from_root,
                turn_number, generation_type, mainline_divergence_point, replaced_node_id,
                semantic_distance_from_parent, avg_sibling_semantic_distance, semantic_drift_since_root,
                semantic_acceleration, branch_entropy, seconds_since_parent, turn_density_ratio,
                sibling_lineage_continuation_rate, sibling_semantic_convergence_pattern,
                edit_chain_depth, cognitive_load_signature, node_spark_factor,
                children_ids, additional_metadata
            ) VALUES %s
            ON CONFLICT (id) DO UPDATE SET
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                embedding_model_version = EXCLUDED.embedding_model_version,
                embedding_generated_at = EXCLUDED.embedding_generated_at,
                semantic_distance_from_parent = EXCLUDED.semantic_distance_from_parent,
                avg_sibling_semantic_distance = EXCLUDED.avg_sibling_semantic_distance,
                semantic_drift_since_root = EXCLUDED.semantic_drift_since_root,
                semantic_acceleration = EXCLUDED.semantic_acceleration,
                branch_entropy = EXCLUDED.branch_entropy,
                cognitive_load_signature = EXCLUDED.cognitive_load_signature,
                node_spark_factor = EXCLUDED.node_spark_factor
        """
        
        if conn:
            with self.get_cursor(conn) as cursor:
                execute_values(cursor, insert_query, node_records, template=None, page_size=100)
        else:
            with self.get_connection() as connection:
                with self.get_cursor(connection) as cursor:
                    execute_values(cursor, insert_query, node_records, template=None, page_size=100)
                    connection.commit()
        
        logger.info(f"Inserted {len(node_records)} nodes for conversation {conversation_id}")
    
    def insert_pairs(self, conversation_id: str, pairs_data: List[Dict[str, Any]], conn=None) -> None:
        """Bulk insert conversation pairs."""
        if not pairs_data:
            logger.warning("No pairs to insert")
            return
        
        pair_records = []
        for pair in pairs_data:
            pair_id = str(uuid.uuid4())
            
            derived = pair.get('derived', {})
            
            embedding = pair.get('embedding')
            embedding_generated_at = datetime.now() if embedding else None
            
            record = (
                pair_id,
                conversation_id,
                pair.get('prompt_id'),
                pair.get('response_id'),
                derived.get('is_mainline', False),
                derived.get('is_alternate', False),
                derived.get('is_terminal_arc', False),
                derived.get('branch_depth', 0),
                derived.get('generation_type', 'unknown'),
                derived.get('divergence_point'),
                derived.get('divergence_turn'),
                derived.get('exchange_position_in_branch'),
                derived.get('alternative_count', 0),
                derived.get('branch_signature_pattern'),
                json.dumps(derived.get('path_from_root', [])),
                embedding,
                self.config.default_embedding_model if embedding else None,
                embedding_generated_at,
                derived.get('coherence_score'),
                derived.get('semantic_drift'),
                derived.get('semantic_drift_from_root'),
                derived.get('abstraction_delta'),
                derived.get('dialogic_continuity_score'),
                derived.get('relative_entropy_to_siblings'),
                derived.get('downstream_spark_factor'),
                derived.get('turn_latency'),
                derived.get('time_since_previous_pair'),
                json.dumps(pair.get('additional_metadata', {}))
            )
            pair_records.append(record)
        
        insert_query = """
            INSERT INTO carta.pairs (
                id, conversation_id, prompt_id, response_id, is_mainline, is_alternate,
                is_terminal_arc, branch_depth, generation_type, divergence_point,
                divergence_turn, exchange_position_in_branch, alternative_count,
                branch_signature_pattern, path_from_root, embedding, embedding_model_version,
                embedding_generated_at, coherence_score, semantic_drift, semantic_drift_from_root,
                abstraction_delta, dialogic_continuity_score, relative_entropy_to_siblings,
                downstream_spark_factor, turn_latency, time_since_previous_pair, additional_metadata
            ) VALUES %s
            ON CONFLICT (prompt_id, response_id) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                embedding_model_version = EXCLUDED.embedding_model_version,
                embedding_generated_at = EXCLUDED.embedding_generated_at,
                coherence_score = EXCLUDED.coherence_score,
                semantic_drift = EXCLUDED.semantic_drift,
                semantic_drift_from_root = EXCLUDED.semantic_drift_from_root,
                abstraction_delta = EXCLUDED.abstraction_delta,
                dialogic_continuity_score = EXCLUDED.dialogic_continuity_score,
                relative_entropy_to_siblings = EXCLUDED.relative_entropy_to_siblings,
                downstream_spark_factor = EXCLUDED.downstream_spark_factor
        """
        
        if conn:
            with self.get_cursor(conn) as cursor:
                execute_values(cursor, insert_query, pair_records, template=None, page_size=100)
        else:
            with self.get_connection() as connection:
                with self.get_cursor(connection) as cursor:
                    execute_values(cursor, insert_query, pair_records, template=None, page_size=100)
                    connection.commit()
        
        logger.info(f"Inserted {len(pair_records)} pairs for conversation {conversation_id}")
    
    def store_conversation(self, conversation_data: Dict[str, Any]) -> str:
        """Store complete conversation with transactional consistency."""
        logger.info("Storing conversation to database")
        
        with self.get_connection() as conn:
            try:
                conversation_id = self.insert_conversation(conversation_data, conn)
                logger.info(f"Stored conversation {conversation_id}")
                
                nodes_data = conversation_data.get('nodes', {})
                if nodes_data:
                    self.insert_nodes(conversation_id, nodes_data, conn)
                
                pairs_data = conversation_data.get('pairs', [])
                if pairs_data:
                    self.insert_pairs(conversation_id, pairs_data, conn)
                
                conn.commit()
                logger.info(f"Successfully stored conversation {conversation_id} with {len(nodes_data)} nodes and {len(pairs_data)} pairs")
                
                return conversation_id
                
            except Exception as e:
                logger.error(f"Error storing conversation: {e}")
                conn.rollback()
                raise
    
    def get_conversation_summary(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve conversation summary by ID."""
        query = """
            SELECT * FROM carta.conversation_summary 
            WHERE conversation_id = %s
        """
        
        with self.get_connection() as conn:
            with self.get_cursor(conn) as cursor:
                cursor.execute(query, (conversation_id,))
                result = cursor.fetchone()
                return dict(result) if result else None 