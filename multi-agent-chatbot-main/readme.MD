# Multi-agent Chatbot

## Setting up the environment

### 1. Create new environment and activate

```

python -m venv venv
source venv/Scripts/activate

```



### 2. Install requirements

```
pip install -r requirements.txt
```

### 3. Environment setup
Create a `.env` file within multi-agent chatbot folder. Add the following-

```
GOOGLE_API_KEY = <GOOGLE API KEY>

LANGCHAIN_TRACING_V2 = false <toggle to capture trace on LangSmith>
LANGCHAIN_ENDPOINT = https://api.smith.langchain.com
LANGCHAIN_API_KEY = < langchain api key >
LANGCHAIN_PROJECT = < langchain project name >
```