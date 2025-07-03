-- Migration: Main schema for recursive conversation trees
-- Created: 2025-05-01
-- Updated: 2025-07-02

-- Required extension for vector operations
CREATE EXTENSION IF NOT EXISTS vector;

-- Primary schema namespace
CREATE SCHEMA IF NOT EXISTS carta;

-- Conversation metadata and state
CREATE TABLE carta.conversations (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    create_time TIMESTAMP WITH TIME ZONE NOT NULL,
    update_time TIMESTAMP WITH TIME ZONE NOT NULL,
    default_model_slug TEXT,
    current_node UUID,
    root_id UUID,
    semantic_tension_score FLOAT,
    description TEXT,
    metadata JSONB,
    embedding_model_version TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Conversation nodes
CREATE TABLE carta.nodes (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES carta.conversations(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES carta.nodes(id),
    role TEXT NOT NULL,
    content TEXT,
    content_type TEXT NOT NULL DEFAULT 'text',
    create_time TIMESTAMP WITH TIME ZONE NOT NULL,
    model_slug TEXT,
    requested_model_slug TEXT,
    is_visually_hidden BOOLEAN DEFAULT FALSE,
    reasoning_status TEXT,
    voice_mode_message BOOLEAN DEFAULT FALSE,
    
    embedding VECTOR(2000),
    embedding_model_version TEXT,
    embedding_generated_at TIMESTAMP WITH TIME ZONE,
    
    is_mainline BOOLEAN NOT NULL DEFAULT FALSE,
    is_terminal BOOLEAN NOT NULL DEFAULT FALSE,
    siblings_count INTEGER NOT NULL DEFAULT 0,
    branch_depth INTEGER NOT NULL DEFAULT 0,
    path_from_root JSONB,
    turn_number INTEGER NOT NULL,
    generation_type TEXT NOT NULL,
    mainline_divergence_point UUID REFERENCES carta.nodes(id),
    replaced_node_id UUID REFERENCES carta.nodes(id),
    
    semantic_distance_from_parent FLOAT,
    avg_sibling_semantic_distance FLOAT,
    semantic_drift_since_root FLOAT,
    semantic_acceleration FLOAT,
    branch_entropy FLOAT,
    
    seconds_since_parent INTEGER,
    turn_density_ratio FLOAT,
    
    sibling_lineage_continuation_rate FLOAT,
    sibling_semantic_convergence_pattern TEXT,
    
    edit_chain_depth INTEGER,
    cognitive_load_signature FLOAT,
    node_spark_factor FLOAT,
    
    children_ids JSONB,
    additional_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Prompt-response pairs
CREATE TABLE carta.pairs (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES carta.conversations(id) ON DELETE CASCADE,
    prompt_id UUID NOT NULL REFERENCES carta.nodes(id) ON DELETE CASCADE,
    response_id UUID NOT NULL REFERENCES carta.nodes(id) ON DELETE CASCADE,
    
    is_mainline BOOLEAN NOT NULL DEFAULT FALSE,
    is_alternate BOOLEAN NOT NULL DEFAULT FALSE,
    is_terminal_arc BOOLEAN NOT NULL DEFAULT FALSE,
    branch_depth INTEGER NOT NULL DEFAULT 0,
    generation_type TEXT NOT NULL,
    divergence_point UUID REFERENCES carta.nodes(id),
    divergence_turn INTEGER,
    exchange_position_in_branch INTEGER,
    alternative_count INTEGER DEFAULT 0,
    branch_signature_pattern TEXT,
    path_from_root JSONB,
    
    embedding VECTOR(2000),
    embedding_model_version TEXT,
    embedding_generated_at TIMESTAMP WITH TIME ZONE,
    
    coherence_score FLOAT,
    semantic_drift FLOAT,
    semantic_drift_from_root FLOAT,
    abstraction_delta FLOAT,
    dialogic_continuity_score FLOAT,
    relative_entropy_to_siblings FLOAT,
    downstream_spark_factor FLOAT,
    
    turn_latency INTEGER,
    time_since_previous_pair INTEGER,
    
    additional_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(prompt_id, response_id)
);

-- Paths between nodes
CREATE TABLE carta.paths (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES carta.conversations(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES carta.nodes(id) ON DELETE CASCADE,
    ancestor_id UUID NOT NULL REFERENCES carta.nodes(id) ON DELETE CASCADE,
    distance INTEGER NOT NULL,
    path_nodes JSONB,
    is_mainline_path BOOLEAN NOT NULL DEFAULT FALSE,
    semantic_drift_along_path FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(node_id, ancestor_id)
);

-- Views for common analysis patterns
CREATE VIEW carta.high_drift_nodes AS
SELECT n.*
FROM carta.nodes n
WHERE n.semantic_drift_since_root > 0.5
  AND n.embedding IS NOT NULL;

CREATE VIEW carta.branch_sparks AS
SELECT n.*
FROM carta.nodes n
WHERE n.node_spark_factor > 0.7
  AND n.embedding IS NOT NULL;

CREATE VIEW carta.counterfactual_paths AS
SELECT n.*
FROM carta.nodes n
WHERE n.is_mainline = FALSE
  AND n.semantic_distance_from_parent > 0.4
  AND n.embedding IS NOT NULL;

CREATE VIEW carta.coherent_exchanges AS
SELECT p.*
FROM carta.pairs p
WHERE p.coherence_score > 0.8
  AND p.embedding IS NOT NULL;