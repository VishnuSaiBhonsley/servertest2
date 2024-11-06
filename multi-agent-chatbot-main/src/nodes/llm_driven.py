# Import all the necessary packages
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
# os.environ["OPENAI_API_KEY"] = "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"
os.environ["GOOGLE_API_KEY"] = "AIzaSyCnCmG44TfCZq27P9aVVX5ug1x_ovhb1kI"
import json
import re
from bs4 import BeautifulSoup

from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_retrieval_chain, create_history_aware_retriever
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import BaseMessage
from langgraph.graph import START, MessagesState, StateGraph
from langchain_community.document_loaders import RecursiveUrlLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain.schema import AIMessage
from langchain.memory import ConversationBufferMemory

from src.all_prompts import rag_agent_system_template, service_intro_template


class LLMNode:

    def __init__(self, llm, embeddings, vectorstore_path, url):
        self.llm = llm
        self.embeddings = embeddings
        self.vectorstore_path = vectorstore_path
        self.url = url
        self.retriever = None
        # index the data first
        self.index_data()
        self.rag_agent_init()

    def bs4_extractor(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        return re.sub(r"\n\n+", "\n\n", soup.text).strip()

    def index_data(self):

        # crete index for the first time
        if len(os.listdir(self.vectorstore_path)) == 0:
            loader = RecursiveUrlLoader(self.url, extractor=self.bs4_extractor)
            docs_list = loader.load()
            text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                chunk_size=100, chunk_overlap=50
            )
            doc_splits = text_splitter.split_documents(docs_list)
            # Create a vectorstore
            vectorstore = FAISS.from_documents(doc_splits, self.embeddings)
            # Save the documents and embeddings
            vectorstore.save_local(self.vectorstore_path)
        else:
            # load saved index
            vectorstore = FAISS.load_local(self.vectorstore_path, self.embeddings, allow_dangerous_deserialization=True)

        # Create retriever
        self.retriever = vectorstore.as_retriever()

    def rag_agent_init(self):

        # # Create a prompt template
        template = rag_agent_system_template

        memory = ConversationBufferMemory(memory_key="chat_history")

        ### Contextualize question ###
        contextualize_q_system_prompt = """Given a chat history and the latest user question \
        which might reference context in the chat history, formulate a standalone question \
        which can be understood without the chat history. Do NOT answer the question, \
        just reformulate it if needed and otherwise return it as is."""
        contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        self.history_aware_retriever = create_history_aware_retriever(
            self.llm, self.retriever, contextualize_q_prompt
        )

        # Create a prompt template
        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", template),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )

        # Create a chain 
        doc_chain = create_stuff_documents_chain(self.llm, qa_prompt)
        rag_chain = create_retrieval_chain(self.history_aware_retriever, doc_chain)

        ### Statefully manage chat history ###
        store = {}


        def get_session_history(session_id: str) -> BaseChatMessageHistory:
            if session_id not in store:
                store[session_id] = ChatMessageHistory()
            return store[session_id]


        self.conversation_rag_chain = RunnableWithMessageHistory(
            rag_chain,
            get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )

    def rag_agent_run(self, state: MessagesState, config) -> list[BaseMessage]:

        messages = state['messages']
        question = messages[-1].content
        session_id = config["configurable"]["thread_id"]
        response = self.conversation_rag_chain.invoke({"input": question}, config={"configurable": {"session_id": session_id}})['answer']
        ai_response = AIMessage(content=response)
        return {"messages": [ai_response]}

if __name__ == "__main__":
    # Gemini models
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=os.getenv("GOOGLE_API_KEY"))
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    # vectorstore path
    ROOT_DIR = "Data"
    vectorstore_path = f"{ROOT_DIR}/vectorstore.db"
    URL = "https://terralogic.com/"
    llm_obj = LLMNode(llm, embeddings, vectorstore_path, URL)
    