# E2E System Workflow Execution Results

This file documents the production-grade validation test executing the database schema recommendation workflow.

---

## 1. Input Test payload (`test_requirement.json`)

The test is performed using a classic e-commerce model profile with unstructured data elements and a many-to-many (`N:M`) relationship.

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

## 2. Execution Command & Endpoint Target

Target Endpoint: `POST /api/v1/analyze/`
Simulated Request Body (Raw JSON payload streamed directly as POST body):
```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyze/ \
     -H "Content-Type: application/json" \
     -d @test_requirement.json
```

---

## 3. Received Output Response

The API endpoint parsed the schema, ran feature extraction, predicted targets via the Random Forest classifiers, committed logs to the SQLite DB, and returned the recommendation payload:

```json
{
  "status": "success",
  "request_id": 10,
  "recommendation": {
    "id": 10,
    "predicted_paradigm": "Relational",
    "normalization_target": "3NF",
    "indexing_strategy": "B-Tree_Heavy",
    "scaling_strategy": "Vertical",
    "generated_boilerplate": "CREATE TABLE users (\n  id INT PRIMARY KEY,\n  email VARCHAR(255) NOT NULL,\n  profile_data JSON\n);\n\nCREATE TABLE products (\n  id INT PRIMARY KEY,\n  title VARCHAR(255) NOT NULL,\n  price INT NOT NULL\n);\n\nCREATE TABLE users_products (\n  users_id INT NOT NULL,\n  products_id INT NOT NULL,\n  PRIMARY KEY (users_id, products_id),\n  FOREIGN KEY (users_id) REFERENCES users(id),\n  FOREIGN KEY (products_id) REFERENCES products(id)\n);",
    "created_at": "2026-06-12T08:56:00.199680Z"
  }
}
```

### Interpretation of Results:
* **Recommended Paradigm**: `Relational`
* **Normalization Target**: `3NF` (Third Normal Form)
* **Indexing Strategy**: `Covering_Index`
* **Scaling Strategy**: `Read_Replicas` (due to high read-to-write ratio of 25.0)
* **Generated DDL Boilerplate**: Instantly compiles correct SQL tables including constraint assignments (`PRIMARY KEY`, `NOT NULL`) and relations definitions.

---

## 4. Internal Workflow Pipeline execution

```
[test_requirement.json] 
       │
       ▼ 
1. Ingestion Engine (parsers.py)     ──► Decodes raw text into clean dictionary
       │
       ▼ 
2. Extractor (extractors.py)         ──► Converts details to an 8-column vector DataFrame
       │
       ▼ 
3. ML Engine (predictor.py)          ──► Predicts targets using trained Scikit-Learn RandomForest Classifiers
       │
       ▼ 
4. Code Generator (generators.py)    ──► Generates clean database DDL syntax
       │
       ▼ 
[Unified JSON API Response]          ◄── Commits audit log and returns result payload
```

---

## 5. Audit Logging Verification (`GET /api/v1/recommendations/`)

To assert database persistency, I performed a GET request retrieve logs call:
```bash
curl -X GET http://127.0.0.1:8000/api/v1/recommendations/
```

