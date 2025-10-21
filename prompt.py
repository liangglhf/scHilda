import json
import re
from config import TOP_N_CANDIDATES

def get_marker_genes(marker_str):
    if not isinstance(marker_str, str): return []
    return [gene.strip().upper() for gene in marker_str.strip().strip('"').split(',')]

def parse_llm_output(raw_output):
    try:
        match = re.search(r'\{.*\}', raw_output, re.DOTALL)
        if not match: return None
        return json.loads(match.group())
    except (json.JSONDecodeError, TypeError):
        return None

def parse_batch_output(llm_output):
    start_pattern = re.compile(r'^\s*(\d+):\s*(.*)')
    results_map = {}
    current_index = None
    buffer = []
    for line in llm_output.strip().split('\n'):
        match = start_pattern.match(line)
        if match:
            if current_index is not None and buffer:
                parsed_json = parse_llm_output("".join(buffer))
                if parsed_json: results_map[current_index] = parsed_json
            current_index = int(match.group(1))
            buffer = [match.group(2)]
        elif current_index is not None:
            buffer.append(line)
    if current_index is not None and buffer:
        parsed_json = parse_llm_output("".join(buffer))
        if parsed_json: results_map[current_index] = parsed_json
    return results_map

def create_major_type_proposal_prompt(segment_df):
    prompt = f"""
CRITICAL INSTRUCTIONS: You are an expert in single-cell transcriptomics. Your task is to act as a primary annotator. For EACH provided cell cluster index and its marker genes, you must propose the **{TOP_N_CANDIDATES} most probable** broad cell lineages (major types). Your reasoning should be based on your deep biological knowledge. The candidates should be ordered from most likely to least likely.
Your final output MUST be a list of responses. Each response MUST start on a new line and follow the format `INDEX: JSON_OBJECT` EXACTLY.
**JSON Format:**
{{
  "candidates": [
    {{"cell_type_name": "...", "cell_ontology_id": "CL:...", "reasoning": "The presence of canonical markers like CD3D, CD4, and CD8A strongly indicates a T cell lineage. These are fundamental to T cell identity."}},
    {{"cell_type_name": "...", "cell_ontology_id": "CL:...", "reasoning": "..."}},
    {{"cell_type_name": "...", "cell_ontology_id": "CL:...", "reasoning": "..."}}
  ]
}}
---
**Marker Gene Lists to Process:**
"""
    marker_lines = [f"{index}: {', '.join(get_marker_genes(row['marker']))}" for index, row in segment_df.iterrows()]
    return prompt + "\n".join(marker_lines)

def create_major_decision_prompt(task_data):
    initial_proposal = f"### Initial LLM Hypothesis (Phase 1)\n{json.dumps(task_data['initial_candidates'], indent=2)}\n"
    
    evidence_archive = "### Evidence Archive\n"
    for cand in task_data['candidates_with_evidence']:
        evidence_archive += f"#### Candidate: {cand['cell_type_name']}\n"
        evidence_archive += f"- **Knowledge Graph Qualitative Summary:**\n{cand['kg_evidence_summary']}\n\n"
        
    prompt = f"""
CRITICAL INSTRUCTIONS: You are a senior computational biologist acting as the final arbiter for a challenging cell type annotation case. An initial analysis has yielded several hypotheses. Your task is to critically evaluate all available qualitative evidence from the Knowledge Graph to make a definitive judgment on the most likely **major cell type**.
**IMPORTANT CONTEXT:**
- The **Knowledge Graph (KG)** contains curated, symbolic knowledge about cell types, markers, and pathways. Your decision should consider the provided KG summaries for each candidate.
Your final output MUST be a single JSON object.
**JSON Format:**
{{
  "final_major_type_name": "...",
  "final_major_type_id": "..."
}}
---
**Decision Archive for Cluster {task_data['cluster_index']}**

{initial_proposal}
{evidence_archive}
"""
    return prompt

def create_final_subtype_prompt(major_type_name, major_type_id, focused_kg_evidence):
    ''' If want to get a explanatory output of the modle, add the following content to the end of the "JSON Format", after the "cell_ontology_id": "...",
        "reasoning": "Based on the confirmed major type '{major_type_name}' and the KG pathway evidence, the final annotation is [Subtype Y].",
        "evidence": {{ "positive_markers": ["...", "..."] }}
    '''
    return f"""
CRITICAL INSTRUCTIONS: You are a cell annotation specialist. The major cell type has been confidently identified. Your task is to determine the most specific subtype based on the provided focused evidence from a knowledge graph.
Your final output MUST be a single JSON object.
**JSON Format:**
{{
  "cell_type_name": "...", 
  "cell_ontology_id": "...",
}}
---
**Annotation Task:**
* **Confirmed Major Type:** {major_type_name} (ID: {major_type_id})
* **Focused Subtype Knowledge Graph Evidence (Pathway-based):**
{focused_kg_evidence}
"""