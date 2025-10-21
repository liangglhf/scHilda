""" Ref: https://github.com/jianghao-zhang/CellTypeAgent/blob/main/CellTypeAgent/eval.py"""
import pandas as pd
import numpy as np
from ols_py.client import Ols4Client
import time
import re
import inflect

def standardize_cell_type(cell_type):
    cell_type = str(cell_type).strip(' ')
    cell_type = re.sub(r'^\d+[\.\ -\-\:]\s*', '', cell_type)
    cell_type = cell_type.strip('.:- ')
    p = inflect.engine()
    singular_cell_type = p.singular_noun(cell_type) 
    if singular_cell_type:
        return singular_cell_type.lower()
    else:
        return cell_type.lower().replace('cells', 'cell')

def flatten(lst):
    if lst is None:
        return []
    flat_list = []
    for item in lst:
        if item is not None:
            if isinstance(item, list):
                flat_list.extend(flatten(item))
            else:
                flat_list.append(item)
    return flat_list

def CL_term_search(cell_type):
    client = Ols4Client()
    try:
        resp = client.select(cell_type, params={"ontology": "cl"})
        if resp.response.numFound == 0:
            return "unknown"
        
        terms = [doc.obo_id for doc in resp.response.docs if doc.obo_id]
        valid_terms = [term for term in terms if term.startswith("CL:")] 
        
        return valid_terms[0] if valid_terms else "unknown"
    except Exception:
        return "unknown"


def match_CLID(cell_type, cl):
    standardized_name = standardize_cell_type(cell_type)

    match = cl[cl['originalname'] == standardized_name]
    if not match.empty:
        return match['CLID'].values[0]
    
    match = cl[cl['Clname'] == standardized_name]
    if not match.empty:
        return match['CLID'].values[0]

    match = cl[cl['originalname'].str.contains(standardized_name, regex=False, na=False)]
    if not match.empty:
        return match['CLID'].values[0]

    max_retry = 3
    clid = "unknown"
    while max_retry > 0:
        try:
            clid = CL_term_search(cell_type)
            break
        except Exception:
            print("Rate limit reached for OLS search. Waiting for 1 second.")
            time.sleep(1)
            max_retry -= 1
            
    return clid

def match_CL_info(CLID, cl, cell_type=None):
    CLname = cl.loc[cl['CLID'] == CLID, 'Clname'].values[0] if len(cl.loc[cl['CLID'] == CLID, 'Clname']) > 0 else "unknown"
    broadtype = cl.loc[cl['CLID'] == CLID, 'type'].values[0] if len(cl.loc[cl['CLID'] == CLID, 'type']) > 0 else "unknown"

    if cell_type is not None: 
        cell_type_std = standardize_cell_type(cell_type)
        broadtype = cl.loc[cl['originalname'] == cell_type_std, 'type'].values[0] if len(cl.loc[cl['originalname'] == cell_type_std, 'type']) > 0 else broadtype

    return CLname, broadtype

def eval_cell_type_annotation_per_cell(pred_cell_type, true_cell_type, cl, hier):
    pred_cell_type_std = standardize_cell_type(pred_cell_type)
    true_cell_name_std = standardize_cell_type(true_cell_type.get('manual_annotation', ''))
    
    pred_CLID = match_CLID(pred_cell_type_std, cl)
    _, pred_broadtype = match_CL_info(pred_CLID, cl, pred_cell_type_std)
    
    true_CLID = true_cell_type.get('manual_CLID', 'unknown')
    true_broadtype = true_cell_type.get('manual_broadtype', 'unknown')
    if pd.isna(true_broadtype): true_broadtype = 'unknown'

    # 1. Full score check (Score = 1.0)
    s1 = False
    if pred_CLID != "unknown" and true_CLID != "unknown" and pd.notna(pred_CLID) and pd.notna(true_CLID):
        t1 = set(str(true_CLID).split(','))
        t2 = set(str(pred_CLID).split(','))
        union_set = t1.union(t2) - {"unknown", None}
        if len(union_set) > 0:
            s1 = len(t1.intersection(t2)) == len(union_set)

    s2 = pred_cell_type_std == true_cell_name_std
    s3 = (str(true_broadtype) == 'malignant cell' and str(pred_broadtype) == 'malignant cell')

    if s1 or s2 or s3:
        return 1.0

    # 2. Partial score check (Score = 0.5)
    hier_full = pd.concat([hier, hier.iloc[:, [1, 0]].rename(columns={1: 0, 0: 1})], ignore_index=True)
    hv = {}
    for _, row in hier_full.iterrows():
        key, value = row[1], row[0]
        if key not in hv:
            hv[key] = []
        hv[key].append(value)
    
    t1 = set(str(true_broadtype).split(','))
    t2 = set(str(pred_broadtype).split(','))

    t1_expanded = t1.union(set(flatten([hv.get(x) for x in t1])))
    t2_expanded = t2.union(set(flatten([hv.get(x) for x in t2])))
    
    intersection = t1_expanded.intersection(t2_expanded) - {"unknown", None, 'nan'}
    if len(intersection) > 0:
        return 0.5
    
    # 3. Mismatch (Score = 0.0)
    return 0.0