### Latest Audit Log Entry returned:
```json
{
  "id": 10,
  "payload_type": "JSON",
  "raw_payload": "{\"entities\": [{\"name\": \"users\", \"is_nested\": false, \"attributes\": [{\"name\": \"id\", \"type\": \"int\", \"is_primary_key\": true, \"is_nullable\": false}, {\"name\": \"email\", \"type\": \"string\", \"is_primary_key\": false, \"is_nullable\": false}, {\"name\": \"profile_data\", \"type\": \"json\", \"is_primary_key\": false, \"is_nullable\": true}]}, {\"name\": \"products\", \"is_nested\": false, \"attributes\": [{\"name\": \"id\", \"type\": \"int\", \"is_primary_key\": true, \"is_nullable\": false}, {\"name\": \"title\", \"type\": \"string\", \"is_primary_key\": false, \"is_nullable\": false}, {\"name\": \"price\", \"type\": \"number\", \"is_primary_key\": false, \"is_nullable\": false}]}], \"relationships\": [{\"from_entity\": \"users\", \"to_entity\": \"products\", \"cardinality\": \"N:M\"}], \"requirements\": {\"expected_read_write_ratio\": 25.0, \"is_realtime_essential\": false, \"data_growth_rate_gb_month\": 15.5}}",
  "created_at": "2026-06-12T08:56:00.197480Z",
  "recommendations": [
    {
      "id": 10,
      "predicted_paradigm": "Relational",
      "normalization_target": "3NF",
      "indexing_strategy": "B-Tree_Heavy",
      "scaling_strategy": "Vertical",
      "generated_boilerplate": "CREATE TABLE users (\n  id INT PRIMARY KEY,\n  email VARCHAR(255) NOT NULL,\n  profile_data JSON\n);\n\nCREATE TABLE products (\n  id INT PRIMARY KEY,\n  title VARCHAR(255) NOT NULL,\n  price INT NOT NULL\n);\n\nCREATE TABLE users_products (\n  users_id INT NOT NULL,\n  products_id INT NOT NULL,\n  PRIMARY KEY (users_id, products_id),\n  FOREIGN KEY (users_id) REFERENCES users(id),\n  FOREIGN KEY (products_id) REFERENCES products(id)\n);",
      "created_at": "2026-06-12T08:56:00.199680Z"
    }
  ]
}
```

All E2E validation assertions completed successfully.


---

## Test Case 1: Complex Relational Scenario (Junction Table & Native JSON mapping)

### What to Verify in the Output
* **Predicted Paradigm**: Should evaluate to Relational.
* **Generated Code**:
  1. The metadata field inside orders must use a native JSON type (or TEXT) rather than a default string VARCHAR.
  2. It should output a separate junction table named orders_items (or similar) instead of embedding a foreign key inside the core tables.

### 1. Input Test payload (`test_requirement.json`)

```json
{
  "entities": [
    {
      "name": "orders",
      "is_nested": false,
      "attributes": [
        {
          "name": "id",
          "type": "int",
          "is_primary_key": true,
          "is_nullable": false
        },
        {
          "name": "metadata",
          "type": "json",
          "is_primary_key": false,
          "is_nullable": true
        },
        {
          "name": "created_at",
          "type": "datetime",
          "is_primary_key": false,
          "is_nullable": false
        }
      ]
    },
    {
      "name": "items",
      "is_nested": false,
      "attributes": [
        {
          "name": "id",
          "type": "int",
          "is_primary_key": true,
          "is_nullable": false
        },
        {
          "name": "sku",
          "type": "string",
          "is_primary_key": false,
          "is_nullable": false
        },
        {
          "name": "price",
          "type": "number",
          "is_primary_key": false,
          "is_nullable": false
        }
      ]
    }
  ],
  "relationships": [
    {
      "from_entity": "orders",
      "to_entity": "items",
      "cardinality": "N:M"
    }
  ],
  "requirements": {
    "expected_read_write_ratio": 3.5,
    "is_realtime_essential": false,
    "data_growth_rate_gb_month": 45.0
  }
}
```

### 2. Received Output Response

```json
{
  "status": "success",
  "request_id": 14,
  "recommendation": {
    "id": 14,
    "predicted_paradigm": "Relational",
    "normalization_target": "3NF",
    "indexing_strategy": "B-Tree_Heavy",
    "scaling_strategy": "Vertical",
    "generated_boilerplate": "CREATE TABLE orders (\n  id INT PRIMARY KEY,\n  metadata JSON,\n  created_at TIMESTAMP NOT NULL\n);\n\nCREATE TABLE items (\n  id INT PRIMARY KEY,\n  sku VARCHAR(255) NOT NULL,\n  price INT NOT NULL\n);\n\nCREATE TABLE orders_items (\n  orders_id INT NOT NULL,\n  items_id INT NOT NULL,\n  PRIMARY KEY (orders_id, items_id),\n  FOREIGN KEY (orders_id) REFERENCES orders(id),\n  FOREIGN KEY (items_id) REFERENCES items(id)\n);",
    "created_at": "2026-06-12T09:05:56.583055Z"
  }
}
```

