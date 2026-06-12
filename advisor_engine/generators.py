import json
from typing import Dict, Any, List, Tuple

class BoilerplateGenerator:
    def __init__(self, parsed_data: Dict[str, Any], predicted_paradigm: str):
        """
        I set up my boilerplate generator here, storing the parsed schema data
        and the database paradigm that my model predicted.
        """
        self.parsed_data = parsed_data
        self.predicted_paradigm = predicted_paradigm

    def generate(self) -> str:
        """
        I route the generation process here depending on what database paradigm we predicted.
        """
        paradigm = self.predicted_paradigm.lower().strip()
        if "relational" in paradigm or "graph" in paradigm:
            return self._generate_sql()
        else:
            return self._generate_nosql()

    def _generate_sql(self) -> str:
        """
        This is where I build my SQL DDL. I'll construct the CREATE TABLE statements here.
        """
        entities = self.parsed_data.get("entities", [])
        relationships = self.parsed_data.get("relationships", [])
        
        # Build a map of foreign keys so I know where they go
        fkeys_by_table: Dict[str, List[Dict[str, str]]] = {}
        for rel in relationships:
            from_ent = rel.get("from_entity", "")
            to_ent = rel.get("to_entity", "")
            cardinality = rel.get("cardinality", "1:1")
            
            # For 1:N relations, the child holds the foreign key reference
            if cardinality in ("1:N", "ONE:MANY"):
                child_table = to_ent
                parent_table = from_ent
            else:
                # Fallback default mapping
                child_table = to_ent
                parent_table = from_ent
                
            if child_table and parent_table:
                if child_table not in fkeys_by_table:
                    fkeys_by_table[child_table] = []
                fkeys_by_table[child_table].append({
                    "column_name": f"{parent_table.lower()}_id",
                    "parent_table": parent_table
                })

        sql_statements: List[str] = []
        for entity in entities:
            name = entity.get("name", "")
            attributes = entity.get("attributes", [])
            
            table_lines: List[str] = []
            
            # Iterate and append column definitions
            for attr in attributes:
                attr_name = attr.get("name", "")
                data_type = str(attr.get("data_type", "")).lower().strip()
                is_pk = attr.get("is_primary_key", False)
                is_null = attr.get("is_nullable", True)
                
                # Map datatype names to their SQL equivalents
                if any(t in data_type for t in ("string", "varchar", "text")):
                    sql_type = "VARCHAR(255)"
                elif any(t in data_type for t in ("integer", "int", "number")):
                    sql_type = "INT"
                elif any(t in data_type for t in ("datetime", "timestamp", "date")):
                    sql_type = "TIMESTAMP"
                else:
                    sql_type = "VARCHAR(255)"
                    
                line = f"  {attr_name} {sql_type}"
                if is_pk:
                    line += " PRIMARY KEY"
                elif not is_null:
                    line += " NOT NULL"
                    
                table_lines.append(line)
                
            # Inject references for any foreign keys
            fkeys = fkeys_by_table.get(name, [])
            for fk in fkeys:
                fk_col = fk["column_name"]
                parent_t = fk["parent_table"]
                
                # Create the foreign key column if I didn't find it in the attributes list
                if not any(attr.get("name", "").lower() == fk_col.lower() for attr in attributes):
                    table_lines.append(f"  {fk_col} INT")
                
                table_lines.append(f"  FOREIGN KEY ({fk_col}) REFERENCES {parent_t}(id)")
                
            table_body = ",\n".join(table_lines)
            create_stmt = f"CREATE TABLE {name} (\n{table_body}\n);"
            sql_statements.append(create_stmt)
            
        return "\n\n".join(sql_statements)

    def _generate_nosql(self) -> str:
        """
        This is where I build my MongoDB $jsonSchema validation block.
        """
        entities = self.parsed_data.get("entities", [])
        relationships = self.parsed_data.get("relationships", [])
        
        nested_names = {e.get("name", "") for e in entities if e.get("is_nested", False)}
        
        # Set up relational mappings so I can embed the children properly
        nested_entities_by_parent: Dict[str, List[Dict[str, Any]]] = {}
        for rel in relationships:
            from_ent = rel.get("from_entity", "")
            to_ent = rel.get("to_entity", "")
            cardinality = rel.get("cardinality", "1:1")
            
            if to_ent in nested_names:
                if from_ent not in nested_entities_by_parent:
                    nested_entities_by_parent[from_ent] = []
                nested_entities_by_parent[from_ent].append({
                    "entity_name": to_ent,
                    "cardinality": cardinality
                })

        # I wrote this recursive helper to build my nested schema properties
        def build_properties(entity_name: str) -> Tuple[Dict[str, Any], List[str]]:
            entity = next((e for e in entities if e.get("name", "") == entity_name), None)
            if not entity:
                return {}, []
                
            properties: Dict[str, Any] = {}
            required: List[str] = []
            
            attributes = entity.get("attributes", [])
            for attr in attributes:
                attr_name = attr.get("name", "")
                data_type = str(attr.get("data_type", "")).lower().strip()
                is_null = attr.get("is_nullable", True)
                
                # Map my attribute data types to MongoDB BSON types
                if any(t in data_type for t in ("string", "varchar", "text")):
                    bson_type = "string"
                elif any(t in data_type for t in ("integer", "int", "number")):
                    bson_type = "int"
                elif any(t in data_type for t in ("datetime", "timestamp", "date")):
                    bson_type = "date"
                elif any(t in data_type for t in ("bool", "boolean")):
                    bson_type = "bool"
                else:
                    bson_type = "string"
                    
                properties[attr_name] = {"bsonType": bson_type}
                if not is_null:
                    required.append(attr_name)
                    
            # Embed my nested entities as sub-objects or arrays
            children = nested_entities_by_parent.get(entity_name, [])
            for child in children:
                child_name = child["entity_name"]
                card = child["cardinality"]
                
                child_props, child_req = build_properties(child_name)
                child_schema: Dict[str, Any] = {
                    "bsonType": "object",
                    "properties": child_props
                }
                if child_req:
                    child_schema["required"] = child_req
                    
                field_name = child_name.lower()
                if card in ("1:N", "ONE:MANY"):
                    field_name = f"{field_name}s"
                    properties[field_name] = {
                        "bsonType": "array",
                        "items": child_schema
                    }
                else:
                    properties[field_name] = child_schema
                    
            return properties, required

        root_schemas: Dict[str, Any] = {}
        for entity in entities:
            ent_name = entity.get("name", "")
            # I only generate root schemas for top-level entities
            if not entity.get("is_nested", False):
                properties, required = build_properties(ent_name)
                
                schema = {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "properties": properties
                    }
                }
                if required:
                    schema["$jsonSchema"]["required"] = required
                    
                root_schemas[ent_name.lower() + "s"] = schema
                
        return json.dumps(root_schemas, indent=2)
