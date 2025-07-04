# CARTA – Conversation Archive for Recursive Thought Analysis

## Overview

CARTA is a semantic analysis system that parses and reconstructs ChatGPT conversation trees, including all branches and alternative paths. It computes over 50 semantic and structural metrics per node and node pair using high-dimensional vector analysis. The system is a PostgreSQL database with pgvector extension for efficient storage and querying of conversation data with vector similarity operations.

## Key Features

### Conversation Structure Analysis
- Preserves complete tree structure from ChatGPT exports
- Maintains parent-child relationships and branching points
- Tracks mainline progression versus exploratory branches
- Identifies conversation termination points
- Maps full conversation topology

### Semantic Vector Processing
- Generates 2000-dimensional embeddings via OpenAI's text-embedding-3-large
- Calculates semantic distances between nodes
- Measures conceptual drift along conversation paths
- Identifies high-divergence areas

### Database Integration
- Provides PostgreSQL storage with pgvector extension
- Enables efficient vector similarity operations
- Supports cross-conversation pattern detection
- Executes combined structural and semantic queries

### Analytical Framework
- Tracks semantic drift along conversation paths
- Analyzes divergence via branch entropy computation
- Scores coherence between prompt-response pairs
- Assesses generative potential (node "spark factor")
- Measures abstraction deltas between turns
- Scores dialogic continuity across exchanges
- Analyzes cognitive load signatures

## Technical Architecture

### Processing Pipeline
1. **Parser**: Extracts conversation trees from JSON exports
2. **Embedder**: Generates vector embeddings and semantic metrics
3. **Database**: Stores structured data with query optimization

### Database Schema
- `conversations`: Stores conversation metadata and state
- `nodes`: Stores individual messages with embeddings and 35+ semantic metrics
- `pairs`: Stores prompt-response relationships with 20+ metrics derived from semantic geometry
- `paths`: Stores conversation ancestry data with semantic drift tracking
- Provides 17 specialized SQL functions for vector search and tree traversal

### Vector Operations
- Utilizes HNSW indexing for performance optimization
- Supports cosine, Euclidean, and inner product distance metrics
- Configures similarity thresholds for query precision

## Query Capabilities

### Structural Queries
- Retrieves complete conversation branches
- Finds alternate paths and terminated branches
- Analyzes depth and branching patterns

### Semantic Search
- Executes similarity search across nodes and pairs
- Performs cross-conversation pattern detection
- Enables semantic clustering

### Combined Analysis
- Identifies nodes with high semantic divergence
- Analyzes paths with specific characteristics
- Executes multi-conversation pattern analysis

## Installation

### Requirements
- Python 3.8+
- PostgreSQL with pgvector (optional, for database storage)
- OpenAI API key

### Setup
```bash
git clone https://github.com/someobserver/carta.git
cd carta
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration
```bash
cp env.example .env
# Required: OPENAI_API_KEY=your-key
```

### Database Setup (Optional)
```bash
# Apply 11 production migrations (schema + indexes + functions + access control)
for i in {001..011}; do
  psql -d your_database -f src/carta/db/migrations/${i}_*.sql
done
```

## Quick Start

```python
from src.carta.pipeline import Pipeline

# Process a ChatGPT export (file-only mode)
pipeline = Pipeline(store_to_database=False)
conversation_ids = pipeline.process_file("chatgpt_export.json", save_intermediates=True)

# View results
print(f"Processed {len(conversation_ids)} conversations")
# Check output files: *_parsed.json, *_embedded.json
```

## Usage

### Basic Processing
```python
from carta.pipeline import Pipeline

# Process with database storage
pipeline = Pipeline(store_to_database=True)
conversation_ids = pipeline.process_file("chatgpt_export.json")
```

### Database Queries
```python
from carta.db import query_functions

# Semantic similarity search
similar_nodes = query_functions.find_similar_nodes(
    query_embedding=target_vector,
    similarity_threshold=0.7
)

# Retrieve complete conversation branch
branch_data = query_functions.get_complete_branch(
    divergence_point_id=node_id
)
```

### Analysis Functions
```python
# Cross-conversation pattern detection
patterns = query_functions.find_recurring_patterns(
    min_similarity=0.8,
    min_occurrences=3
)

# Semantic drift analysis
drift_analysis = query_functions.calculate_semantic_drift(
    conversation_id=conv_id
)

# Find high-potential generative nodes
sparks = query_functions.find_semantic_sparks(
    conversation_id=conv_id,
    min_spark_factor=0.7
)

# Branch traversal and alternate path analysis
branch = query_functions.get_complete_branch(divergence_point_id=node_id)
paths = query_functions.find_alternate_paths(node_id=node_id, max_depth=3)
```

