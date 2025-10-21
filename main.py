import os
import pandas as pd
import numpy as np
import time
import json
import sys
from tqdm import tqdm
import concurrent.futures
import traceback
from LLM import complete_text
import config
from KG import KnowledgeGraphHandler
import prompt
import eval

def major_propose(segment_df):
    p = prompt.create_major_type_proposal_prompt(segment_df)
    llm_output = complete_text(p, model=config.MODEL)
    return prompt.parse_batch_output(llm_output)

def major_decide(task_data, kg_handler):
    marker_genes = prompt.get_marker_genes(task_data['marker'])
    initial_candidates = task_data.get('initial_candidates', {}).get('candidates', [])
    
    candidates_with_evidence = []
    for cand in initial_candidates:
        cl_id = cand.get("cell_ontology_id")
        kg_summary = kg_handler.get_qualitative_evidence_summary(cl_id, marker_genes)
        
        cand_with_evidence = cand.copy()
        cand_with_evidence['kg_evidence_summary'] = kg_summary
        candidates_with_evidence.append(cand_with_evidence)
    
    task_data['candidates_with_evidence'] = candidates_with_evidence

    p_decision = prompt.create_major_decision_prompt(task_data)
    llm_output = complete_text(p_decision, model=config.MODEL)
    expert_decision = prompt.parse_llm_output(llm_output)
    
    major_type_name, major_type_id = None, None
    if expert_decision:
        major_type_name = expert_decision.get('final_major_type_name')
        major_type_id = expert_decision.get('final_major_type_id')
    
    if not major_type_name or not major_type_id:
        if initial_candidates:
            major_type_name = initial_candidates[0].get('cell_type_name')
            major_type_id = initial_candidates[0].get('cell_ontology_id')

    task_data['final_major_type_name'] = major_type_name
    task_data['final_major_type_id'] = major_type_id
    
    return task_data

def sub_annotation(task_data, kg_handler):
    major_type_name = task_data.get('final_major_type_name')
    major_type_id = task_data.get('final_major_type_id')
    marker_genes = prompt.get_marker_genes(task_data['marker'])

    if not major_type_name or not major_type_id:
         task_data['final_annotation'] = {"error": "Could not determine major type in the previous phase."}
         return task_data

    focused_evidence = kg_handler.get_focused_subtype_evidence(major_type_id, marker_genes)
    p_final = prompt.create_final_subtype_prompt(major_type_name, major_type_id, focused_evidence)
    final_llm_output = complete_text(p_final, model=config.MODEL)
    
    final_annotation = prompt.parse_llm_output(final_llm_output)
    if final_annotation:
        task_data['final_annotation'] = final_annotation
    else:
        task_data['final_annotation'] = {
            "cell_type_name": major_type_name,
            "cell_ontology_id": major_type_id,
        }
    return task_data

def run_pipeline(dataset_name, dataset_path):
    print(f"\n--- Starting to process dataset: {dataset_name} ---")
    df = pd.read_csv(dataset_path)
    kg_handler = KnowledgeGraphHandler(config.NEO4J_URI, config.NEO4J_USERNAME, config.NEO4J_PASSWORD)

    print("\nPhase 1: Proposing major types with LLM ...")
    phase1_results = {}
    segments = [df.iloc[i:i+config.SEGMENT_SIZE] for i in range(0, len(df), config.SEGMENT_SIZE)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        futures = {executor.submit(major_propose, seg): seg for seg in segments}
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(segments), desc="Phase 1: Proposing"):
            try:
                result = future.result()
                if result: phase1_results.update(result)
            except Exception as e:
                print(f"A Phase 1 task failed: {e}")

    print("\nPhase 2: Deciding major types with KG evidence ...")
    phase2_tasks = []
    for index, row in df.iterrows():
        if index in phase1_results:
            task = row.to_dict()
            task['cluster_index'] = index
            task['initial_candidates'] = phase1_results[index]
            phase2_tasks.append(task)
    
    phase2_results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        futures = {executor.submit(major_decide, task, kg_handler): task['cluster_index'] for task in phase2_tasks}
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(phase2_tasks), desc="Phase 2: Deciding"):
            try:
                result = future.result()
                if result and 'cluster_index' in result:
                    phase2_results[result['cluster_index']] = result
            except Exception as e:
                print(f"A Phase 2 task failed: {e}")

    print("\nPhase 3: Annotating subtypes using subgraph domain ...")
    phase3_tasks = list(phase2_results.values())
    all_final_results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        futures = {executor.submit(sub_annotation, task, kg_handler): task['cluster_index'] for task in phase3_tasks}
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(phase3_tasks), desc="Phase 3: Annotating"):
            try:
                result = future.result()
                if result and 'cluster_index' in result:
                    all_final_results[result['cluster_index']] = result
            except Exception as e:
                print(f"A Phase 3 task failed: {e}")

    print("\nAssembling final results ...")
    final_rows = []
    for index, row in df.iterrows():
        res = row.to_dict()
        res['cluster'] = index

        final_result_data = all_final_results.get(index)
        if final_result_data and 'final_annotation' in final_result_data:
            final_anno = final_result_data['final_annotation']
            res['scHilda_final_prediction_name'] = final_anno.get('cell_type_name', 'Unassigned')
            res['scHilda_final_prediction_id'] = final_anno.get('cell_ontology_id', 'Unassigned')
            res['llm_final_decision_raw'] = json.dumps(final_anno)
        else:
            res['scHilda_final_prediction_name'] = 'Unassigned'
            res['scHilda_final_prediction_id'] = 'Unassigned'
            res['llm_final_decision_raw'] = '{"error": "Annotation failed completely."}'

        final_rows.append(res)
        
    final_results_df = pd.DataFrame(final_rows)
    columns_to_drop = [
        'candidates_with_scores', 'initial_candidates', 'confirmed_major_type', 
        'softmax_scores', 'top1_raw_score', 'top1_softmax_score', 'total_sw_score',
        'determined_path'
    ]
    final_results_df = final_results_df.drop(columns=columns_to_drop, errors='ignore')

    output_filename = os.path.join(config.RESULTS_DIR, f"scHilda_results_{dataset_name}.csv")
    final_results_df.to_csv(output_filename, index=False)
    print(f"\nResults saved to: {output_filename}")

    kg_handler.close()

