from typing import Literal, Annotated, List

from langgraph.graph import StateGraph, START, END
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import GoogleGenerativeAIEmbeddings

import os
import sys
from dotenv import load_dotenv

sys.path.append(os.getcwd())
from src.subgraphs.ServiceInformation.ServiceInformation_subgraph import ServiceInformationSubgraph
from src.subgraphs.faq_llm_career import FAQLLMSubgraph

# Load environment variables
load_dotenv()

class OverallState(MessagesState):
    # messages is implicit
    name: str
    email: str
    score: float
    options: List[str]


# conditional edges
def should_go_to_llm_career(state: OverallState)  -> Literal[END, "faq_llm_career"]:
    """
    Determines whether the user has provided their name and email ID to proceed to LLM free Node.
   
    Args:
        state (messages): The current state
    
    Returns:
        str: A decision whether to go back to END or LLM Free node
    """
    if "name" in state and "email" in state and state["name"] is not None and state["email"] is not None:
        print("condition edge")
        print(state["name"], "---", state["email"])
        return "faq_llm_career"
    else:
        return END

def stream_graph_updates(user_input: str, config: dict):
    for event in graph.stream({"messages": [("user", user_input)]}, config):
        for value in event.values():
            print("Assistant: ", value["messages"][-1].content)


if __name__ == "__main__":
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    # Building graph

    faq_subgraph = FAQLLMSubgraph(llm, embeddings)
    faq_node = faq_subgraph.faq_llm_career_build_graph()
    service_info_subgraph = ServiceInformationSubgraph(llm)
    service_info_node = service_info_subgraph.IntroductionNode

    graph_builder = StateGraph(OverallState)
    graph_builder.add_node("IntroductionNode", service_info_node)
    graph_builder.add_node("faq_llm_career", faq_node)

    graph_builder.add_edge(START, "IntroductionNode")
    graph_builder.add_conditional_edges("IntroductionNode", should_go_to_llm_career)
    graph_builder.add_edge("faq_llm_career", END)

    memory = MemorySaver()
    graph = graph_builder.compile(checkpointer=memory)

    config = {"configurable": {"thread_id": "1"}}

    # uncomment to view the graph
    # with open("graph.png", "wb") as png:
    #     png.write(graph.get_graph(xray=1).draw_mermaid_png())

    while True:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        # graph.invoke({"messages": [user_input]}, config)
        stream_graph_updates(user_input, config)

