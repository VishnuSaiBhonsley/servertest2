from langgraph.graph import StateGraph, START, END
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage, SystemMessage, RemoveMessage
from langgraph.prebuilt import ToolNode, tools_condition

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver

import os
from IPython.display import Image, display
import sys
sys.path.append(os.getcwd())

from src.tools.sendGmail import SendGmailTool


llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)


# creating messages
class State(MessagesState):
    summary: str


# chatbot node
def chatbot_with_summary(state: State):
    """
    Node that uses summary, if available, to prepare response.

    Args:
        state: Message state of the conversation, with 'messages' and 'summary'
    
    Returns:

    """
    summary = state.get("summary", "")
    sys_msg = '''You are a helpful assistant for Terralogic website. 
                            You will provide information about the service,  career page and how to contact Sales.\n'''
    if summary:
        system_summary_message = f"Summary of the earlier conversation: {summary}"
        # append summary to new message
        system_message = [sys_msg] + [system_summary_message]
        messages = [SystemMessage(content=system_message)] + state["messages"]
    else:
        messages = [SystemMessage(content=sys_msg)] + state["messages"]
    
    response = llm.invoke(messages)
    return {"messages": response}


# summarizer node
def summarize_conversation(state: State):
    """
    Creates summary of the conversation. If there is a summary already present, it extends it.

    Args:
        state: Message state of the conversation, with 'messages' and 'summary'
    
    Returns:
        state:
    """
    summary = state.get('summary', "")

    # summary prompt
    if summary:
        summary_message = (f"This is the summary of the prior conversation : {summary}\n"
                            "Extend the summary by considering the new message above. Make it short and apt. Dont leave out user activities.")
    else:
        summary_message = "Create a summary of the conversation above: .Make it short and apt. Dont leave out user activities."
    
    messages = state["messages"] + [HumanMessage(content=summary_message)]
    response = llm.invoke(messages)

    # Delete all but the 2 most recent messages
    # delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]
    # return {"summary": response.content, "messages": delete_messages}
    return {"summary": response.content}


def send_email(state: State):
    """
    Node to invoke gmail tool subgraph
    """
    summary_msg = graph.get_state(config).values.get("summary","")
    print("Summary message to be sent")
    print(summary_msg)
    print(state["summary"])
    messages = HumanMessage(content=summary_msg)
    response = gmail_subgraph.invoke({"mail_content": messages})
    return 


# conditional edge
def should_summarize(state: State):
    """
    """
    messages = state["messages"]
    if len(messages) > 1:
        return "summarize_conversation"
    return END


# conditional edge
def should_send_summary_email(state: State):
    """
    """
    messages = state["messages"]
    if len(messages) > 5:
        return "send_email"
    return END




if __name__ == "__main__":

    # email_template
    email_template = {}
    email_template["to"] = 'aneesh.reddy@terralogic.com'
    email_template["subject"] = "Conversation Summary and others"


    # preparing graph
    # create summary sub-graph
    gmail_tool = SendGmailTool(llm, email_template)
    gmail_subgraph = gmail_tool.build_email_tool_graph()
    
    workflow = StateGraph(State)
    # create nodes
    workflow.add_node("chatbot_with_summary", chatbot_with_summary)
    workflow.add_node("summarize_conversation", summarize_conversation)
    workflow.add_node("send_email", send_email)

    # create edges
    workflow.add_edge(START, "chatbot_with_summary")
    workflow.add_conditional_edges("chatbot_with_summary", should_summarize)
    workflow.add_conditional_edges("chatbot_with_summary", should_send_summary_email)
    workflow.add_edge("summarize_conversation", END)
    workflow.add_edge("send_email", END)

    # compile
    memory = MemorySaver()
    graph = workflow.compile(checkpointer=memory)
    # display(Image(graph.get_graph().draw_mermaid_png())
            
    with open("subgraph.png", "wb") as png:
        png.write(graph.get_graph(xray=1).draw_mermaid_png())


"""

    config = {"configurable": {"thread_id": "1"}}

    while True:
        user_input = input("User: ")
        if user_input == "done":
            break
        user_input = HumanMessage(content=user_input)
        output = graph.invoke({"messages": [user_input]}, config)
        # print("=====raw messages====")
        # print(messages)
        # print("===raw ends===")
        for m in output['messages']:
            m.pretty_print()

        print("conversation summary")
        print(graph.get_state(config).values.get("summary",""))
        """