def run_evaluation_stage(data, dataset_name, cl, hier):
    print(f"\n--- Starting evaluation for {dataset_name} ---")
    if data.empty:
        print("\nEvaluation Error: The results dataframe is empty.")
        return

    scores = []
    data['scHilda_final_prediction_name'] = data['scHilda_final_prediction_name'].astype(str)

    for _, row in tqdm(data.iterrows(), total=len(data), desc="Evaluating"):
        pred_cell = row['scHilda_final_prediction_name']
        true_cell_info = row[['manual_annotation', 'manual_CLname', 'manual_CLID', 'manual_broadtype']].to_dict()
        score = eval.eval_cell_type_annotation_per_cell(pred_cell, true_cell_info, cl, hier)
        scores.append(score)
    
    agreement_score = np.mean(scores) if scores else 0

    print("\n====================== scHilda Evaluation ======================")
    print(f"Dataset: {dataset_name}")
    print(f"Total cell clusters: {len(data)}")
    print(f"Agreement Score: {agreement_score:.4f}")
    print("================================================================\n")


if __name__ == "__main__":
    os.makedirs(config.RESULTS_DIR, exist_ok=True)
    
    if not config.NEO4J_PASSWORD:
        print("Warning: NEO4J_PASSWORD environment variable not found. Using default password from config.py.")

    try:
      cl_df = pd.read_csv(config.COMPILED_FILE_PATH)
      hier_df = pd.read_csv(config.RELATION_FILE_PATH, header=None)
    except FileNotFoundError as e:
      sys.exit(f"Error: Could not load evaluation dependency files. Please check the paths. {e}")

    start_time = time.time()
    datasets_to_process = [
        {"name": "coloncancer", "path": os.path.join(config.DATA_BASE_PATH, "coloncancer.csv")},
        {"name": "BCL", "path": os.path.join(config.DATA_BASE_PATH, "BCL.csv")},
        {"name": "literature", "path": os.path.join(config.DATA_BASE_PATH, "literature.csv")},
        {"name": "lungcancer", "path": os.path.join(config.DATA_BASE_PATH, "lungcancer.csv")},
        {"name": "HCA", "path": os.path.join(config.DATA_BASE_PATH, "HCA.csv")},
        {"name": "HCL", "path": os.path.join(config.DATA_BASE_PATH, "HCL.csv")},
        {"name": "MCA", "path": os.path.join(config.DATA_BASE_PATH, "MCA.csv")},
        {"name": "Azimuth", "path": os.path.join(config.DATA_BASE_PATH, "Azimuth.csv")},
    ]

    for dataset in datasets_to_process:
        if not os.path.exists(dataset["path"]):
            print(f"\nWarning: Dataset file not found, skipping: {dataset['path']}")
            continue
        
        run_pipeline(dataset["name"], dataset["path"])
        
        try:
            output_filename = os.path.join(config.RESULTS_DIR, f"scHilda_results_{dataset['name']}_refined_only.csv")
            results_df = pd.read_csv(output_filename)
            run_evaluation_stage(results_df, dataset['name'], cl_df, hier_df)
        except FileNotFoundError:
            print(f"Evaluation failed: Result file not found at {output_filename}")
        except Exception as e:
            print(f"An unknown error occurred during evaluation: {e}")
            traceback.print_exc()

    end_time = time.time()
    print(f"\n--- All datasets processed. Total time: {end_time - start_time:.2f} seconds ---")