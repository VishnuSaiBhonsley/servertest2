import sys
import os
sys.path.append(os.getcwd())
import pprint

from langgraph.graph import START, MessagesState, StateGraph, END
from langgraph.prebuilt import ToolNode
from typing import Annotated, Sequence, List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain.schema import AIMessage
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.nodes.search import SearchNode
from src.nodes.llm_driven import LLMNode
from src.tools.careers import CareerToolNode
from src.all_prompts import job_intent_template


# Directory initializations
ROOT_DIR = "Data"
PDF_PATH = f'{ROOT_DIR}/faq_data/Lollypop_Design_FAQS.pdf'
EMBEDDINGS_PATH = f'{ROOT_DIR}/faq_data/faq_embeddings.npz'
FAQ_JSON_PATH = f'{ROOT_DIR}/faq_data/faqs_from_pdf.json'
vectorstore_path = f"{ROOT_DIR}/vectorstore.db"

# Website for indexing
URL = "https://lollypop.design/"
career_page_url = "https://lollypop.design/careers/"
FAQ_SEARCH_THRESH = 0.85


# state definition
class AgentState(TypedDict):
    # The add_messages function defines how an update should be processed
    # Default is to replace. add_messages says "append"
    messages: Annotated[Sequence[BaseMessage], add_messages]
    score: float
    options: List[str]

class FAQLLMSubgraph:
    def __init__(self, llm, decision_llm, embeddings):
        self.llm = llm
        self.decision_llm = decision_llm
        self.embeddings = embeddings
        # initialize LLM, search, career nodes
        self.llm_obj = LLMNode(self.llm, self.embeddings, vectorstore_path, URL)
        self.search_obj = SearchNode(PDF_PATH, EMBEDDINGS_PATH, FAQ_JSON_PATH)
        self.search_obj.load_faq_data()      # load the faq data on startup
        self.tool_obj = CareerToolNode(career_page_url, llm)

    # condition and routing functions
    def llm_free(self, state):

        messages = state['messages']
        question = messages[-1].content
        top_faqs, top_scores = self.search_obj.faq_search(question, mode='cosine')
        options = []                    # consists top 4 QAs. Top 1 is given as answer, rest 3 questions as options
        for faq in top_faqs:
            options.append(faq['question'])
        relevant_options = options[1:]
        top_score = float(top_scores[0])
        if top_score < FAQ_SEARCH_THRESH:
            return {'score':top_score, 'options':relevant_options}
        ai_response = AIMessage(content=top_faqs[0]['answer'])
        return {'messages': [ai_response], 'score':top_score, 'options':relevant_options}

    def route_to_llm(self, state):

        top_score = state['score']
        if top_score < FAQ_SEARCH_THRESH:
            return "yes"
        return "no"

    def tool_condition(self, state):

        prompt = PromptTemplate(
            template=job_intent_template,
            input_variables=["question"],
        )

        rag_chain = prompt | self.decision_llm | StrOutputParser()
        messages = state['messages']
        question = messages[-1].content
        output = rag_chain.invoke({"question": question})
        output = output.strip()

        return output


    def faq_llm_career_build_graph(self):
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node('llm_agent', self.llm_obj.rag_agent_run)
        workflow.add_node('llm_free', self.llm_free)
        # workflow.add_node('career_tool', self.tool_obj._run_search_jobs)

        # Add edges
        workflow.add_edge(START, "llm_free")
        # workflow.add_conditional_edges(
        #     START,
        #     self.tool_condition,
        #     {
        #         "yes": "career_tool",
        #         "no": "llm_free",
        #     },
        # )
        workflow.add_conditional_edges(
            "llm_free",
            self.route_to_llm,
            {
                "yes": "llm_agent",
                "no": END,
            },
        )
        # workflow.add_edge("career_tool", END)
        workflow.add_edge("llm_agent", END)

        memory = MemorySaver()
        graph = workflow.compile(checkpointer=memory)
        return graph


if __name__ == "__main__":
    # LLM and Embed models
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=os.getenv("GOOGLE_API_KEY"))
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    
    # Compile
    faq_career_node = FAQLLMSubgraph(llm, embeddings)
    graph = faq_career_node.faq_llm_career_build_graph()
    id = "abc123"
    config = {"configurable": {"thread_id": id}}
    # testing the graph
    while True:
        print("***************************")
        user_input = input("Human Message:")
        if 'bye' in user_input:
            print('Thank you for contacting TL. Have a nice day!')
            break
        inputs = {
            "messages": [
                ("user", user_input),
            ]
        }
        output = graph.invoke(inputs, config)
        print("AI message: ", output['messages'][-1].content)
        if 'options' in output:
            print("LLM-free options: ", output['options'])
        print("***************************")
