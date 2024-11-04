import requests
from bs4 import BeautifulSoup
from typing import Optional,Dict,List
from langchain_core.tools import tool, BaseTool
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import MessagesState
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from src.all_prompts import job_params_template


class Job(BaseModel):
    jobtype: str = Field(description="The job role specified by the user")
    location: str = Field(description="The location at which the user is looking for jobs")


class CareerToolNode:
    """search for available jobs on career website based on jobtype and location and should provide the link"""

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
        self.jobtype = job_params['jobrole']
        self.location = job_params['location']

    def _run_search_jobs(self, state: MessagesState):

        messages = state['messages']
        question = messages[-1].content
        self.extract_job_params(question)
        if self.jobtype == "" and self.location == "":
            user_input = input('Are you looking for a specific job role in a specific location?')
            messages = state['messages'] + [HumanMessage(content=user_input)]
            question = messages[-1].content
            self.extract_job_params(question)

        try:
            response = requests.get(self.url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            job_elements = soup.find_all('div', class_='job-title')
                
            jobs = []
            for index, job_element in enumerate(job_elements, start=1):
                # Extract job title
                title_element = job_element.find('h6', class_='job-title__heading')
                title = title_element.text.strip() if title_element else 'N/A'
                
                # Extract job location
                location_element = job_element.find('span', class_='job-location')
                loc = location_element.text.strip() if location_element else 'N/A'
                
                # Extract the application link
                link_element = title_element.find_parent('a')  
                link = link_element['href'].strip() if link_element and 'href' in link_element.attrs else 'N/A'

                # Filter based on job type and location
                if self.jobtype and self.jobtype.lower() not in title.lower():
                    continue  

                if self.location and self.location.lower() not in loc.lower():
                    continue  
                
                jobs.append(f"Title: {title}\nLocation: {loc}\nApply here: {link}\n")

            if jobs:
                message = "\n".join(jobs)
            else:
                message = "No matching job openings found."
        
        except requests.RequestException as e:
            message = f"Error fetching the jobs: {e}"

        ai_response = AIMessage(content=message)
        return {'messages':[ai_response]}
    

if __name__ == "__main__":
    career_page_url = "https://terralogic.com/careers/"
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=os.getenv("GOOGLE_API_KEY"))
    tool_obj = CareerToolNode(career_page_url, llm)