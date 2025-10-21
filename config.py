import os

RESULTS_DIR = "results"
MODEL = "deepseek-chat"
TOP_N_CANDIDATES = 3
MAX_RETRIES = 3

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

SEGMENT_SIZE = 4
MAX_WORKERS = 64

BASE_PATH = "./"
DATA_BASE_PATH = os.path.join(BASE_PATH, "datasets/")
EVAL_DATA_PATH = os.path.join(BASE_PATH, "eval/")
COMPILED_FILE_PATH = os.path.join(EVAL_DATA_PATH, "compiled.csv")
RELATION_FILE_PATH = os.path.join(EVAL_DATA_PATH, "relation.csv")