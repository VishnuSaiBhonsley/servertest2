from typing import Literal, Annotated, List
from pydantic import BaseModel, Field
from typing_extensions import TypedDict
import operator

from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, START, END
from langgraph.graph import MessagesState
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, RemoveMessage
from langgraph.prebuilt import ToolNode, tools_condition

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.output_parsers import JsonOutputParser

import os
from IPython.display import Image, display
import sys

sys.path.append(os.getcwd())
# import ServiceInformation_prompts as prompts
import src.all_prompts as prompts
from dotenv import load_dotenv

load_dotenv()

class OverallState(MessagesState):
    # messages is implicit
    name: str
    email: str


class UserInformation(BaseModel):
    """User Information from the user input"""
    name: str = Field(default=None, description="The user's name")
    email: str = Field(default=None, description="The user's email ID")

# class OverallState(TypedDict):
#     messages: Annotated[List[BaseMessage], operator.add]
#     name: str
#     email: str

# helper function for content extraction
class ServiceInformationSubgraph:
    def __init__(self, llm, decision_llm):
        self.llm = llm
        self.decision_llm = decision_llm

    def NameAndEmailParser(self, user_response: str):
        ##### name and email extraction #####
        user_name = None
        user_email = None
        
        # print("ServiceInformation-subgraph -- user_response")
        # print(user_response)
        # llm_with_tool = self.llm.with_structured_output(UserInformation)

        # print("ServiceInformationNode -- extractor prompt")
        prompt = PromptTemplate(template=prompts.extract_name_email_template, input_variables=["text"])
        # print(prompt)
        chain = prompt | self.decision_llm | JsonOutputParser()   

        # print("User response on which extraction is going to run")
        # print(user_response)

        # print("sleeping for 2 seconds")
        # time.sleep(5)
        decision = chain.invoke({"text": user_response})
        # print("extracted data")
        # print(decision)

        user_name = decision["name"] if decision["name"] != "" else None
        user_email = decision["email"] if decision["email"] != "" else None
        
        return user_name, user_email


    # Introduction Node
    def IntroductionNode(self, state: OverallState):
        """
        Node that greets the user, collects user's name, emailID and tells the service that the chat server can offer.
        """
        sys_msg = prompts.service_intro_template
        messages = [SystemMessage(content=sys_msg)] + state["messages"]
        response = self.llm.invoke(messages)
        # print("name in the state ", state["name"])
        # print("Number of messages in the state ", len(state["messages"]))
        # print("IntroductionNode: user input")
        # print("keys present in Introduction Node ", state.keys())

        user_name = state.get("name", None)
        user_email = state.get("email", None)
        # print("Keys ptresent in the state ", state.keys())
        # print("Old data in the state\n", user_name, user_email)

        # current turn user input - parse name and email from this content
        user_response = state["messages"][-1].content
        extracted_name, extracted_email = self.NameAndEmailParser(user_response)
        
        user_name = user_name if user_name is not None else extracted_name
        user_email = user_email if user_email is not None else extracted_email       

        # print("state captured ")
        # print(state.keys())
        # print(state)

        return {"messages": [response], "name": user_name, "email": user_email}


    # data 
    # LLM Free node
    def llm_free(self, state: OverallState):
        print("you came to llm free")
        return {"messages": ["llm free"]}


# LLM Node


# conditional edges
def should_go_to_llm_free(state: OverallState)  -> Literal[END, "llm_free"]:
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
        return "llm_free"
    else:
        return END
    




def stream_graph_updates(user_input: str, config: dict):
    for event in graph.stream({"messages": [("user", user_input)]}, config):
        for value in event.values():
            print("Assistant: ", value["messages"][-1].content)




if __name__ == "__main__":
    print("We begin")

    # llm object creation
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)

    graph_builder = StateGraph(OverallState)
    introduction_subgraph = ServiceInformationSubgraph(llm)

    # add nodes
    graph_builder.add_node("IntroductionNode", introduction_subgraph.IntroductionNode)
    graph_builder.add_node("llm_free", introduction_subgraph.llm_free)

    # build edges
    graph_builder.add_edge(START, "IntroductionNode")
    graph_builder.add_conditional_edges("IntroductionNode", should_go_to_llm_free)
    # graph_builder.add_edge("IntroductionNode", END)
    graph_builder.add_edge("llm_free", END)

    # compile graph
    memory = MemorySaver()
    graph = graph_builder.compile(checkpointer=memory)
    config = {"configurable": {"thread_id": "1"}}

    # uncomment to view the graph
    # with open("ServiceInformation.png", "wb") as png:
    #     png.write(graph.get_graph(xray=1).draw_mermaid_png())
    
    
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        # graph.invoke({"messages": [user_input]}, config)
        stream_graph_updates(user_input, config)
