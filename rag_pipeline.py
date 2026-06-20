import os
import numpy as np
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from google import genai
from groq import Groq

load_dotenv()

# Gemini client for embeddings only
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Groq client for LLM
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def load_resumes(pdf_paths):
    all_docs = []
    for path in pdf_paths:
        loader = PyPDFLoader(path)
        docs = loader.load()
        for doc in docs:
            doc.metadata["source"] = os.path.basename(path)
        all_docs.extend(docs)
    return all_docs

def chunk_documents(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    return splitter.split_documents(docs)

class GeminiEmbeddings:
    def __call__(self, text):
        return self.embed_query(text)
    
    def embed_documents(self, texts):
        embeddings = []
        for text in texts:
            result = gemini_client.models.embed_content(
                model="gemini-embedding-001",
                contents=text
            )
            embeddings.append(result.embeddings[0].values)
        return embeddings

    def embed_query(self, text):
        result = gemini_client.models.embed_content(
            model="gemini-embedding-001",
            contents=text
        )
        return result.embeddings[0].values

def create_vector_store(chunks):
    embeddings = GeminiEmbeddings()
    texts = [chunk.page_content for chunk in chunks]
    metadatas = [chunk.metadata for chunk in chunks]
    vector_store = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
    return vector_store

def query_screener(question, vector_store):
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})
    relevant_docs = retriever.invoke(question)
    
    context = "\n\n".join([
        f"[From: {doc.metadata['source']}]\n{doc.page_content}"
        for doc in relevant_docs
    ])
    sources = list(set([doc.metadata["source"] for doc in relevant_docs]))
    
    chat = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{
            "role": "user",
            "content": f"""You are an expert HR recruiter and resume screener.
Based on the following resume content, answer the question clearly.
Always mention candidate names and specific skills in your answer.

Resume Content:
{context}

Question: {question}

Give a structured, clear answer."""
        }]
    )
    
    return chat.choices[0].message.content, sources