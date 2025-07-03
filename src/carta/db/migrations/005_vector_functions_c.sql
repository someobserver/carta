-- Migration: Vector functions C
-- Created: 2025-05-01
-- Updated: 2025-07-02

-- Finds nodes with similar semantic patterns across conversations
CREATE OR REPLACE FUNCTION carta.find_recurring_patterns(
    query_vector VECTOR(2000),
    min_similarity FLOAT DEFAULT 0.8,
    limit_count INTEGER DEFAULT 10,
    role_filter TEXT DEFAULT NULL,
    exclude_conversations UUID[] DEFAULT NULL,
    embedding_model_version TEXT DEFAULT NULL
) RETURNS TABLE (
    conversation_id UUID,
    conversation_title TEXT,
    node_id UUID,
    role TEXT,
    content TEXT,
    similarity FLOAT,
    turn_number INTEGER,
    semantic_drift_since_root FLOAT,
    node_spark_factor FLOAT,
    is_mainline BOOLEAN
) LANGUAGE SQL AS $$
    SELECT 
        n.conversation_id,
        c.title AS conversation_title,
        n.id AS node_id,
        n.role,
        n.content,
        1 - (n.embedding <-> query_vector) AS similarity,
        n.turn_number,
        n.semantic_drift_since_root,
        n.node_spark_factor,
        n.is_mainline
    FROM 
        carta.nodes n
        JOIN carta.conversations c ON n.conversation_id = c.id
    WHERE 
        n.embedding IS NOT NULL
        AND 1 - (n.embedding <-> query_vector) >= min_similarity
        AND (role_filter IS NULL OR n.role = role_filter)
        AND (exclude_conversations IS NULL OR NOT (n.conversation_id = ANY(exclude_conversations)))
        AND (find_recurring_patterns.embedding_model_version IS NULL OR n.embedding_model_version = find_recurring_patterns.embedding_model_version)
    ORDER BY 
        (1 - (n.embedding <-> query_vector)) * (1 + (n.node_spark_factor * 0.2)) DESC
    LIMIT limit_count;
$$;

-- Calculates conversation branch entropy metrics
CREATE OR REPLACE FUNCTION carta.calculate_conversation_entropy(
    conversation_id UUID,
    include_full_metrics BOOLEAN DEFAULT FALSE
) RETURNS TABLE (
    turn_number INTEGER,
    branch_count INTEGER,
    avg_branch_depth FLOAT,
    entropy FLOAT,
    semantic_divergence FLOAT,
    semantic_drift_acceleration FLOAT,
    max_sibling_distance FLOAT,
    continuation_rate FLOAT,
    mainline_semantic_drift FLOAT,
    cognitive_load_avg FLOAT
) LANGUAGE SQL AS $$
    SELECT 
        n.turn_number,
        COUNT(DISTINCT n.mainline_divergence_point) AS branch_count,
        AVG(n.branch_depth) AS avg_branch_depth,
        AVG(n.branch_entropy) AS entropy,
        AVG(n.semantic_distance_from_parent) AS semantic_divergence,
        CASE WHEN include_full_metrics THEN
            AVG(n.semantic_acceleration)
        ELSE NULL END AS semantic_drift_acceleration,
        CASE WHEN include_full_metrics THEN
            MAX(n.avg_sibling_semantic_distance)
        ELSE NULL END AS max_sibling_distance,
        CASE WHEN include_full_metrics THEN
            AVG(n.sibling_lineage_continuation_rate)
        ELSE NULL END AS continuation_rate,
        CASE WHEN include_full_metrics THEN
            AVG(CASE WHEN n.is_mainline THEN n.semantic_drift_since_root ELSE NULL END)
        ELSE NULL END AS mainline_semantic_drift,
        CASE WHEN include_full_metrics THEN
            AVG(n.cognitive_load_signature)
        ELSE NULL END AS cognitive_load_avg
    FROM carta.nodes n
    WHERE 
        n.conversation_id = calculate_conversation_entropy.conversation_id
        AND (n.mainline_divergence_point IS NOT NULL OR n.is_mainline)
    GROUP BY n.turn_number
    ORDER BY n.turn_number;
$$;

-- Performs weighted search combining multiple semantic metrics
CREATE OR REPLACE FUNCTION carta.weighted_semantic_search(
    query_vector VECTOR(2000),
    conversation_id UUID,
    similarity_weight FLOAT DEFAULT 0.6,
    spark_factor_weight FLOAT DEFAULT 0.2,
    branch_entropy_weight FLOAT DEFAULT 0.1,
    semantic_drift_weight FLOAT DEFAULT 0.1,
    limit_count INTEGER DEFAULT 10,
    include_mainline_only BOOLEAN DEFAULT FALSE,
    embedding_model_version TEXT DEFAULT NULL
) RETURNS TABLE (
    node_id UUID,
    content TEXT,
    role TEXT,
    combined_score FLOAT,
    similarity FLOAT,
    node_spark_factor FLOAT,
    branch_entropy FLOAT,
    semantic_drift_since_root FLOAT,
    is_mainline BOOLEAN,
    turn_number INTEGER
) LANGUAGE SQL AS $$
    SELECT 
        n.id AS node_id,
        n.content,
        n.role,
        ((1 - (n.embedding <-> query_vector)) * similarity_weight) +
        (COALESCE(n.node_spark_factor, 0) * spark_factor_weight) +
        (COALESCE(n.branch_entropy, 0) * branch_entropy_weight) +
        (COALESCE(n.semantic_drift_since_root, 0) * semantic_drift_weight) AS combined_score,
        (1 - (n.embedding <-> query_vector)) AS similarity,
        n.node_spark_factor,
        n.branch_entropy,
        n.semantic_drift_since_root,
        n.is_mainline,
        n.turn_number
    FROM carta.nodes n
    WHERE 
        n.conversation_id = weighted_semantic_search.conversation_id
        AND (NOT include_mainline_only OR n.is_mainline = TRUE)
        AND n.embedding IS NOT NULL
        AND (weighted_semantic_search.embedding_model_version IS NULL OR n.embedding_model_version = weighted_semantic_search.embedding_model_version)
    ORDER BY 
        ((1 - (n.embedding <-> query_vector)) * similarity_weight) +
        (COALESCE(n.node_spark_factor, 0) * spark_factor_weight) +
        (COALESCE(n.branch_entropy, 0) * branch_entropy_weight) +
        (COALESCE(n.semantic_drift_since_root, 0) * semantic_drift_weight) DESC
    LIMIT limit_count;
$$;