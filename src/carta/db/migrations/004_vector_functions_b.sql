-- Migration: Vector functions B
-- Created: 2025-05-01
-- Updated: 2025-07-02

-- Retrieves full node path from root to target with optional semantic metrics
CREATE OR REPLACE FUNCTION carta.get_path_to_node(
    target_node_id UUID,
    include_semantic_metrics BOOLEAN DEFAULT TRUE
) RETURNS TABLE (
    node_id UUID,
    content TEXT,
    role TEXT,
    turn_number INTEGER,
    is_mainline BOOLEAN,
    branch_depth INTEGER,
    generation_type TEXT,
    semantic_drift_since_root FLOAT,
    semantic_distance_from_parent FLOAT, 
    node_spark_factor FLOAT,
    path_order INTEGER
) LANGUAGE SQL AS $$
    WITH RECURSIVE node_path AS (
        -- Target node as starting point
        SELECT 
            n.id,
            n.content,
            n.role,
            n.turn_number,
            n.is_mainline,
            n.branch_depth,
            n.generation_type,
            n.semantic_drift_since_root,
            n.semantic_distance_from_parent,
            n.node_spark_factor,
            n.parent_id,
            0 AS path_order
        FROM carta.nodes n
        WHERE n.id = target_node_id
        
        UNION ALL
        
        -- Recursively traverse parent nodes
        SELECT 
            n.id,
            n.content,
            n.role,
            n.turn_number,
            n.is_mainline,
            n.branch_depth,
            n.generation_type,
            n.semantic_drift_since_root,
            n.semantic_distance_from_parent,
            n.node_spark_factor,
            n.parent_id,
            p.path_order - 1
        FROM carta.nodes n
        JOIN node_path p ON n.id = p.parent_id
        WHERE p.path_order > -50  -- Recursion depth safeguard
    )
    SELECT 
        id AS node_id,
        content,
        role,
        turn_number,
        is_mainline,
        branch_depth,
        generation_type,
        semantic_drift_since_root,
        semantic_distance_from_parent,
        node_spark_factor,
        ABS(path_order) AS path_order
    FROM node_path
    ORDER BY path_order;
$$;

-- Computes semantic distance between two nodes using specified metric
CREATE OR REPLACE FUNCTION carta.calculate_semantic_drift(
    node_id_1 UUID,
    node_id_2 UUID,
    drift_method TEXT DEFAULT 'cosine'
) RETURNS FLOAT LANGUAGE plpgsql AS $$
DECLARE
    result FLOAT;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM carta.nodes 
        WHERE id IN (node_id_1, node_id_2) 
        AND embedding IS NOT NULL
    ) THEN
        RETURN NULL;
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM carta.nodes n1
        JOIN carta.nodes n2 ON n1.id = node_id_1 AND n2.id = node_id_2
        WHERE n1.embedding_model_version != n2.embedding_model_version
        AND n1.embedding_model_version IS NOT NULL
        AND n2.embedding_model_version IS NOT NULL
    ) THEN
        RAISE WARNING 'Embedding model version mismatch between nodes';
    END IF;

    SELECT 
        CASE
            WHEN drift_method = 'cosine' THEN 1 - (n1.embedding <=> n2.embedding)
            WHEN drift_method = 'euclidean' THEN n1.embedding <-> n2.embedding
            WHEN drift_method = 'inner' THEN 1 - (n1.embedding <#> n2.embedding)
            ELSE 1 - (n1.embedding <=> n2.embedding)
        END
    INTO result
    FROM 
        carta.nodes n1,
        carta.nodes n2
    WHERE 
        n1.id = node_id_1
        AND n2.id = node_id_2
        AND n1.embedding IS NOT NULL
        AND n2.embedding IS NOT NULL;
    
    RETURN result;
END;
$$;

-- Identifies semantically similar conversation branches to query vector
CREATE OR REPLACE FUNCTION carta.find_similar_branches(
    query_vector VECTOR(2000),
    conversation_id UUID,
    min_branch_depth INTEGER DEFAULT 1,
    limit_count INTEGER DEFAULT 10,
    min_similarity FLOAT DEFAULT 0.5,
    include_terminal_only BOOLEAN DEFAULT FALSE,
    max_depth INTEGER DEFAULT 10
) RETURNS TABLE (
    divergence_point UUID,
    divergence_content TEXT,
    divergence_turn_number INTEGER,
    branch_node_count INTEGER,
    avg_branch_depth FLOAT,
    avg_semantic_drift FLOAT,
    max_semantic_drift FLOAT,
    branch_entropy FLOAT,
    terminal_node_count INTEGER,
    max_node_spark_factor FLOAT,
    avg_semantic_acceleration FLOAT
) LANGUAGE SQL AS $$
    WITH branch_nodes AS (
        SELECT 
            n.mainline_divergence_point,
            COUNT(*) AS node_count,
            AVG(n.branch_depth) AS avg_depth,
            AVG(n.semantic_drift_since_root) AS avg_drift,
            MAX(n.semantic_drift_since_root) AS max_drift,
            AVG(n.branch_entropy) AS avg_entropy,
            COUNT(CASE WHEN n.is_terminal THEN 1 END) AS terminal_count,
            MAX(n.node_spark_factor) AS max_spark,
            AVG(n.semantic_acceleration) AS avg_acceleration
        FROM carta.nodes n
        WHERE 
            n.conversation_id = find_similar_branches.conversation_id
            AND n.mainline_divergence_point IS NOT NULL
            AND n.branch_depth >= min_branch_depth
            AND n.branch_depth <= max_depth
            AND n.embedding IS NOT NULL
            AND (NOT include_terminal_only OR EXISTS (
                SELECT 1 FROM carta.nodes t 
                WHERE t.parent_id = n.id AND t.is_terminal
            ))
            AND 1 - (n.embedding <-> query_vector) >= min_similarity
        GROUP BY n.mainline_divergence_point
    )
    SELECT 
        bn.mainline_divergence_point AS divergence_point,
        dp.content AS divergence_content,
        dp.turn_number AS divergence_turn_number,
        bn.node_count AS branch_node_count,
        bn.avg_depth AS avg_branch_depth,
        bn.avg_drift AS avg_semantic_drift,
        bn.max_drift AS max_semantic_drift,
        bn.avg_entropy AS branch_entropy,
        bn.terminal_count AS terminal_node_count,
        bn.max_spark AS max_node_spark_factor,
        bn.avg_acceleration AS avg_semantic_acceleration
    FROM 
        branch_nodes bn
        JOIN carta.nodes dp ON bn.mainline_divergence_point = dp.id
    ORDER BY 
        (bn.avg_drift * 0.4 + bn.avg_entropy * 0.3 + bn.max_spark * 0.3) DESC,
        bn.node_count DESC
    LIMIT limit_count;
$$;