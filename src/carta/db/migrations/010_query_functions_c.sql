-- Migration: Query functions C
-- Created: 2025-05-01
-- Updated: 2025-07-02

-- Detects terminated branches with remaining potential
CREATE OR REPLACE FUNCTION carta.find_semantic_dead_ends(
    conversation_id UUID,
    min_semantic_potential FLOAT DEFAULT 0.6,
    limit_count INTEGER DEFAULT 10
) RETURNS TABLE (
    node_id UUID,
    content TEXT,
    role TEXT,
    turn_number INTEGER,
    branch_depth INTEGER,
    is_terminal BOOLEAN,
    semantic_drift_since_root FLOAT,
    unrealized_potential FLOAT
) LANGUAGE SQL AS $$
    SELECT 
        n.id AS node_id,
        n.content,
        n.role,
        n.turn_number,
        n.branch_depth,
        n.is_terminal,
        n.semantic_drift_since_root,
        (n.cognitive_load_signature * 0.3 + 
        COALESCE(n.branch_entropy, 0) * 0.3 + 
        COALESCE(n.semantic_acceleration, 0) * 0.4) AS unrealized_potential
    FROM carta.nodes n
    WHERE 
        n.conversation_id = find_semantic_dead_ends.conversation_id
        AND n.is_terminal = TRUE
        AND n.is_mainline = FALSE
        AND (n.cognitive_load_signature * 0.3 + 
            COALESCE(n.branch_entropy, 0) * 0.3 + 
            COALESCE(n.semantic_acceleration, 0) * 0.4) >= min_semantic_potential
    ORDER BY 
        (n.cognitive_load_signature * 0.3 + 
        COALESCE(n.branch_entropy, 0) * 0.3 + 
        COALESCE(n.semantic_acceleration, 0) * 0.4) DESC
    LIMIT limit_count;
$$;

-- Computes node influence metrics for a conversation
-- Influence score combines descendant count (60%) and semantic similarity (40%)
CREATE OR REPLACE FUNCTION carta.compute_semantic_influence(
    conversation_id UUID
) RETURNS TABLE (
    node_id UUID,
    content TEXT,
    role TEXT,
    turn_number INTEGER,
    influence_score FLOAT,
    descendant_count INTEGER,
    semantic_reach FLOAT
) LANGUAGE plpgsql AS $$
DECLARE
    total_nodes INTEGER;
BEGIN
    -- Normalization factor for descendant count
    SELECT COUNT(*) INTO total_nodes
    FROM carta.nodes
    WHERE conversation_id = compute_semantic_influence.conversation_id;
    
    RETURN QUERY
    WITH RECURSIVE node_descendants AS (
        -- Anchor: nodes with direct lineage
        SELECT 
            n.id AS node_id,
            ARRAY[n.id] AS descendant_ids,
            1 AS depth,
            ARRAY[n.embedding] AS descendant_embeddings
        FROM carta.nodes n
        WHERE 
            n.conversation_id = compute_semantic_influence.conversation_id
        
        UNION ALL
        
        -- Recursion: accumulate descendants (depth-limited)
        SELECT 
            nd.node_id,
            nd.descendant_ids || n.id,
            nd.depth + 1,
            nd.descendant_embeddings || n.embedding
        FROM carta.nodes n
        JOIN node_descendants nd ON n.parent_id = ANY(nd.descendant_ids)
        WHERE nd.depth < 5 -- Performance safeguard
    ),
    influence_stats AS (
        -- Aggregate descendant metrics per node
        SELECT 
            node_id,
            COUNT(DISTINCT descendant_ids) - 1 AS descendant_count,
            CASE 
                WHEN array_length(descendant_embeddings, 1) > 1 THEN
                    (SELECT AVG(1 - (descendant_embeddings[1] <=> e))
                    FROM unnest(descendant_embeddings[2:array_length(descendant_embeddings, 1)]) AS e)
                ELSE 0
            END AS semantic_reach
        FROM (
            SELECT 
                node_id,
                array_agg(DISTINCT unnest(descendant_ids)) AS descendant_ids,
                array_agg(DISTINCT unnest(descendant_embeddings)) AS descendant_embeddings
            FROM node_descendants
            GROUP BY node_id
        ) AS agg_descendants
    )
    SELECT 
        n.id AS node_id,
        n.content,
        n.role,
        n.turn_number,
        (i.descendant_count::FLOAT / NULLIF(total_nodes, 0) * 0.6 + COALESCE(i.semantic_reach, 0) * 0.4) AS influence_score,
        i.descendant_count,
        COALESCE(i.semantic_reach, 0) AS semantic_reach
    FROM 
        carta.nodes n
        JOIN influence_stats i ON n.id = i.node_id
    ORDER BY 
        (i.descendant_count::FLOAT / NULLIF(total_nodes, 0) * 0.6 + COALESCE(i.semantic_reach, 0) * 0.4) DESC;
END;
$$; 