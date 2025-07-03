-- Migration: Vector functions E
-- Created: 2025-05-01
-- Updated: 2025-07-02

-- Retrieves all descendant nodes with configurable depth limit
CREATE OR REPLACE FUNCTION carta.get_all_descendants(
    node_id UUID,
    max_depth INTEGER DEFAULT 10
) RETURNS TABLE (
    descendant_id UUID,
    content TEXT,
    role TEXT,
    generation_type TEXT,
    depth INTEGER,
    path TEXT[]
) LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE descendants AS (
        SELECT 
            n.id AS descendant_id,
            n.content,
            n.role,
            n.generation_type,
            1 AS depth,
            ARRAY[n.id::TEXT] AS path
        FROM carta.nodes n
        WHERE n.parent_id = node_id
        
        UNION ALL
        
        SELECT 
            n.id,
            n.content,
            n.role,
            n.generation_type,
            d.depth + 1,
            d.path || n.id::TEXT
        FROM carta.nodes n
        JOIN descendants d ON n.parent_id = d.descendant_id
        WHERE d.depth < max_depth
    )
    SELECT * FROM descendants
    ORDER BY depth, descendant_id;
END;
$$;

-- Identifies nodes with missing embeddings for a given conversation
CREATE OR REPLACE FUNCTION carta.check_missing_embeddings(
    conversation_id UUID
) RETURNS TABLE (
    node_id UUID,
    role TEXT,
    turn_number INTEGER,
    create_time TIMESTAMP WITH TIME ZONE,
    is_mainline BOOLEAN
) LANGUAGE SQL AS $$
    SELECT 
        id AS node_id,
        role,
        turn_number,
        create_time,
        is_mainline
    FROM carta.nodes
    WHERE 
        conversation_id = check_missing_embeddings.conversation_id
        AND embedding IS NULL
    ORDER BY turn_number, create_time;
$$;