# CARTA – Conversation Archive for Recursive Thought Analysis

## Overview

CARTA extracts complete conversation trees, including all branches and alternate paths. It calculates 50+ derived metrics per node/pair and provides tools for semantic analysis through high-dimensional vector embeddings. The system stores structured conversation data in PostgreSQL with pgvector support, enabling advanced search and analysis capabilities.

## Key Features

### Conversation Structure Analysis
- Preserves complete tree structure from ChatGPT exports
- Maintains parent-child relationships and branching points
- Tracks mainline progression versus exploratory branches
- Identifies conversation termination points
- Maps full conversation topology

### Semantic Vector Processing
- Generates 2000-dim embeddings via OpenAI's text-embedding-3-large
- Calculates semantic distances between nodes
- Measures conceptual drift along conversation paths
- Identifies high-divergence areas

### Database Integration
- PostgreSQL storage with pgvector extension
- Efficient vector similarity operations
- Cross-conversation pattern detection
- Combined structural and semantic queries

### Analytical Framework
- Semantic drift tracking along conversation paths
- Divergence analysis via branch entropy computation
- Coherence scoring between prompt-response pairs
- Generative potential assessment (node "spark factor")
- Abstraction delta measurements between turns
- Dialogic continuity scoring across exchanges
- Cognitive load signature analysis

## Technical Architecture

### Processing Pipeline
1. **Parser**: Extracts conversation trees from JSON exports
2. **Embedder**: Generates vector embeddings and semantic metrics
3. **Database**: Stores structured data with query optimization

### Database Schema
- `conversations`: Conversation metadata and state
- `nodes`: Individual messages with embeddings and 35+ semantic metrics
- `pairs`: Prompt-response relationships with 20+ metrics derived from semantic geometry
- `paths`: Conversation ancestry data with semantic drift tracking
- 17 specialized SQL functions for vector search and tree traversal

### Vector Operations
- HNSW indexing for performance
- Supports cosine, Euclidean, and inner product metrics
- Configurable similarity thresholds

## Query Capabilities

### Structural Queries
- Retrieve complete conversation branches
- Find alternate paths & terminated branches
- Analyze depth and branching patterns

### Semantic Search
- Similarity search across nodes and pairs
- Cross-conversation pattern detection
- Semantic clustering

### Combined Analysis
- Nodes with high semantic divergence
- Paths with specific characteristics
- Multi-conversation pattern analysis

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

## Documentation

Forthcoming.

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

# Retrieve a complete conversation branch
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

