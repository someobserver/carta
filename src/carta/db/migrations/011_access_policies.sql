-- Migration: Access control and configuration for recursive memory system
-- Created: 2025-05-01
-- Updated: 2025-07-02

-- Service account setup
CREATE ROLE carta_service WITH LOGIN PASSWORD 'replace_with_secure_password';

-- Schema permissions
GRANT USAGE ON SCHEMA carta TO carta_service;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA carta TO carta_service;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA carta TO carta_service;

-- Row-level security configuration
ALTER TABLE carta.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE carta.nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE carta.pairs ENABLE ROW LEVEL SECURITY;
ALTER TABLE carta.paths ENABLE ROW LEVEL SECURITY;

-- RLS policies for service account
CREATE POLICY service_all_conversations ON carta.conversations FOR ALL TO carta_service USING (true);
CREATE POLICY service_all_nodes ON carta.nodes FOR ALL TO carta_service USING (true);
CREATE POLICY service_all_pairs ON carta.pairs FOR ALL TO carta_service USING (true);
CREATE POLICY service_all_paths ON carta.paths FOR ALL TO carta_service USING (true);

-- Function permissions
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA carta TO carta_service;

-- Analytical views
CREATE OR REPLACE VIEW carta.conversation_summary AS
SELECT 
    c.id AS conversation_id,
    c.title,
    c.create_time,
    c.update_time,
    COUNT(DISTINCT n.id) AS total_nodes,
    COUNT(DISTINCT CASE WHEN n.is_mainline THEN n.id END) AS mainline_nodes,
    COUNT(DISTINCT CASE WHEN NOT n.is_mainline THEN n.id END) AS branch_nodes,
    MAX(n.turn_number) AS max_turn_number,
    COUNT(DISTINCT p.id) AS total_pairs,
    COUNT(DISTINCT CASE WHEN n.parent_id IS NULL THEN n.id END) AS root_nodes,
    COUNT(DISTINCT CASE WHEN n.is_terminal THEN n.id END) AS terminal_nodes,
    c.semantic_tension_score,
    c.root_id,
    c.current_node
FROM 
    carta.conversations c
    LEFT JOIN carta.nodes n ON c.id = n.conversation_id
    LEFT JOIN carta.pairs p ON c.id = p.conversation_id
GROUP BY c.id, c.title, c.create_time, c.update_time, c.semantic_tension_score, c.root_id, c.current_node;

CREATE OR REPLACE VIEW carta.branch_statistics AS
SELECT 
    n.conversation_id,
    n.mainline_divergence_point,
    COUNT(*) AS branch_node_count,
    AVG(n.branch_depth) AS avg_branch_depth,
    MAX(n.branch_depth) AS max_branch_depth,
    COUNT(DISTINCT p.id) AS branch_pair_count,
    AVG(n.semantic_distance_from_parent) AS avg_semantic_distance,
    AVG(n.semantic_drift_since_root) AS avg_semantic_drift,
    MIN(CASE WHEN n.is_terminal THEN n.turn_number ELSE NULL END) AS earliest_termination,
    MAX(CASE WHEN n.is_terminal THEN n.turn_number ELSE NULL END) AS latest_termination,
    COUNT(DISTINCT CASE WHEN n.is_terminal THEN n.id END) AS terminal_node_count
FROM 
    carta.nodes n
    LEFT JOIN carta.pairs p ON (p.prompt_id = n.id OR p.response_id = n.id)
WHERE 
    n.mainline_divergence_point IS NOT NULL
GROUP BY 
    n.conversation_id, n.mainline_divergence_point;

CREATE OR REPLACE VIEW carta.semantic_drift_analysis AS
SELECT 
    n.conversation_id,
    n.turn_number,
    COUNT(DISTINCT CASE WHEN n.is_mainline THEN n.id END) AS mainline_nodes,
    COUNT(DISTINCT CASE WHEN NOT n.is_mainline THEN n.id END) AS branch_nodes,
    AVG(CASE WHEN n.is_mainline THEN n.semantic_drift_since_root ELSE NULL END) AS mainline_drift,
    AVG(CASE WHEN NOT n.is_mainline THEN n.semantic_drift_since_root ELSE NULL END) AS branch_drift,
    MAX(CASE WHEN NOT n.is_mainline THEN n.semantic_distance_from_parent ELSE NULL END) AS max_branch_distance,
    AVG(n.branch_entropy) AS avg_entropy
FROM 
    carta.nodes n
GROUP BY 
    n.conversation_id, n.turn_number
ORDER BY 
    n.conversation_id, n.turn_number;

-- Performance optimization
CREATE MATERIALIZED VIEW carta.pair_similarity_matrix AS
SELECT 
    p1.id AS pair1_id,
    p2.id AS pair2_id,
    p1.conversation_id,
    1 - (p1.embedding <=> p2.embedding) AS similarity
FROM 
    carta.pairs p1
    JOIN carta.pairs p2 ON p1.id < p2.id AND p1.conversation_id = p2.conversation_id
WHERE 
    1 - (p1.embedding <=> p2.embedding) > 0.7
ORDER BY 
    p1.conversation_id,
    1 - (p1.embedding <=> p2.embedding) DESC;

CREATE INDEX idx_pair_similarity_matrix ON carta.pair_similarity_matrix (conversation_id, similarity DESC);

-- Documentation
COMMENT ON SCHEMA carta IS 'Cognitive memory architecture schema';
COMMENT ON TABLE carta.conversations IS 'Conversation metadata with recursive structure';
COMMENT ON TABLE carta.nodes IS 'Messages with lineage and semantic metrics';
COMMENT ON TABLE carta.pairs IS 'Prompt-response pairs with semantic relationships';
COMMENT ON TABLE carta.paths IS 'Conversation tree ancestry tracking';

-- Verification (commented)
-- SELECT extname FROM pg_extension WHERE extname = 'vector';