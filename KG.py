import sys
from neo4j import GraphDatabase

class KnowledgeGraphHandler:
    def __init__(self, uri, username, password):
        try:
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            self.driver.verify_connectivity()
        except Exception as e:
            sys.exit(f"connection error: {e}")

    def close(self):
        if self.driver:
            self.driver.close()

    def get_qualitative_evidence_summary(self, cell_ontology_id, marker_genes):
        if not cell_ontology_id or not marker_genes:
            return "No cell ontology ID or marker genes provided."
        try:
            with self.driver.session() as session:
                has_parent = session.execute_read(self._check_parent_ontology, cell_ontology_id)
                pathways_count = session.execute_read(self._get_functional_pathways_count, cell_ontology_id, marker_genes)
                coexpression_count = session.execute_read(self._get_coexpression_network_count, cell_ontology_id, marker_genes)

            summary_parts = [
                f"- Ontology: This cell type {'has' if has_parent else 'does not have'} a parent in the cell ontology, suggesting it is a {'well-defined' if has_parent else 'root or isolated'} term.",
                f"- Functional Pathways: The markers are associated with {pathways_count} known functional pathways active in this cell type.",
                f"- Co-expression Network: Found {coexpression_count} co-expression links among the provided markers within this cell type's context."
            ]
            return "\n".join(summary_parts)
        except Exception as e:
            print(f"warning: {cell_ontology_id} error: {e}")
            return "Error querying the knowledge graph for qualitative evidence."

    def get_focused_subtype_evidence(self, major_type_id, genes):
        if not major_type_id or not genes:
            return "No major type ID or genes provided for focused subtype query."
        
        cypher_query = """
        MATCH (major_type:CellType {ontology_id: $major_type_id})
        MATCH (subtype:CellType)-[:IS_A*1..]->(major_type)
        WHERE subtype.name IS NOT NULL
        WITH subtype
        // particapate
        OPTIONAL MATCH (g2:Gene)-[:PARTICIPATES_IN]->(p:Pathway)-[:HAS_ACTIVITY_IN]->(subtype)
        WHERE g2.gene_symbol IN $genes

        WITH subtype, 
             collect(DISTINCT {pathway: p.name, gene: g2.gene_symbol, relation: 'HAS_ACTIVITY_IN'}) AS pathways

        WHERE size(pathways) > 0
        RETURN subtype.name AS subtype_name,
               subtype.ontology_id AS subtype_id,
               // marker_list 
               [] AS marker_list, 
               [p in pathways WHERE p.pathway IS NOT NULL | p.pathway + ' (via ' + p.gene + ')'] AS pathway_list
        LIMIT 20
        """
        try:
            with self.driver.session() as session:
                result = session.run(cypher_query, major_type_id=major_type_id, genes=genes)
                evidence_strings = []
                for record in result:
                    name = record['subtype_name']
                    evidence_parts = []
                    #  marker_listst always null, set false
                    if record['marker_list']:
                        evidence_parts.append(f"is directly marked by {', '.join(record['marker_list'])}")
                    if record['pathway_list']:
                        evidence_parts.append(f"has active pathways such as {', '.join(record['pathway_list'])}")
                    
                    if evidence_parts:
                        evidence_strings.append(f"- Subtype '{name}': {' and '.join(evidence_parts)}.")

                return "\n".join(evidence_strings) if evidence_strings else "No specific subtype information found for the given markers under the confirmed major type based on pathway analysis."
        except Exception as e:
            print(f"error: {e}")
            return "Error querying the knowledge graph for subtype evidence."

    @staticmethod
    def _get_curated_markers_count(tx, cl_id, genes):
        query = "MATCH (ct:CellType {ontology_id: $cl_id})<-[:IS_MARKER_FOR]-(g:Gene) WHERE g.gene_symbol IN $genes RETURN count(g)"
        return tx.run(query, cl_id=cl_id, genes=genes).single()[0]

    @staticmethod
    def _check_parent_ontology(tx, cl_id):
        query = "MATCH (:CellType {ontology_id: $cl_id})-[:IS_A]->() RETURN count(*) > 0"
        return tx.run(query, cl_id=cl_id).single()[0]

    @staticmethod
    def _get_functional_pathways_count(tx, cl_id, genes):
        query = "MATCH (g:Gene)-[:PARTICIPATES_IN]->(p:Pathway)-[:HAS_ACTIVITY_IN]->(:CellType {ontology_id: $cl_id}) WHERE g.gene_symbol IN $genes RETURN count(DISTINCT p)"
        return tx.run(query, cl_id=cl_id, genes=genes).single()[0]

    @staticmethod
    def _get_coexpression_network_count(tx, cl_id, genes):
        query = "UNWIND $genes as gene1 UNWIND $genes as gene2 WITH gene1, gene2 WHERE gene1 < gene2 MATCH (g1:Gene {gene_symbol: gene1})-[r:COEXPRESSED_IN]-(g2:Gene {gene_symbol: gene2}) WHERE r.cell_type = $cl_id RETURN count(r)"
        return tx.run(query, cl_id=cl_id, genes=genes).single()[0]