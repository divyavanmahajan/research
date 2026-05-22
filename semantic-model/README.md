# Semantic Model for Unity Catalog

A layered representation of Databricks Unity Catalog table schemas, optimized for LLM-powered SQL generation.

## Structure

```
semantic-model/
├── extract/                    # Tools to extract and build the model
│   ├── config.yaml             # Configure catalogs, schemas, and options
│   ├── extract_catalog.py      # Pull metadata from Unity Catalog via SDK
│   ├── infer_relationships.py  # Detect FK relationships from naming conventions
│   ├── enrich_descriptions.py  # Optional: use Claude to fill missing descriptions
│   ├── build_model.py          # Generate all model files from raw JSON
│   ├── run_all.sh              # Run the full pipeline in one command
│   └── requirements.txt
└── model/                      # Generated semantic model (commit this)
    ├── catalog_index.yaml      # Compact index — always inject into LLM context
    ├── relationships.md        # Full join graph
    ├── glossary.md             # Business term → physical mapping (edit manually)
    └── tables/
        └── {schema}/
            └── {table}.md      # Per-table detail with columns, joins, examples
```

## Quick Start

```bash
cd semantic-model/extract
pip install -r requirements.txt

# Configure your Databricks connection
export DATABRICKS_HOST=https://your-workspace.azuredatabricks.net
export DATABRICKS_TOKEN=dapi...

# Edit config.yaml to set your target catalogs/schemas
# Then run the full pipeline:
./run_all.sh
```

## How to Use the Model for SQL Generation

### Strategy: Two-layer injection

**Always inject** `model/catalog_index.yaml` into every prompt. It's ~3-8KB and gives the LLM a complete map of all tables and their relationships.

**Load on demand** the relevant `model/tables/{schema}/{table}.md` files for the tables the LLM identifies as relevant from the index.

### Example system prompt

```
You are a SQL expert for Databricks. Generate Spark SQL queries only.

## Catalog Overview
<contents of model/catalog_index.yaml>

## Business Glossary
<contents of model/glossary.md>

When you need column-level detail for a specific table, I will provide the
relevant table file from model/tables/{schema}/{table}.md.
```

### RAG Strategy

For RAG-based retrieval:
- Index each `tables/{schema}/{table}.md` as a separate chunk
- Use `catalog_index.yaml` as the routing layer: embed table names + descriptions to find relevant tables
- Retrieve the matching `.md` files and inject them alongside the index

## Updating the Model

Re-run the pipeline whenever your schema changes:

```bash
./run_all.sh
```

The `glossary.md` file is **not overwritten** — it's maintained manually to preserve your business term definitions.

## Configuration Options

See `extract/config.yaml` for all options including:
- **Multi-catalog extraction**: target multiple catalogs in one run
- **Relationship inference tuning**: adjust FK suffix patterns
- **Description enrichment**: use Claude to generate missing column descriptions
- **Sampling**: extract distinct values for low-cardinality enum columns

## Design Decisions

### Why not a graph database?
KuzuDB or Neo4j would give richer traversal, but LLMs can't query them directly — you'd need a translation layer anyway. Markdown files with explicit join examples are more direct and require zero infrastructure.

### Why two layers (index + detail files)?
For 50–300 tables, you can't fit all column-level detail into one context window. The compact YAML index (~3-8KB) fits easily and tells the LLM which tables are relevant. The per-table `.md` files (~500–1500 tokens each) are loaded selectively.

### Why infer relationships from naming conventions?
Unity Catalog doesn't enforce FK constraints. Most Databricks schemas use consistent naming (e.g., `customer_id` always references `customers.customer_id`). The inference covers ~80-90% of real relationships; the glossary and table comments cover the rest.
