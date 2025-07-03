-- Migration: Vector functions A
-- Created: 2025-05-01
-- Updated: 2025-07-02

-- Retrieves conversation nodes similar to query vector with configurable filters
CREATE OR REPLACE FUNCTION carta.find_similar_nodes(
    query_vector VECTOR(2000),
    conversation_id UUID,
    limit_count INTEGER DEFAULT 10,
    similarity_threshold FLOAT DEFAULT 0.7,
    include_mainline_only BOOLEAN DEFAULT FALSE,
    min_semantic_drift FLOAT DEFAULT NULL,
    max_semantic_drift FLOAT DEFAULT NULL,
    generation_type TEXT DEFAULT NULL,
    branch_entropy_threshold FLOAT DEFAULT NULL,
    spark_factor_threshold FLOAT DEFAULT NULL,
    embedding_model_version TEXT DEFAULT NULL
) RETURNS TABLE (
    node_id UUID,
    similarity FLOAT,
    role TEXT,
    content TEXT,
    turn_number INTEGER,
    is_mainline BOOLEAN,
    branch_depth INTEGER,
    generation_type TEXT,
    semantic_drift_since_root FLOAT,
    branch_entropy FLOAT,
    node_spark_factor FLOAT
) LANGUAGE SQL AS $$
    SELECT 
        id AS node_id,
        1 - (embedding <-> query_vector) AS similarity,
        role,
        content,
        turn_number,
        is_mainline,
        branch_depth,
        generation_type,
        semantic_drift_since_root,
        branch_entropy,
        node_spark_factor
    FROM carta.nodes
    WHERE 
        conversation_id = find_similar_nodes.conversation_id
        AND (NOT include_mainline_only OR is_mainline = TRUE)
        AND embedding IS NOT NULL
        AND 1 - (embedding <-> query_vector) >= similarity_threshold
        AND (min_semantic_drift IS NULL OR semantic_drift_since_root >= min_semantic_drift)
        AND (max_semantic_drift IS NULL OR semantic_drift_since_root <= max_semantic_drift)
        AND (generation_type IS NULL OR nodes.generation_type = find_similar_nodes.generation_type)
        AND (branch_entropy_threshold IS NULL OR branch_entropy >= branch_entropy_threshold)
        AND (spark_factor_threshold IS NULL OR node_spark_factor >= spark_factor_threshold)
        AND (find_similar_nodes.embedding_model_version IS NULL OR nodes.embedding_model_version = find_similar_nodes.embedding_model_version)
    ORDER BY similarity DESC
    LIMIT limit_count;
$$;

-- Finds prompt-response pairs similar to query vector with semantic filters
CREATE OR REPLACE FUNCTION carta.find_similar_pairs(
    query_vector VECTOR(2000),
    conversation_id UUID,
    limit_count INTEGER DEFAULT 10,
    similarity_threshold FLOAT DEFAULT 0.7,
    include_mainline_only BOOLEAN DEFAULT FALSE,
    min_coherence FLOAT DEFAULT NULL,
    min_abstraction_delta FLOAT DEFAULT NULL,
    max_abstraction_delta FLOAT DEFAULT NULL,
    min_downstream_spark FLOAT DEFAULT NULL,
    embedding_model_version TEXT DEFAULT NULL
) RETURNS TABLE (
    pair_id UUID,
    similarity FLOAT,
    prompt_id UUID,
    response_id UUID,
    prompt_content TEXT,
    response_content TEXT,
    is_mainline BOOLEAN,
    branch_depth INTEGER,
    generation_type TEXT,
    coherence_score FLOAT,
    semantic_drift FLOAT,
    abstraction_delta FLOAT,
    downstream_spark_factor FLOAT
) LANGUAGE SQL AS $$
    SELECT 
        p.id AS pair_id,
        1 - (p.embedding <-> query_vector) AS similarity,
        p.prompt_id,
        p.response_id,
        np.content AS prompt_content,
        nr.content AS response_content,
        p.is_mainline,
        p.branch_depth,
        p.generation_type,
        p.coherence_score,
        p.semantic_drift,
        p.abstraction_delta,
        p.downstream_spark_factor
    FROM 
        carta.pairs p
        JOIN carta.nodes np ON p.prompt_id = np.id
        JOIN carta.nodes nr ON p.response_id = nr.id
    WHERE 
        p.conversation_id = find_similar_pairs.conversation_id
        AND (NOT include_mainline_only OR p.is_mainline = TRUE)
        AND p.embedding IS NOT NULL
        AND 1 - (p.embedding <-> query_vector) >= similarity_threshold
        AND (min_coherence IS NULL OR p.coherence_score >= min_coherence)
        AND (min_abstraction_delta IS NULL OR p.abstraction_delta >= min_abstraction_delta)
        AND (max_abstraction_delta IS NULL OR p.abstraction_delta <= max_abstraction_delta)
        AND (min_downstream_spark IS NULL OR p.downstream_spark_factor >= min_downstream_spark)
        AND (find_similar_pairs.embedding_model_version IS NULL OR p.embedding_model_version = find_similar_pairs.embedding_model_version)
    ORDER BY similarity DESC
    LIMIT limit_count;
$$;

-- Retrieves divergent branches from specified node with sorting options
CREATE OR REPLACE FUNCTION carta.find_node_branches(
    node_id UUID,
    limit_count INTEGER DEFAULT 10,
    include_semantic_metrics BOOLEAN DEFAULT TRUE,
    min_semantic_distance FLOAT DEFAULT NULL,
    max_semantic_distance FLOAT DEFAULT NULL,
    sort_by TEXT DEFAULT 'semantic_distance'
) RETURNS TABLE (
    divergent_node_id UUID,
    content TEXT,
    semantic_distance FLOAT,
    branch_depth INTEGER,
    turn_number INTEGER,
    generation_type TEXT,
    branch_entropy FLOAT,
    semantic_drift_since_root FLOAT,
    node_spark_factor FLOAT
) LANGUAGE SQL AS $$
    SELECT 
        id AS divergent_node_id,
        content,
        semantic_distance_from_parent AS semantic_distance,
        branch_depth,
        turn_number,
        generation_type,
        branch_entropy,
        semantic_drift_since_root,
        node_spark_factor
    FROM carta.nodes
    WHERE 
        mainline_divergence_point = node_id
        AND (min_semantic_distance IS NULL OR semantic_distance_from_parent >= min_semantic_distance)
        AND (max_semantic_distance IS NULL OR semantic_distance_from_parent <= max_semantic_distance)
    ORDER BY 
        CASE 
            WHEN sort_by = 'semantic_distance' THEN semantic_distance_from_parent
            WHEN sort_by = 'branch_depth' THEN branch_depth
            WHEN sort_by = 'turn_number' THEN turn_number
            WHEN sort_by = 'branch_entropy' THEN branch_entropy
            WHEN sort_by = 'spark_factor' THEN node_spark_factor
            ELSE semantic_distance_from_parent
        END ASC
    LIMIT limit_count;
$$;