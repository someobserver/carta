-- Migration: Query functions A
-- Created: 2025-05-01
-- Updated: 2025-07-02

-- Retrieves all nodes in a conversation branch starting from divergence point
CREATE OR REPLACE FUNCTION carta.get_complete_branch(
    divergence_point_id UUID
) RETURNS TABLE (
    node_id UUID,
    parent_id UUID,
    content TEXT,
    role TEXT,
    turn_number INTEGER,
    branch_depth INTEGER,
    generation_type TEXT,
    semantic_drift_since_root FLOAT,
    semantic_distance_from_parent FLOAT,
    branch_level INTEGER
) LANGUAGE SQL AS $$
    WITH RECURSIVE branch_nodes AS (
        SELECT 
            n.id AS node_id,
            n.parent_id,
            n.content,
            n.role,
            n.turn_number,
            n.branch_depth,
            n.generation_type,
            n.semantic_drift_since_root,
            n.semantic_distance_from_parent,
            1 AS branch_level
        FROM carta.nodes n
        WHERE n.mainline_divergence_point = divergence_point_id
        
        UNION ALL
        
        SELECT 
            n.id AS node_id,
            n.parent_id,
            n.content,
            n.role,
            n.turn_number,
            n.branch_depth,
            n.generation_type,
            n.semantic_drift_since_root,
            n.semantic_distance_from_parent,
            bn.branch_level + 1
        FROM carta.nodes n
        JOIN branch_nodes bn ON n.parent_id = bn.node_id
    )
    SELECT 
        n.id AS node_id,
        n.parent_id,
        n.content,
        n.role,
        n.turn_number,
        n.branch_depth,
        n.generation_type,
        n.semantic_drift_since_root,
        n.semantic_distance_from_parent,
        0 AS branch_level
    FROM carta.nodes n
    WHERE n.id = divergence_point_id
    
    UNION ALL
    
    SELECT * FROM branch_nodes
    ORDER BY branch_level, turn_number;
$$;

-- Enumerates possible conversation paths from a given node
CREATE OR REPLACE FUNCTION carta.find_alternate_paths(
    node_id UUID,
    max_depth INTEGER DEFAULT 3
) RETURNS TABLE (
    path_id INTEGER,
    node_sequence JSONB,
    path_depth INTEGER,
    avg_semantic_drift FLOAT,
    is_terminal BOOLEAN,
    terminal_node_id UUID
) LANGUAGE plpgsql AS $$
DECLARE
    base_node_record RECORD;
    conversation_id_val UUID;
    turn_number_val INTEGER;
BEGIN
    SELECT n.conversation_id, n.turn_number INTO base_node_record
    FROM carta.nodes n
    WHERE n.id = node_id;
    
    conversation_id_val := base_node_record.conversation_id;
    turn_number_val := base_node_record.turn_number;
    
    RETURN QUERY
    WITH RECURSIVE alt_paths(path_id, start_node, current_node, node_sequence, depth, semantic_drift_sum, node_count, is_terminal) AS (
        SELECT 
            ROW_NUMBER() OVER (ORDER BY n.semantic_distance_from_parent) AS path_id,
            node_id AS start_node,
            n.id AS current_node,
            jsonb_build_array(jsonb_build_object(
                'id', n.id,
                'turn', n.turn_number,
                'role', n.role,
                'content', n.content
            )) AS node_sequence,
            1 AS depth,
            COALESCE(n.semantic_distance_from_parent, 0) AS semantic_drift_sum,
            1 AS node_count,
            n.is_terminal AS is_terminal
        FROM carta.nodes n
        WHERE 
            n.conversation_id = conversation_id_val
            AND n.turn_number = turn_number_val
        
        UNION ALL
        
        SELECT 
            ap.path_id,
            ap.start_node,
            n.id AS current_node,
            ap.node_sequence || jsonb_build_object(
                'id', n.id,
                'turn', n.turn_number,
                'role', n.role,
                'content', n.content
            ) AS node_sequence,
            ap.depth + 1 AS depth,
            ap.semantic_drift_sum + COALESCE(n.semantic_distance_from_parent, 0) AS semantic_drift_sum,
            ap.node_count + 1 AS node_count,
            n.is_terminal AS is_terminal
        FROM carta.nodes n
        JOIN alt_paths ap ON n.parent_id = ap.current_node
        WHERE ap.depth < max_depth AND NOT ap.is_terminal
    )
    SELECT 
        path_id,
        node_sequence,
        depth AS path_depth,
        semantic_drift_sum / NULLIF(node_count, 0) AS avg_semantic_drift,
        is_terminal,
        current_node AS terminal_node_id
    FROM alt_paths
    WHERE depth = max_depth OR is_terminal
    ORDER BY path_id;
END;
$$;