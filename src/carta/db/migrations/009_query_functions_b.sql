-- Migration: Query functions B
-- Created: 2025-05-01
-- Updated: 2025-07-02

-- Compares semantic similarity between mainline and branch nodes at a turn
CREATE OR REPLACE FUNCTION carta.compare_branching_semantics(
    conversation_id UUID,
    turn_number INTEGER
) RETURNS TABLE (
    mainline_node_id UUID,
    mainline_content TEXT,
    branch_node_id UUID,
    branch_content TEXT,
    semantic_similarity FLOAT,
    branch_depth INTEGER,
    generation_type TEXT
) LANGUAGE SQL AS $$
    WITH mainline_node AS (
        SELECT 
            id,
            content,
            embedding
        FROM carta.nodes
        WHERE 
            conversation_id = compare_branching_semantics.conversation_id
            AND turn_number = compare_branching_semantics.turn_number
            AND is_mainline = TRUE
        LIMIT 1
    )
    SELECT 
        mn.id AS mainline_node_id,
        mn.content AS mainline_content,
        bn.id AS branch_node_id,
        bn.content AS branch_content,
        1 - (mn.embedding <=> bn.embedding) AS semantic_similarity,
        bn.branch_depth,
        bn.generation_type
    FROM 
        mainline_node mn,
        carta.nodes bn
    WHERE 
        bn.conversation_id = compare_branching_semantics.conversation_id
        AND bn.turn_number = compare_branching_semantics.turn_number
        AND bn.is_mainline = FALSE
    ORDER BY semantic_similarity DESC;
$$;
-- Computes average embedding vector for given node set
CREATE OR REPLACE FUNCTION carta.calculate_semantic_centroid(
    node_ids UUID[]
) RETURNS VECTOR(2000) LANGUAGE plpgsql AS $$
DECLARE
    centroid VECTOR(2000);
    node_count INTEGER;
BEGIN
    SELECT 
        AVG(embedding),
        COUNT(*)
    INTO 
        centroid,
        node_count
    FROM carta.nodes
    WHERE id = ANY(node_ids);
    
    IF node_count = 0 THEN
        RETURN NULL;
    END IF;
    
    RETURN centroid;
END;
$$;

-- Tracks semantic progression through conversation turns
CREATE OR REPLACE FUNCTION carta.semantic_evolution(
    conversation_id UUID,
    include_branches BOOLEAN DEFAULT FALSE
) RETURNS TABLE (
    turn_number INTEGER,
    mainline_embedding VECTOR(2000),
    branch_centroid VECTOR(2000),
    branch_count INTEGER,
    semantic_distance FLOAT,
    entropy FLOAT
) LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    WITH turns AS (
        SELECT DISTINCT turn_number
        FROM carta.nodes
        WHERE conversation_id = semantic_evolution.conversation_id
        ORDER BY turn_number
    ),
    mainline_nodes AS (
        SELECT 
            n.turn_number,
            n.embedding AS mainline_embedding
        FROM carta.nodes n
        WHERE 
            n.conversation_id = semantic_evolution.conversation_id
            AND n.is_mainline = TRUE
    ),
    branch_stats AS (
        SELECT 
            n.turn_number,
            carta.calculate_semantic_centroid(ARRAY_AGG(n.id)) AS branch_centroid,
            COUNT(*) AS branch_count,
            AVG(n.branch_entropy) AS entropy
        FROM carta.nodes n
        WHERE 
            n.conversation_id = semantic_evolution.conversation_id
            AND n.is_mainline = FALSE
            AND include_branches = TRUE
        GROUP BY n.turn_number
    )
    SELECT 
        t.turn_number,
        mn.mainline_embedding,
        bs.branch_centroid,
        COALESCE(bs.branch_count, 0) AS branch_count,
        CASE 
            WHEN mn.mainline_embedding IS NOT NULL AND bs.branch_centroid IS NOT NULL 
            THEN 1 - (mn.mainline_embedding <=> bs.branch_centroid)
            ELSE NULL
        END AS semantic_distance,
        COALESCE(bs.entropy, 0) AS entropy
    FROM turns t
    LEFT JOIN mainline_nodes mn ON t.turn_number = mn.turn_number
    LEFT JOIN branch_stats bs ON t.turn_number = bs.turn_number
    ORDER BY t.turn_number;
END;
$$;

-- Identifies high-potential generative nodes
CREATE OR REPLACE FUNCTION carta.find_semantic_sparks(
    conversation_id UUID,
    min_spark_factor FLOAT DEFAULT 0.5,
    limit_count INTEGER DEFAULT 10
) RETURNS TABLE (
    node_id UUID,
    content TEXT,
    role TEXT,
    turn_number INTEGER,
    spark_factor FLOAT,
    branch_count INTEGER,
    semantic_entropy FLOAT
) LANGUAGE SQL AS $$
    SELECT 
        n.id AS node_id,
        n.content,
        n.role,
        n.turn_number,
        n.node_spark_factor AS spark_factor,
        COUNT(DISTINCT c.id) AS branch_count,
        n.branch_entropy AS semantic_entropy
    FROM 
        carta.nodes n
        LEFT JOIN carta.nodes c ON n.id = c.parent_id
    WHERE 
        n.conversation_id = find_semantic_sparks.conversation_id
        AND n.node_spark_factor >= min_spark_factor
    GROUP BY 
        n.id, n.content, n.role, n.turn_number, n.node_spark_factor, n.branch_entropy
    ORDER BY 
        n.node_spark_factor DESC,
        COUNT(DISTINCT c.id) DESC
    LIMIT limit_count;
$$;