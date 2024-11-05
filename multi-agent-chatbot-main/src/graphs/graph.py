from typing import Literal, Annotated, List

from langgraph.graph import StateGraph, START, END
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_cohere import ChatCohere
from langgraph.graph import MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.schema import HumanMessage

import os
import sys
from dotenv import load_dotenv

sys.path.append(os.getcwd())
from src.subgraphs.ServiceInformation.ServiceInformation_subgraph import ServiceInformationSubgraph
from src.subgraphs.faq_llm_career import FAQLLMSubgraph
from src.tools.careers import CareerToolNode
from src.all_prompts import supervisor_prompt

# Load environment variables
load_dotenv()

career_page_url = "https://lollypop.design/careers/"

class OverallState(MessagesState):
    # messages is implicit
    name: str
    email: str
    score: float
    options: List[str]


class Supervisor:
    """central supervising agent that transfers control to other nodes"""

    def __init__(self, llm):
        self.llm = llm
        self.next_node = END
        self.status = ""
        prompt = PromptTemplate(
            template = supervisor_prompt,
            input_variables=["question", "name", "email"],
        )
        self.chain = prompt | self.llm | StrOutputParser()

    def understand(self, state):

        messages = state['messages']
        question = messages[-1].content
        name = state.get("name", None)
        email = state.get("email", None)
        self.status = self.chain.invoke({"question":question, "name":name, "email":email})
        self.status = self.status.strip()
        response_msg = HumanMessage(content=question)
        return {'messages':[response_msg]}

    def get_next_node(self, state):

        if self.status == "introducing":
            self.next_node = "introduction_node"
        elif self.status == "answering":
            self.next_node = "faq_llm_node"
        else:
            self.next_node = END
        return self.next_node
    

# def stream_graph_updates(user_input: str, config: dict):
#     for event in graph.stream({"messages": [("user", user_input)]}, config):
#         for value in event.values():
#             print("Assistant: ", value["messages"][-1].content)


class LollypopDesignGraph:
    def __init__(self):
        # llm = ChatCohere(model='command-r-plus-08-2024')
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

        # Node creations
        self.supervisor_agent = Supervisor(llm)
        self.supervisor_node = self.supervisor_agent.understand

        service_info_subgraph = ServiceInformationSubgraph(llm)
        self.service_info_node = service_info_subgraph.IntroductionNode

        faq_subgraph = FAQLLMSubgraph(llm, embeddings)
        self.faq_node = faq_subgraph.faq_llm_career_build_graph()

        career_tool = CareerToolNode(career_page_url, llm)
        self.career_node = career_tool._run_search_jobs

    

    def build_graph(self):
        graph_builder = StateGraph(OverallState)
        graph_builder.add_node("supervisor_node", self.supervisor_node)
        graph_builder.add_node("introduction_node", self.service_info_node)
        graph_builder.add_node("faq_llm_node", self.faq_node)
        graph_builder.add_node("career_node", self.career_node)

        graph_builder.add_edge(START, "supervisor_node")
        graph_builder.add_conditional_edges("supervisor_node", self.supervisor_agent.get_next_node)
        graph_builder.add_edge("introduction_node", END)
        graph_builder.add_edge("faq_llm_node", END)
        graph_builder.add_edge("career_node", END)

        memory = MemorySaver()
        self.graph = graph_builder.compile(checkpointer=memory)
    

    def run_graph(self, user_input, session_id):
        config = {"configurable": {"thread_id": session_id}}
        llm_free_options = []
        inputs = {
            "messages": [
                ("user", user_input),
            ]
        }

        output = self.graph.invoke(inputs, config)
        chatbot_answer = output['messages'][-1].content
        if 'options' in output:
            llm_free_options = output['options']

        return {"chatbot_answer": chatbot_answer, "llm_free_options": llm_free_options}


if __name__ == "__main__":
    lollypop_design = LollypopDesignGraph()
    lollypop_design.build_graph()

    while True:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        output = lollypop_design.run_graph(user_input, session_id = "1")
        print("AI bot: ", output["chatbot_answer"])
        if 'llm_free_options' in output:
            print("LLM-free options: ", output['llm_free_options'])
        print("***************************")

    # uncomment to view the graph
    with open("graph_career.png", "wb") as png:
        png.write(lollypop_design.graph.get_graph(xray=1).draw_mermaid_png())