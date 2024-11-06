import os
import re
import json
import numpy as np
import fitz
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from docx import Document
from docx.oxml.ns import qn

# Paths for the cached files
ROOT_DIR = "Data"
PDF_PATH = f'{ROOT_DIR}/faq_data/Lollypop_Design_FAQS.pdf'
EMBEDDINGS_PATH = f'{ROOT_DIR}/faq_data/faq_embeddings.npz'
FAQ_JSON_PATH = f'{ROOT_DIR}/faq_data/faqs_from_pdf.json'


class SearchNode:
    
    def __init__(self, pdf_path, embeddings_path, faq_json_path) -> None:
        self.embed_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.pdf_path = pdf_path
        self.embeddings_path = embeddings_path
        self.faq_json_path = faq_json_path
        self.faqs = None
        self.faq_embeddings = None
        
    def embed_sentences(self, sentences):
        """
        Embed a list of sentences using the SentenceTransformer model.
        """
        return self.embed_model.encode(sentences)
    
    def extract_text_from_pdf_pymupdf(self):
        """
        Extract text from a PDF file using pdfplumber.
        """
        doc = fitz.open(self.pdf_path)
        pages = [page.get_text() for page in doc]
        return pages

    def split_pdf_text_into_faqs_multiline(self, pdf_text):
        """
        Split the extracted PDF text into a list of FAQ entries, handling multi-line questions and answers.
        """
        faqs = []
        current_faq = {"question": "", "answer": ""}
        question_lines = []
        collecting_question = False

        for page in pdf_text:
            lines = page.split('\n')
            for line in lines:
                if 'https' in line or 'FAQ' in line:
                    continue
                line = line.strip()
                
                # Use regex to detect question patterns and remove numbering
                match = re.match(r"(?:\d+\.\s*)?(What|How|Why|When|Which|Where|Do|Does|Is)\b(.+)", line, re.IGNORECASE)
                if match:
                    question_text = match.group(1) + match.group(2)  # Extract matched question without numbering
                    
                    # If there is a previous FAQ entry, save it first
                    if current_faq["question"] and current_faq["answer"]:
                        faqs.append(current_faq)
                        current_faq = {"question": "", "answer": ""}
                    
                    # Check if question spans multiple lines
                    if not line.endswith('?'):
                        question_lines.append(question_text)
                        collecting_question = True
                    else:
                        current_faq = {"question": question_text.strip(), "answer": ""}
                        collecting_question = False
                elif collecting_question:
                    question_lines.append(line)
                    if line.endswith('?'):
                        # Join collected lines to form the full question
                        question = " ".join(question_lines).strip()
                        current_faq = {"question": question, "answer": ""}
                        question_lines = []
                        collecting_question = False
                else:
                    if not current_faq["question"]:
                        continue
                    current_faq["answer"] += line.strip() + " "

        # Append last FAQ if it has both question and answer
        if current_faq["question"] and current_faq["answer"]:
            faqs.append(current_faq)

        return faqs

    def load_faq_data(self):
        """
        Load FAQs and embeddings from precomputed files if available.
        Otherwise, extract from PDF and compute embeddings.
        """

        if os.path.exists(self.embeddings_path) and os.path.exists(self.faq_json_path):
            # Load precomputed FAQs and embeddings
            with open(self.faq_json_path, 'r') as f:
                self.faqs = json.load(f)
            data = np.load(self.embeddings_path)
            self.faq_embeddings = data['faq_embeddings']
            print("Loaded precomputed FAQs and embeddings.")
        else:
            # Extract text from PDF and compute embeddings
            print("Extracting text from PDF...")
            pdf_text = self.extract_text_from_pdf_pymupdf()
            self.faqs = self.split_pdf_text_into_faqs_multiline(pdf_text)
            
            with open(self.faq_json_path, 'w') as f:
                json.dump(self.faqs, f, indent=4)
            
            print("Computing embeddings...")
            faq_questions = [faq["question"] for faq in self.faqs]
            self.faq_embeddings = self.embed_sentences(faq_questions)
            
            np.savez(self.embeddings_path, faq_embeddings=self.faq_embeddings)
            print("FAQs and embeddings saved.")

    def faq_search(self, user_question, top_n=4, mode='cosine'):
        """
        Perform semantic search between the user question and the FAQs.
        """
        user_embedding = self.embed_sentences([user_question])

        if mode == 'cosine':
            similarities = cosine_similarity(user_embedding, self.faq_embeddings)[0]
            top_indices = np.argsort(similarities)[-top_n:][::-1]
            top_faqs = [self.faqs[i] for i in top_indices]
            top_scores = [similarities[i] for i in top_indices]

        return top_faqs, top_scores

# Load FAQ data on startup
search_obj = SearchNode(PDF_PATH, EMBEDDINGS_PATH, FAQ_JSON_PATH)
search_obj.load_faq_data()

# Example usage
if __name__ == "__main__":
    user_query = "What is UX Research?"
    top_faqs, top_scores = search_obj.faq_search(user_query)

    print("**********************************")
    print("User Query: ", user_query)
    print("**********************************")
    for idx, faq in enumerate(top_faqs):
        print(f"Top {idx + 1}:\nQ: {faq['question']}\nA: {faq['answer']}\nScore: {top_scores[idx]}\n")
