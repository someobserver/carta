-- Migration: Indexes
-- Created: 2025-05-01
-- Updated: 2025-07-02

-- Primary indexes
CREATE INDEX idx_nodes_parent_id ON carta.nodes(parent_id);
CREATE INDEX idx_nodes_conversation_id ON carta.nodes(conversation_id);
CREATE INDEX idx_nodes_conversation_turn ON carta.nodes(conversation_id, turn_number);
CREATE INDEX idx_nodes_mainline ON carta.nodes(conversation_id, is_mainline);
CREATE INDEX idx_nodes_generation_type ON carta.nodes(conversation_id, generation_type);
CREATE INDEX idx_nodes_mainline_divergence ON carta.nodes(mainline_divergence_point);
CREATE INDEX idx_nodes_replaced_node ON carta.nodes(replaced_node_id);

-- Semantic metric indexes
CREATE INDEX idx_nodes_semantic_drift ON carta.nodes(conversation_id, semantic_drift_since_root);
CREATE INDEX idx_nodes_branch_entropy ON carta.nodes(conversation_id, branch_entropy);
CREATE INDEX idx_nodes_node_spark ON carta.nodes(conversation_id, node_spark_factor);
CREATE INDEX idx_nodes_cognitive_load ON carta.nodes(conversation_id, cognitive_load_signature);
CREATE INDEX idx_nodes_semantic_acceleration ON carta.nodes(conversation_id, semantic_acceleration);
CREATE INDEX idx_nodes_semantic_distance_from_parent ON carta.nodes(conversation_id, semantic_distance_from_parent);
CREATE INDEX idx_nodes_avg_sibling_distance ON carta.nodes(conversation_id, avg_sibling_semantic_distance);

-- Pair relationship indexes
CREATE INDEX idx_pairs_conversation_id ON carta.pairs(conversation_id);
CREATE INDEX idx_pairs_prompt_id ON carta.pairs(prompt_id);
CREATE INDEX idx_pairs_response_id ON carta.pairs(response_id);
CREATE INDEX idx_pairs_mainline ON carta.pairs(conversation_id, is_mainline);
CREATE INDEX idx_pairs_generation_type ON carta.pairs(conversation_id, generation_type);
CREATE INDEX idx_pairs_divergence_point ON carta.pairs(divergence_point);

-- Pair semantic indexes
CREATE INDEX idx_pairs_semantic_drift ON carta.pairs(conversation_id, semantic_drift);
CREATE INDEX idx_pairs_coherence ON carta.pairs(conversation_id, coherence_score);
CREATE INDEX idx_pairs_abstraction ON carta.pairs(conversation_id, abstraction_delta);
CREATE INDEX idx_pairs_spark_factor ON carta.pairs(conversation_id, downstream_spark_factor);
CREATE INDEX idx_pairs_continuity ON carta.pairs(conversation_id, dialogic_continuity_score);

-- Path traversal indexes
CREATE INDEX idx_paths_conversation_id ON carta.paths(conversation_id);
CREATE INDEX idx_paths_node_id ON carta.paths(node_id);
CREATE INDEX idx_paths_ancestor_id ON carta.paths(ancestor_id);
CREATE INDEX idx_paths_mainline ON carta.paths(conversation_id, is_mainline_path);
CREATE INDEX idx_paths_distance ON carta.paths(conversation_id, distance);
CREATE INDEX idx_paths_semantic_drift ON carta.paths(conversation_id, semantic_drift_along_path);

-- Embedding version indexes
CREATE INDEX idx_nodes_embedding_version ON carta.nodes(embedding_model_version);
CREATE INDEX idx_pairs_embedding_version ON carta.pairs(embedding_model_version);

-- Vector search indexes (HNSW)
CREATE INDEX idx_nodes_embedding ON carta.nodes 
    USING hnsw (embedding vector_cosine_ops) 
    WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_pairs_embedding ON carta.pairs 
    USING hnsw (embedding vector_cosine_ops) 
    WITH (m = 16, ef_construction = 64);

-- Composite vector indexes
CREATE INDEX idx_nodes_embedding_mainline ON carta.nodes(is_mainline, conversation_id) 
    INCLUDE (embedding);

CREATE INDEX idx_nodes_embedding_generation ON carta.nodes(generation_type, conversation_id) 
    INCLUDE (embedding);

CREATE INDEX idx_pairs_embedding_mainline ON carta.pairs(is_mainline, conversation_id) 
    INCLUDE (embedding);

-- JSONB path indexes
CREATE INDEX idx_nodes_path_from_root ON carta.nodes USING GIN (path_from_root jsonb_path_ops);
CREATE INDEX idx_nodes_children_ids ON carta.nodes USING GIN (children_ids jsonb_path_ops);
CREATE INDEX idx_pairs_path_from_root ON carta.pairs USING GIN (path_from_root jsonb_path_ops);
CREATE INDEX idx_paths_path_nodes ON carta.paths USING GIN (path_nodes jsonb_path_ops);

-- Metric documentation table
CREATE TABLE carta.scale_documentation (
    metric_name TEXT PRIMARY KEY,
    table_name TEXT NOT NULL,
    scale_min FLOAT,
    scale_max FLOAT,
    interpretation TEXT NOT NULL,
    calculation_method TEXT,
    normalized BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Metric documentation values
INSERT INTO carta.scale_documentation
(metric_name, table_name, scale_min, scale_max, interpretation, calculation_method, normalized)
VALUES
('coherence_score', 'pairs', 0.0, 1.0, 'Measures semantic alignment between prompt and response. Higher values indicate stronger alignment.', 'Cosine similarity between prompt and response embeddings.', TRUE),
('semantic_drift', 'pairs', 0.0, 2.0, 'Semantic distance between prompt and response. Lower values indicate less meaning shift.', 'Cosine distance between prompt and response embeddings.', TRUE),
('semantic_drift_since_root', 'nodes', 0.0, NULL, 'Cumulative semantic distance from the conversation start. Higher values indicate greater meaning evolution.', 'Sum of semantic distances along the path from root.', FALSE),
('branch_entropy', 'nodes', 0.0, NULL, 'Diversity of meaning at a branch point. Higher values indicate greater semantic diversity.', 'Information entropy calculation on sibling semantic distances.', FALSE),
('node_spark_factor', 'nodes', 0.0, 1.0, 'Generative potential of a node. Higher values indicate greater potential for productive branches.', 'Composite score based on semantic richness and child generation patterns.', TRUE),
('downstream_spark_factor', 'pairs', 0.0, 1.0, 'Generative potential of a dialog exchange. Higher values indicate exchanges that sparked productive continuation.', 'Derived from child branch patterns and semantic diversity.', TRUE),
('abstraction_delta', 'pairs', -1.0, 1.0, 'Change in abstraction level from prompt to response. Positive values indicate increasing abstraction, negative values indicate greater specificity.', 'Calculated from embedding position in abstraction space.', TRUE),
('dialogic_continuity_score', 'pairs', 0.0, 1.0, 'Thematic continuity with previous exchanges. Higher values indicate stronger narrative continuity.', 'Semantic similarity with previous exchange context.', TRUE),
('branch_signature_pattern', 'pairs', NULL, NULL, 'Encoded description of branch structure and pattern. Format: "Depth:N|Breadth:N|Pattern:{linear|bushy|sparse}"', 'String encoding of branch structure attributes.', FALSE),
('sibling_semantic_convergence_pattern', 'nodes', NULL, NULL, 'Pattern of semantic similarity among siblings. Format: "Convergent|Divergent|Mixed|Clustered:N"', 'Clustering analysis of sibling embeddings.', FALSE); 