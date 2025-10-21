# **scHilda: Hierarchical Integration of LLM with KG Database for Single-Cell Type Annotation**

**scHilda** is a novel computational framework designed to address the critical bottleneck of cell type annotation in single-cell RNA sequencing (scRNA-seq). By deeply integrating the reasoning process of a Large Language Model (LLM) with an external Knowledge Graph (KG) and employing a hierarchical arbitration annotation strategy, scHilda significantly enhances the accuracy, robustness, and interpretability of cell type annotation. This strategy first identifies major cell lineages with the support of global knowledge and subsequently retrieves focused subgraph information related to that lineage to precisely resolve cell subtypes, thereby effectively constraining the LLM's decision space and mitigating the risk of "hallucination."

*Figure 1: Schematic diagram of the scHilda hierarchical annotation and dynamic knowledge-enhanced reasoning framework.*

## **Installation and Configuration**

### **1\. Cloning the Repository**

```bash
git clone https://github.com/liangglhf/scHilda.git
cd scHilda
```

### **2\. Environment and Dependencies**

```bash
pip install anthropic numpy inflect neo4j ols-py openai pandas PyYAML tiktoken tqdm
```

### **3\. Knowledge Graph Configuration (Neo4j)**

1. **Launch a Neo4j instance.** You can use Neo4j Desktop or a server deployment.  
2. **Import the knowledge graph data.** Detailed instructions for populating the database are provided in [README.md](https://github.com/liangglhf/scHilda/blob/main/KG/README.md) of the 'KG/' directory.  
3. **Set your own information in the config.py** for the database connection: 

```bash
NEO4J\_URI="your_neo4j_uri"  
NEO4J\_USERNAME="your_neo4j_username"  
NEO4J\_PASSWORD="your_neo4j_password"
```

### **4\. LLM API Key Configuration**

Create a directory named APIs in the project root and place your API key files within this directory.

Set 'APIs/model\_api\_key.yaml' as:

```bash
base_url: your_model_base_url
api_key: your_model_api_key
```

## **Execution**

Once the configuration is complete, you can execute the main script to run the full pipeline on the benchmark datasets.

```bash
python main.py
```

This command will process the datasets predefined in 'main.py', save the annotation results to the 'results/' directory, and print the evaluation scores to the console.

To adapt the framework for your custom datasets, format your data according to the examples in the 'datasets/' directory and modify the dataset list within the 'main.py' script accordingly.
