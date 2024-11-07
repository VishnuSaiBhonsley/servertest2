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

"""

This module requires credentials.json to be placed in the working directory.
Follow- https://developers.google.com/gmail/api/quickstart/python for the creation and enablement.

"""

class InputState(TypedDict):
    mail_content: str

class OutputState(TypedDict):
    sent_status: str

class OverallState(TypedDict):
    mail_content: str
    sent_status: str



class SendGmailTool:
    def __init__(self, llm, email_template):
        self.llm = llm
        self.tools = [self.send_email_message_tool]
        self.tool_node = ToolNode(self.tools)
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.email_template = email_template
    
        gmail_toolkit = GmailToolkit()
        gmail_tools = gmail_toolkit.get_tools()
        self.send_email_tool = next(tool for tool in gmail_tools if tool.name == "send_gmail_message")


    def send_email_message_tool(self, mail_content: str):
        """
        Send given mail content as email to a Gmail account.

        Args:
            mail_content: message content of the email

        """
        self.email_template["message"] = mail_content
        print(self.email_template)

        try:
            status_message = self.send_email_tool.invoke(self.email_template)
            status = {"status_code": 200, "status_message": status_message}
            print(status)
        except Exception as e:
            status = {"status_code": 500, "status_message": e}
            print(f"Failed to send. Error: {str(e)}")
     
        return status


    def send_email_message(self, state):
        """
        Send email with the given message, body to the recipient.
        """
        sys_msg = SystemMessage(content="You are helpful agent tasked with sending mail for the given message content")
        response = self.llm_with_tools.invoke([sys_msg] + state["messages"])
        return {"messages": response}
    

    
    def prepare_mail_call(self, messages: InputState) -> OutputState:
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
        response = self.tool_node.invoke({"messages": [message_with_single_tool_call]})
        print("After sending email\n", response)
        response = eval(response["messages"][0].content)
        print("sending status")
        return {"sent_status": response}
   


    def build_email_tool_graph(self):            
        builder = StateGraph(OverallState, input=InputState, output=OutputState)
        builder.add_node("prepare_mail_call", self.prepare_mail_call)

        builder.add_edge(START, "prepare_mail_call")
        builder.add_edge("prepare_mail_call", END)
        graph = builder.compile()
        return graph


if __name__ == "__main__":
    email_template = {}
    email_template["to"] = 'shashank.holla@terralogic.com'
    email_template["subject"] = "Conversation Summary and others"

    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)
    gmail_tool = SendGmailTool(llm, email_template)

    graph = gmail_tool.build_email_tool_graph()
    messages = HumanMessage(content="Will this thing work?")
    messages = graph.invoke({"mail_content": messages})
    print("----------------------")
    print(messages)

   



