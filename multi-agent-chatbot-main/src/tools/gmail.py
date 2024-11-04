from langchain_google_community import GmailToolkit
from langchain_google_genai import ChatGoogleGenerativeAI

from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from langgraph.graph import START, StateGraph, END
from langgraph.prebuilt import tools_condition
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

import os
from dotenv import load_dotenv

load_dotenv()


class InputState(TypedDict):
    mail_content: str

class OutputState(TypedDict):
    sent_status: str


class OverallState(TypedDict):
    mail_content: str
    sent_status: str


email_template = {}
email_template["to"] = 'shashank.holla@terralogic.com'
email_template["subject"] = "Conversation Summary and others"

gmail_toolkit = GmailToolkit()
gmail_tools = gmail_toolkit.get_tools()
send_email_tool = next(tool for tool in gmail_tools if tool.name == "send_gmail_message")


def send_email_message_tool(mail_content: str):
    """
    Send given mail content as email to a Gmail account.

    Args:
        mail_content: message content of the email

    """
    email_template["message"] = mail_content
    print(email_template)

    try:
        status_message = send_email_tool.invoke(email_template)
        status = {"status_code": 200, "status_message": status_message}
        print(status)
    except Exception as e:
        status = {"status_code": 500, "status_message": e}
        print(f"Failed to send. Error: {str(e)}")
    
    return status



tools = [send_email_message_tool]
tool_node = ToolNode(tools)



def prepare_mail_call(messages: InputState) -> OutputState:
    message_with_single_tool_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "send_email_message_tool",
                "args": {"mail_content": messages["mail_content"].content},
                "id": "email_sender",
                "type": "tool_call",
            }
        ],
    )
    response = tool_node.invoke({"messages": [message_with_single_tool_call]})
    print("After sending email\n", response)
    response = eval(response["messages"][0].content)
    print("sending status")
    return {"sent_status": response}


messages = HumanMessage(content="Monday message")
# print(prepare_mail_call({"mail_content": messages}))

# building graph
builder = StateGraph(OverallState, input=InputState, output=OutputState)
builder.add_node("prepare_mail_call", prepare_mail_call)
# builder.add_node("email_tool", ToolNode(tools))

builder.add_edge(START, "prepare_mail_call")
builder.add_edge("prepare_mail_call", END)
# builder.add_edge("prepare_mail_call", "email_tool")
# builder.add_edge("email_tool", END)
graph = builder.compile()
response = graph.invoke({"mail_content": messages})

print("response captured")
print(response)