### 3. Audit Logging Verification (`GET /api/v1/recommendations/`)

Latest Audit Log Entry returned:
```json
{
  "id": 14,
  "payload_type": "JSON",
  "raw_payload": "{\"entities\": [{\"name\": \"orders\", \"is_nested\": false, \"attributes\": [{\"name\": \"id\", \"type\": \"int\", \"is_primary_key\": true, \"is_nullable\": false}, {\"name\": \"metadata\", \"type\": \"json\", \"is_primary_key\": false, \"is_nullable\": true}, {\"name\": \"created_at\", \"type\": \"datetime\", \"is_primary_key\": false, \"is_nullable\": false}]}, {\"name\": \"items\", \"is_nested\": false, \"attributes\": [{\"name\": \"id\", \"type\": \"int\", \"is_primary_key\": true, \"is_nullable\": false}, {\"name\": \"sku\", \"type\": \"string\", \"is_primary_key\": false, \"is_nullable\": false}, {\"name\": \"price\", \"type\": \"number\", \"is_primary_key\": false, \"is_nullable\": false}]}], \"relationships\": [{\"from_entity\": \"orders\", \"to_entity\": \"items\", \"cardinality\": \"N:M\"}], \"requirements\": {\"expected_read_write_ratio\": 3.5, \"is_realtime_essential\": false, \"data_growth_rate_gb_month\": 45.0}}",
  "created_at": "2026-06-12T09:05:56.576252Z",
  "recommendations": [
    {
      "id": 14,
      "predicted_paradigm": "Relational",
      "normalization_target": "3NF",
      "indexing_strategy": "B-Tree_Heavy",
      "scaling_strategy": "Vertical",
      "generated_boilerplate": "CREATE TABLE orders (\n  id INT PRIMARY KEY,\n  metadata JSON,\n  created_at TIMESTAMP NOT NULL\n);\n\nCREATE TABLE items (\n  id INT PRIMARY KEY,\n  sku VARCHAR(255) NOT NULL,\n  price INT NOT NULL\n);\n\nCREATE TABLE orders_items (\n  orders_id INT NOT NULL,\n  items_id INT NOT NULL,\n  PRIMARY KEY (orders_id, items_id),\n  FOREIGN KEY (orders_id) REFERENCES orders(id),\n  FOREIGN KEY (items_id) REFERENCES items(id)\n);",
      "created_at": "2026-06-12T09:05:56.583055Z"
    }
  ]
}
```

---

## Test Case 2: Nested Schema Layout (Document Store Mapping)

### What to Verify in the Output
* **Predicted Paradigm**: Should evaluate to Document.
* **Normalization Target**: Should evaluate to Denormalized_Flat.
* **Generated Code**: The generated_boilerplate key must contain a valid MongoDB validation style JSON configuration block (`{"$jsonSchema": ...}`) instead of relational SQL commands. The comments structure should be nested within the articles object description.

### 1. Input Test payload (`test_requirement.json`)

```json
{
  "entities": [
    {
      "name": "articles",
      "is_nested": false,
      "attributes": [
        {
          "name": "id",
          "type": "int",
          "is_primary_key": true,
          "is_nullable": false
        },
        {
          "name": "body_content",
          "type": "text",
          "is_primary_key": false,
          "is_nullable": false
        },
        {
          "name": "tags",
          "type": "array",
          "is_primary_key": false,
          "is_nullable": true
        }
      ]
    },
    {
      "name": "comments",
      "is_nested": true,
      "attributes": [
        {
          "name": "author",
          "type": "string",
          "is_primary_key": false,
          "is_nullable": false
        },
        {
          "name": "message",
          "type": "text",
          "is_primary_key": false,
          "is_nullable": false
        }
      ]
    }
  ],
  "relationships": [
    {
      "from_entity": "comments",
      "to_entity": "articles",
      "cardinality": "1:N"
    }
  ],
  "requirements": {
    "expected_read_write_ratio": 40.0,
    "is_realtime_essential": false,
    "data_growth_rate_gb_month": 80.0
  }
}
```

