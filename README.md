# **scHilda: Hierarchical Integration of LLM with KG Database for Single-Cell Type Annotation**

**scHilda** is a novel computational framework designed to address the critical bottleneck of cell type annotation in single-cell RNA sequencing (scRNA-seq). By deeply integrating the reasoning process of a Large Language Model (LLM) with an external Knowledge Graph (KG) and employing a hierarchical arbitration annotation strategy, scHilda significantly enhances the accuracy, robustness, and interpretability of cell type annotation. This strategy first identifies major cell lineages with the support of global knowledge and subsequently retrieves focused subgraph information related to that lineage to precisely resolve cell subtypes, thereby effectively constraining the LLM's decision space and mitigating the risk of "hallucination."

*Figure 1: Schematic diagram of the scHilda hierarchical annotation and dynamic knowledge-enhanced reasoning framework.*

## **Installation and Configuration**

### **1\. Cloning the Repository**

```bash
git clone \[URL\_to\_your\_repository\]  
cd scHilda
```

### **2\. Environment and Dependencies**

We recommend using Conda for environment management.

```bash
conda create \-n scHilda python=3.10  
conda activate scHilda
pip install anthropic numpy inflect neo4j ols-py openai pandas PyYAML tiktoken tqdm
```

### **3\. Knowledge Graph Configuration (Neo4j)**

1. **Launch a Neo4j instance.** You can use Neo4j Desktop or a server deployment.  
2. **Import the knowledge graph data.** Detailed instructions for populating the database are provided in the $\texttt{\`KG/README.md\`}$ 'KG/README.md'.  
3. **Set your own information in the config.py** for the database connection: 

```bash
NEO4J\_URI="bolt://localhost:7687"  
NEO4J\_USERNAME="neo4j"  
NEO4J\_PASSWORD="your\_neo4j\_password"
```

### **4\. LLM API Key Configuration**

Place your API key in the corresponding file of 'APIs/'.
Set APIs/model/model\_api\_key.yaml:

```bash
  your\_model\_api\_key  
```

## **Execution**

Once the configuration is complete, you can execute the main script to run the full pipeline on the benchmark datasets.

```bash
python main.py
```

This command will process the datasets predefined in main.py, save the annotation results to the 'results/', and print the evaluation scores to the console.

To adapt the framework for your custom datasets, format your data according to the examples in the 'datasets/' and modify the dataset list within the 'main.py' script accordingly.
