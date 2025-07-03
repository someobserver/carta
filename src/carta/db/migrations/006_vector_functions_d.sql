-- Migration: Vector functions D
-- Created: 2025-05-01
-- Updated: 2025-07-02

-- Finds conversation nodes with similar lineage paths from root
CREATE OR REPLACE FUNCTION carta.find_nodes_with_similar_ancestry(
    node_id UUID,
    limit_count INTEGER DEFAULT 10,
    min_path_similarity FLOAT DEFAULT 0.7,
    max_depth INTEGER DEFAULT 20
) RETURNS TABLE (
    target_node_id UUID,
    target_content TEXT,
    target_role TEXT,
    path_similarity FLOAT,
    common_ancestry_depth INTEGER,
    semantic_drift_difference FLOAT,
    conversation_id UUID,
    conversation_title TEXT
) LANGUAGE plpgsql AS $$
DECLARE
    source_conversation_id UUID;
    source_path JSONB;
    source_drift FLOAT;
    source_embedding_model TEXT;
BEGIN
    -- Retrieve source node metadata
    SELECT 
        n.conversation_id, 
        n.path_from_root,
        n.semantic_drift_since_root,
        n.embedding_model_version
    INTO 
        source_conversation_id,
        source_path,
        source_drift,
        source_embedding_model
    FROM carta.nodes n
    WHERE n.id = node_id;
    
    -- Validate source node data
    IF source_path IS NULL OR jsonb_array_length(source_path) = 0 THEN
        RAISE WARNING 'Source node % has no valid path_from_root', node_id;
        RETURN;
    END IF;
    
    -- Apply depth limit to path analysis
    IF jsonb_array_length(source_path) > max_depth THEN
        source_path = source_path->0->(max_depth-1);
    END IF;
    
    RETURN QUERY
    SELECT 
        n.id AS target_node_id,
        n.content AS target_content,
        n.role AS target_role,
        CASE 
            WHEN jsonb_array_length(n.path_from_root) > 0 AND jsonb_array_length(source_path) > 0 THEN
                ((jsonb_array_length(source_path) + jsonb_array_length(n.path_from_root)) / 
                (2.0 * GREATEST(jsonb_array_length(source_path), jsonb_array_length(n.path_from_root)))) *
                (1.0 - ABS(n.semantic_drift_since_root - source_drift) / GREATEST(n.semantic_drift_since_root, source_drift, 0.1))
            ELSE 0.0
        END AS path_similarity,
        (
            SELECT COUNT(*)
            FROM (
                SELECT DISTINCT unnest(ARRAY(SELECT jsonb_array_elements_text(source_path)))
                INTERSECT
                SELECT DISTINCT unnest(ARRAY(SELECT jsonb_array_elements_text(n.path_from_root)))
            ) AS common_elements
        ) AS common_ancestry_depth,
        ABS(n.semantic_drift_since_root - source_drift) AS semantic_drift_difference,
        n.conversation_id,
        c.title AS conversation_title
    FROM 
        carta.nodes n
        JOIN carta.conversations c ON n.conversation_id = c.id
    WHERE 
        n.id != node_id
        AND n.embedding IS NOT NULL
        AND jsonb_array_length(n.path_from_root) > 0
        AND jsonb_array_length(n.path_from_root) <= max_depth
        AND (source_embedding_model IS NULL OR n.embedding_model_version = source_embedding_model)
        AND (
            CASE 
                WHEN jsonb_array_length(n.path_from_root) > 0 AND jsonb_array_length(source_path) > 0 THEN
                    ((jsonb_array_length(source_path) + jsonb_array_length(n.path_from_root)) / 
                    (2.0 * GREATEST(jsonb_array_length(source_path), jsonb_array_length(n.path_from_root)))) *
                    (1.0 - ABS(n.semantic_drift_since_root - source_drift) / GREATEST(n.semantic_drift_since_root, source_drift, 0.1))
                ELSE 0.0
            END
        ) >= min_path_similarity
    ORDER BY path_similarity DESC, common_ancestry_depth DESC
    LIMIT limit_count;
END;
$$;

-- Computes aggregated metrics for all nodes branching from a divergence point
CREATE OR REPLACE FUNCTION carta.calculate_branch_metrics(
    divergence_point_id UUID,
    max_depth INTEGER DEFAULT 10
) RETURNS TABLE (
    branch_divergence_point_id UUID,
    branch_node_count INTEGER,
    max_branch_depth INTEGER,
    avg_branch_depth FLOAT,
    total_semantic_drift FLOAT,
    avg_semantic_drift FLOAT,
    max_semantic_drift FLOAT,
    branch_entropy FLOAT,
    terminal_node_count INTEGER,
    spark_factor FLOAT
) LANGUAGE plpgsql AS $$
DECLARE
    result RECORD;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM carta.nodes WHERE id = divergence_point_id) THEN
        RAISE EXCEPTION 'Divergence point % does not exist', divergence_point_id;
    END IF;
    
    WITH branch_nodes AS (
        SELECT 
            n.id, 
            n.branch_depth,
            n.semantic_drift_since_root,
            n.is_terminal,
            n.branch_entropy,
            n.node_spark_factor
        FROM carta.nodes n
        WHERE 
            n.mainline_divergence_point = divergence_point_id
            AND n.branch_depth <= max_depth
            AND n.embedding IS NOT NULL
    )
    SELECT 
        divergence_point_id AS branch_divergence_point_id,
        COUNT(*) AS branch_node_count,
        MAX(branch_depth) AS max_branch_depth,
        AVG(branch_depth) AS avg_branch_depth,
        SUM(semantic_drift_since_root) AS total_semantic_drift,
        AVG(semantic_drift_since_root) AS avg_semantic_drift,
        MAX(semantic_drift_since_root) AS max_semantic_drift,
        AVG(branch_entropy) AS branch_entropy,
        COUNT(CASE WHEN is_terminal THEN 1 END) AS terminal_node_count,
        MAX(node_spark_factor) AS spark_factor
    INTO result
    FROM branch_nodes;
    
    RETURN QUERY SELECT
        result.branch_divergence_point_id,
        result.branch_node_count,
        result.max_branch_depth,
        result.avg_branch_depth,
        result.total_semantic_drift,
        result.avg_semantic_drift,
        result.max_semantic_drift,
        result.branch_entropy,
        result.terminal_node_count,
        result.spark_factor;
END;
$$;