# E2E Workflow Results

This file documents the input schema payload, execution commands, SQLite audit logs, and machine learning inference results for the database schema recommendation engine.

---

## 1. Input Payload (`test_requirement.json`)

```json
{
  "entities": [
    {
      "name": "users",
      "is_nested": false,
      "attributes": [
        {"name": "id", "type": "int", "is_primary_key": true, "is_nullable": false},
        {"name": "email", "type": "string", "is_primary_key": false, "is_nullable": false},
        {"name": "profile_data", "type": "json", "is_primary_key": false, "is_nullable": true}
      ]
    },
    {
      "name": "products",
      "is_nested": false,
      "attributes": [
        {"name": "id", "type": "int", "is_primary_key": true, "is_nullable": false},
        {"name": "title", "type": "string", "is_primary_key": false, "is_nullable": false},
        {"name": "price", "type": "number", "is_primary_key": false, "is_nullable": false}
      ]
    }
  ],
  "relationships": [
    {
      "from_entity": "users",
      "to_entity": "products",
      "cardinality": "N:M"
    }
  ],
  "requirements": {
    "expected_read_write_ratio": 25.0,
    "is_realtime_essential": false,
    "data_growth_rate_gb_month": 15.5
  }
}
```

---

## 2. Execution Commands

### Step A: Start the active Django server
```bash
python manage.py runserver
```

### Step B: Stream payload directly to the analysis API routing path
```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyze/ \
     -H "Content-Type: application/json" \
     -d @test_requirement.json
```

### Step C: Fetch the audit log list to verify log history persistence
```bash
curl -X GET http://127.0.0.1:8000/api/v1/recommendations/
```

---

## 3. SQLite Database Output

Calling `GET /api/v1/recommendations/` returns the logged audit record committed to our local `db.sqlite3` framework:

```json
{
  "id": 8,
  "payload_type": "JSON",
  "raw_payload": "{\"entities\": [{\"name\": \"users\", \"is_nested\": false, \"attributes\": [{\"name\": \"id\", \"type\": \"int\", \"is_primary_key\": true, \"is_nullable\": false}, {\"name\": \"email\", \"type\": \"string\", \"is_primary_key\": false, \"is_nullable\": false}, {\"name\": \"profile_data\", \"type\": \"json\", \"is_primary_key\": false, \"is_nullable\": true}]}, {\"name\": \"products\", \"is_nested\": false, \"attributes\": [{\"name\": \"id\", \"type\": \"int\", \"is_primary_key\": true, \"is_nullable\": false}, {\"name\": \"title\", \"type\": \"string\", \"is_primary_key\": false, \"is_nullable\": false}, {\"name\": \"price\", \"type\": \"number\", \"is_primary_key\": false, \"is_nullable\": false}]}], \"relationships\": [{\"from_entity\": \"users\", \"to_entity\": \"products\", \"cardinality\": \"N:M\"}], \"requirements\": {\"expected_read_write_ratio\": 25.0, \"is_realtime_essential\": false, \"data_growth_rate_gb_month\": 15.5}}",
  "created_at": "2026-06-12T08:14:16.355114Z",
  "recommendations": [
    {
      "id": 8,
      "predicted_paradigm": "Relational",
      "normalization_target": "3NF",
      "indexing_strategy": "B-Tree_Heavy",
      "scaling_strategy": "Vertical",
      "generated_boilerplate": "CREATE TABLE users (\n  id INT PRIMARY KEY,\n  email VARCHAR(255) NOT NULL,\n  profile_data VARCHAR(255)\n);\n\nCREATE TABLE products (\n  id INT PRIMARY KEY,\n  title VARCHAR(255) NOT NULL,\n  price INT NOT NULL,\n  users_id INT,\n  FOREIGN KEY (users_id) REFERENCES users(id)\n);",
      "created_at": "2026-06-12T08:14:16.356647Z"
    }
  ]
}
```

---

## 4. Machine Learning Inference

### Predicted Schema Recommedations:
* **recommended_db_paradigm**: `Relational`
* **normalization_target**: `3NF`
* **indexing_strategy**: `B-Tree_Heavy`
* **scaling_strategy**: `Vertical`

### Inference Interpretation:
1. **Paradigm (Relational)**: 
   * The schema defines two flat entities (`users` and `products`) with a complex join relationship mapping (`N:M`). It is highly structured and does not use nested entities, leading the Random Forest model to recommend a classic Relational DBMS.
2. **Normalization Target (3NF)**:
   * Relational structures automatically recommend 3NF alignment to eliminate redundancy and maintain integrity across the cross-referencing tables.
3. **Indexing Strategy (B-Tree_Heavy)**:
   * Since there is no extreme read-heavy ratio or complex nested JSON property filtering required, the system recommends standard `B-Tree` indexing on the primary keys.
4. **Scaling Strategy (Vertical)**:
   * The simulated data growth rate is 15.5 GB/month (moderate volume) and the read-write ratio is 25.0 (which is read-skewed but not high enough to warrant distributed sharding immediately). The model recommends vertical scaling (resource upgrades) as the most efficient, cost-effective initial step.
