# **scHilda Knowledge Graph Reconstruction Guide**

### **1\. Introduction**

The 'KG/' directory contains the complete dataset for the scHilda knowledge graph. This guide provides instructions to fully reconstruct the scHilda knowledge graph within a Neo4j Aura cloud database instance.

### **2\. Database Setup and Node Importation**

To begin, provision a new instance on [Neo4j Aura](https://www.google.com/search?q=https://neo4j.com/cloud/aura-db/).

Within the new instance, first execute the following commands to establish essential uniqueness constraints. This step is critical for data integrity and optimal import performance.

'''bash
CREATE CONSTRAINT unique\_gene\_symbol IF NOT EXISTS FOR (g:Gene) REQUIRE g.gene\_symbol IS UNIQUE;  
CREATE CONSTRAINT unique\_celltype\_id IF NOT EXISTS FOR (c:CellType) REQUIRE c.ontology\_id IS UNIQUE;  
CREATE CONSTRAINT unique\_pathway\_id IF NOT EXISTS FOR (p:Pathway) REQUIRE p.id IS UNIQUE;
'''
Once the constraints are successfully created, proceed by executing the following commands sequentially to import all node entities.

'''bash
USING PERIODIC COMMIT 1000
LOAD CSV WITH HEADERS FROM 'https://raw.githubusercontent.com/liangglhf/scHilda/main/KG/Node.csv' AS row
CALL {
  WITH row
  CASE row.label
    WHEN 'CellType' THEN
      MERGE (c:CellType {ontology_id: row.id})
        ON CREATE SET c.name = row.name
    WHEN 'Gene' THEN
      MERGE (g:Gene {gene_symbol: row.id})
    WHEN 'Pathway' THEN
      MERGE (p:Pathway {id: row.id})
        ON CREATE SET p.name = row.name
  END
}
'''

### **3\. Importing IS\_A Relationships**

LOAD CSV WITH HEADERS FROM '\[https://raw.githubusercontent.com/liangglhf/scHilda/main/KG/IS\_A.csv\](https://raw.githubusercontent.com/liangglhf/scHilda/main/KG/IS\_A.csv)' AS row  
MATCH (c1:CellType {ontology\_id: row.\`n.ontology\_id\`})  
MATCH (c2:CellType {ontology\_id: row.\`m.ontology\_id\`})  
MERGE (c1)-\[r:IS\_A\]-\>(c2);

### **4\. Importing HAS\_ACTIVITY\_IN Relationships**

This relationship is distributed across five files. Execute the following command for each file (from HAS\_ACTIVITY\_IN\_1.csv to HAS\_ACTIVITY\_IN\_5.csv), modifying the filename accordingly.

USING PERIODIC COMMIT 1000  
LOAD CSV WITH HEADERS FROM '\[https://raw.githubusercontent.com/liangglhf/scHilda/main/KG/HAS\_ACTIVITY\_IN\_1.csv\](https://raw.githubusercontent.com/liangglhf/scHilda/main/KG/HAS\_ACTIVITY\_IN\_1.csv)' AS row  
MATCH (p:Pathway {id: row.\`n.id\`})  
MATCH (c:CellType {ontology\_id: row.\`m.ontology\_id\`})  
MERGE (p)-\[r:HAS\_ACTIVITY\_IN\]-\>(c);

### **5\. Importing COEXPRESSED\_IN Relationships**

This relationship is distributed across six files. Execute the following command for each file (from COEXPRESSED\_IN\_1.csv to COEXPRESSED\_IN\_6.csv), modifying the filename accordingly.

USING PERIODIC COMMIT 1000  
LOAD CSV WITH HEADERS FROM '\[https://raw.githubusercontent.com/liangglhf/scHilda/main/KG/COEXPRESSED\_IN\_1.csv\](https://raw.githubusercontent.com/liangglhf/scHilda/main/KG/COEXPRESSED\_IN\_1.csv)' AS row  
MATCH (g1:Gene {gene\_symbol: row.\`n.gene\_symbol\`})  
MATCH (g2:Gene {gene\_symbol: row.\`m.gene\_symbol\`})  
MERGE (g1)-\[r:COEXPRESSED\_IN\]-\>(g2)  
  ON CREATE SET r.weight \= toFloat(row.\`r.weight\`), r.cell\_type \= row.\`r.cell\_type\`;

### **6\. Importing PARTICIPATES\_IN Relationships**

This relationship is distributed across multiple files. Execute the following command for each PARTICIPATES\_IN batch file, modifying the filename accordingly.

USING PERIODIC COMMIT 1000  
LOAD CSV WITH HEADERS FROM '\[https://raw.githubusercontent.com/liangglhf/scHilda/main/KG/PARTICIPATES\_IN\_1.csv\](https://raw.githubusercontent.com/liangglhf/scHilda/main/KG/PARTICIPATES\_IN\_1.csv)' AS row  
MATCH (g:Gene {gene\_symbol: row.\`n.gene\_symbol\`})  
MATCH (p:Pathway {id: row.\`m.id\`})  
MERGE (g)-\[r:PARTICIPATES\_IN\]-\>(p);

### **7\. Validation (Optional)**

The following queries can be executed to validate that all data has been imported completely.

MATCH (n) RETURN labels(n) AS NodeType, count(\*) AS Count;  
MATCH ()-\[r\]-\>() RETURN type(r) AS RelationshipType, count(\*) AS Count;

### **8\. Incorporating New Datasets**

To incorporate new datasets into the knowledge graph, new COEXPRESSED\_IN and HAS\_ACTIVITY\_IN relationships must be computed and imported, following the 'Methods' described in the paper.