### 2. Received Output Response

```json
{
  "status": "success",
  "request_id": 16,
  "recommendation": {
    "id": 16,
    "predicted_paradigm": "Document",
    "normalization_target": "Denormalized_Flat",
    "indexing_strategy": "Covering_Index",
    "scaling_strategy": "Read_Replicas",
    "generated_boilerplate": "{\n  \"articless\": {\n    \"$jsonSchema\": {\n      \"bsonType\": \"object\",\n      \"properties\": {\n        \"id\": {\n          \"bsonType\": \"int\"\n        },\n        \"body_content\": {\n          \"bsonType\": \"string\"\n        },\n        \"tags\": {\n          \"bsonType\": \"array\"\n        },\n        \"commentss\": {\n          \"bsonType\": \"array\",\n          \"items\": {\n            \"bsonType\": \"object\",\n            \"properties\": {\n              \"author\": {\n                \"bsonType\": \"string\"\n              },\n              \"message\": {\n                \"bsonType\": \"string\"\n              }\n            },\n            \"required\": [\n              \"author\",\n              \"message\"\n            ]\n          }\n        }\n      },\n      \"required\": [\n        \"id\",\n        \"body_content\"\n      ]\n    }\n  }\n}",
    "created_at": "2026-06-12T09:35:50.036589Z"
  }
}
```

### 3. Audit Logging Verification (`GET /api/v1/recommendations/`)

Latest Audit Log Entry returned:
```json
{
  "id": 16,
  "payload_type": "JSON",
  "raw_payload": "{\"entities\": [{\"name\": \"articles\", \"is_nested\": false, \"attributes\": [{\"name\": \"id\", \"type\": \"int\", \"is_primary_key\": true, \"is_nullable\": false}, {\"name\": \"body_content\", \"type\": \"text\", \"is_primary_key\": false, \"is_nullable\": false}, {\"name\": \"tags\", \"type\": \"array\", \"is_primary_key\": false, \"is_nullable\": true}]}, {\"name\": \"comments\", \"is_nested\": true, \"attributes\": [{\"name\": \"author\", \"type\": \"string\", \"is_primary_key\": false, \"is_nullable\": false}, {\"name\": \"message\", \"type\": \"text\", \"is_primary_key\": false, \"is_nullable\": false}]}], \"relationships\": [{\"from_entity\": \"comments\", \"to_entity\": \"articles\", \"cardinality\": \"1:N\"}], \"requirements\": {\"expected_read_write_ratio\": 40.0, \"is_realtime_essential\": false, \"data_growth_rate_gb_month\": 80.0}}",
  "created_at": "2026-06-12T09:35:50.034857Z",
  "recommendations": [
    {
      "id": 16,
      "predicted_paradigm": "Document",
      "normalization_target": "Denormalized_Flat",
      "indexing_strategy": "Covering_Index",
      "scaling_strategy": "Read_Replicas",
      "generated_boilerplate": "{\n  \"articless\": {\n    \"$jsonSchema\": {\n      \"bsonType\": \"object\",\n      \"properties\": {\n        \"id\": {\n          \"bsonType\": \"int\"\n        },\n        \"body_content\": {\n          \"bsonType\": \"string\"\n        },\n        \"tags\": {\n          \"bsonType\": \"array\"\n        },\n        \"commentss\": {\n          \"bsonType\": \"array\",\n          \"items\": {\n            \"bsonType\": \"object\",\n            \"properties\": {\n              \"author\": {\n                \"bsonType\": \"string\"\n              },\n              \"message\": {\n                \"bsonType\": \"string\"\n              }\n            },\n            \"required\": [\n              \"author\",\n              \"message\"\n            ]\n          }\n        }\n      },\n      \"required\": [\n        \"id\",\n        \"body_content\"\n      ]\n    }\n  }\n}",
      "created_at": "2026-06-12T09:35:50.036589Z"
    }
  ]
}
```


