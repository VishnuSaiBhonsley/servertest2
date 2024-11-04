# Multi-agent Chatbot

## Setting up the environment

### 1. Create new environment and activate

Virtual Environment:
```
python -m venv venv
source venv/Scripts/activate

```

Conda Environment:
```
conda create -n env_name python=version
conda activate env_name

```



### 2. Install requirements

```
pip install -r requirements.txt
```

### 3. Run the following once to create knowledge base for FAQs and RAG

1. FAQ Embeddings creation from pdf document:
Create 'Data/faq_data' folder and ensure the FAQ pdf presence in the folder. From root directory run:
```
python src/nodes/search.py 
```

2. Data Indexing and Vectorstore creation for RAG based LLM agent
```
python src/nodes/llm-driven.py 
```

