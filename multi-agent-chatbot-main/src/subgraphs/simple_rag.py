from langgraph.graph import StateGraph, START, END
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import ToolNode, tools_condition

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver

import os
from dotenv import load_dotenv
from typing import Annotated
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict
from typing import List


llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)

# pre-built Message class with pre-build messages key
from langgraph.graph import MessagesState

# class MessagesState(MessagesState):
#     # Add any keys needed beyond messages, which is pre-built
#     messages: Annotated[list[int], add_messages]

class NewState(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list[int], add_messages]

sys_msg = SystemMessage(content="You are a helpful assistant tasked with performing arithmetic on a set of inputs.")
# create node
def assistant(state: MessagesState):
   return {"messages": [llm.invoke([sys_msg] + state["messages"])]}

# building graph
builder = StateGraph(NewState)

# defining nodes
# assistant is the llm function with tools binding
builder.add_node("assistant", assistant)
# defining edges
# START -> assistant -> conditional edge -> tools -> END
builder.add_edge(START, "assistant")
# re-routing tool back to assistant
builder.add_edge("assistant", END)

memory = MemorySaver()
# compile graph
react_graph = builder.compile(checkpointer=memory)


def stream_graph_updates(graph, user_input: str, config):
    for event in graph.stream({"messages": [("user", user_input)]}, config):
        for value in event.values():
            print("Assistant:", value["messages"][-1].content)

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "3"}}

    while True:
        user_input = input("User: ")
        if user_input == "done":
            break
        messages = react_graph.invoke({"messages": user_input}, config)
        # print("=====raw messages====")
        # print(messages)
        # print("===raw ends===")
        for m in messages['messages']:
            m.pretty_print()
        
        # stream_graph_updates(react_graph, user_input, config)
