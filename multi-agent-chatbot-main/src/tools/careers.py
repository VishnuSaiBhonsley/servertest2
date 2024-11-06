import sys
import os
sys.path.append(os.getcwd())

import requests
from bs4 import BeautifulSoup
from typing import Optional,Dict,List
from langchain_core.tools import tool, BaseTool
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import MessagesState
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

from src.all_prompts import job_params_template



class Job(BaseModel):
    jobtype: str = Field(description="The job role specified by the user")
    location: str = Field(description="The location at which the user is looking for jobs")


from bs4 import BeautifulSoup
import requests

class CareerToolNode:
    """Search for available jobs on a career website based on job type and location, providing the link."""

    def __init__(self, url, llm):
        self.jobtype = ""
        self.location = ""
        self.url = url
        self.llm = llm
        self.structured_llm = self.llm.with_structured_output(Job)
        self.career_llm = self.define_career_llm()

    def define_career_llm(self):
        prompt = PromptTemplate(
            template=job_params_template,
            input_variables=["question"],
        )
        chain = prompt | self.llm | JsonOutputParser()
        return chain

    def extract_job_params(self, message):
        job_params = self.career_llm.invoke({"question": message})
        self.jobtype = job_params.get('jobrole', "")
        self.location = job_params.get('location', "")

    def _run_search_jobs(self, state: MessagesState):
        messages = state['messages']
        question = messages[-1].content
        self.extract_job_params(question)
        
        if not self.jobtype and not self.location:
            user_input = input('Are you looking for a specific job role in a specific location? \nIf "Yes" please specify job role or/and location:')
            messages = state['messages'] + [HumanMessage(content=user_input)]
            question = messages[-1].content
            self.extract_job_params(question)

        try:
            response = requests.get(self.url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            job_elements = soup.find_all('li', class_='open-ticket-list__item')
                
            jobs = []
            for job_element in job_elements:
                # Extract job title
                title_element = job_element.find('h6', class_='fnt-18 clr-white fnt-600 m-0')
                title = title_element.text.strip() if title_element else 'N/A'

                # Extract job location
                location_element = job_element.find('span', class_='d-inline-block fnt-400 fnt-14 clr-white text-right')
                loc = location_element.text.strip() if location_element else 'N/A'

                # Extract the application link
                link_element = job_element.find('a', class_='d-flex')
                link = link_element['href'].strip() if link_element else 'N/A'

                # Filter based on job type and location
                if self.jobtype and self.jobtype.lower() not in title.lower():
                    continue
                if self.location and self.location.lower() not in loc.lower():
                    continue
                
                jobs.append(f"Title: {title}\nLocation: {loc}\nApply here: {link}\n")

            message = "\n".join(jobs) if jobs else "No matching job openings found."
        
        except requests.RequestException as e:
            message = f"Error fetching the jobs: {e}"

        ai_response = AIMessage(content=message)
        return {'messages': [ai_response]}
    

    

if __name__ == "__main__":
    career_page_url = "https://lollypop.design/careers/"
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=os.getenv("GOOGLE_API_KEY"))
    tool_obj = CareerToolNode(career_page_url, llm)

    while True:
        user_input = input("Human Message:")
        if 'bye' in user_input:
            print('Thank you for contacting LP. Have a nice day!')
            break
        inputs = {
            "messages": [
                HumanMessage(user_input)
            ]
        }
        output = tool_obj._run_search_jobs(inputs)
        print("AI message: ", output['messages'][-1].content)