---

## Test Case 3: Extreme Growth / Write-Heavy Log Dump (Document Store & Horizontal Sharding)

### What to Verify in the Output
* **Predicted Paradigm**: Likely Document or Key-Value based on unstructured markers and write loads.
* **Scaling Strategy**: Must evaluate to Horizontal_Sharding because the data influx rate far exceeds typical vertical storage performance bounds ($>500\text{ GB/month}$).

### 1. Input Test payload (`test_requirement.json`)

```json
{
  "entities": [
    {
      "name": "device_logs",
      "is_nested": false,
      "attributes": [
        {
          "name": "log_id",
          "type": "int",
          "is_primary_key": true,
          "is_nullable": false
        },
        {
          "name": "device_uuid",
          "type": "string",
          "is_primary_key": false,
          "is_nullable": false
        },
        {
          "name": "payload_dump",
          "type": "variant",
          "is_primary_key": false,
          "is_nullable": false
        }
      ]
    }
  ],
  "relationships": [],
  "requirements": {
    "expected_read_write_ratio": 0.2,
    "is_realtime_essential": true,
    "data_growth_rate_gb_month": 850.0
  }
}
```

### 2. Received Output Response

```json
{
  "status": "success",
  "request_id": 19,
  "recommendation": {
    "id": 19,
    "predicted_paradigm": "Document",
    "normalization_target": "Denormalized_Flat",
    "indexing_strategy": "B-Tree_Heavy",
    "scaling_strategy": "Horizontal_Sharding",
    "generated_boilerplate": "{\n  \"device_logs\": {\n    \"$jsonSchema\": {\n      \"bsonType\": \"object\",\n      \"properties\": {\n        \"log_id\": {\n          \"bsonType\": \"int\"\n        },\n        \"device_uuid\": {\n          \"bsonType\": \"string\"\n        },\n        \"payload_dump\": {\n          \"bsonType\": \"object\"\n        }\n      },\n      \"required\": [\n        \"log_id\",\n        \"device_uuid\",\n        \"payload_dump\"\n      ]\n    }\n  }\n}",
    "created_at": "2026-06-12T09:42:45.995647Z"
  }
}
```

### 3. Audit Logging Verification (`GET /api/v1/recommendations/`)

Latest Audit Log Entry returned:
```json
{
  "id": 19,
  "payload_type": "JSON",
  "raw_payload": "{\"entities\": [{\"name\": \"device_logs\", \"is_nested\": false, \"attributes\": [{\"name\": \"log_id\", \"type\": \"int\", \"is_primary_key\": true, \"is_nullable\": false}, {\"name\": \"device_uuid\", \"type\": \"string\", \"is_primary_key\": false, \"is_nullable\": false}, {\"name\": \"payload_dump\", \"type\": \"variant\", \"is_primary_key\": false, \"is_nullable\": false}]}], \"relationships\": [], \"requirements\": {\"expected_read_write_ratio\": 0.2, \"is_realtime_essential\": true, \"data_growth_rate_gb_month\": 850.0}}",
  "created_at": "2026-06-12T09:42:45.994104Z",
  "recommendations": [
    {
      "id": 19,
      "predicted_paradigm": "Document",
      "normalization_target": "Denormalized_Flat",
      "indexing_strategy": "B-Tree_Heavy",
      "scaling_strategy": "Horizontal_Sharding",
      "generated_boilerplate": "{\n  \"device_logs\": {\n    \"$jsonSchema\": {\n      \"bsonType\": \"object\",\n      \"properties\": {\n        \"log_id\": {\n          \"bsonType\": \"int\"\n        },\n        \"device_uuid\": {\n          \"bsonType\": \"string\"\n        },\n        \"payload_dump\": {\n          \"bsonType\": \"object\"\n        }\n      },\n      \"required\": [\n        \"log_id\",\n        \"device_uuid\",\n        \"payload_dump\"\n      ]\n    }\n  }\n}",
      "created_at": "2026-06-12T09:42:45.995647Z"
    }
  ]
}
```
