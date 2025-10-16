import os
import shutil
import chromadb # NEW IMPORT

from langchain_community.llms import Ollama
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader,WebBaseLoader # <-- Add WebBaseLoader

from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# from app.core.prompts import rag_prompt

import csv # <-- ADD THIS
from langchain_core.documents import Document

# --- Initialize Core Components ---
# vector_db_path = "local_chroma_db"
# client = chromadb.PersistentClient(path=vector_db_path)
client = None
vectorstore = None
conversational_chain = None
# embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vector_db_path = "local_chroma_db"

rag_prompt = '''
"""
 ## ROLE & GOAL ##
You are an expert assistant for question-answering tasks.
Your task is to answer the user's question based ONLY on the provided context.

Read the retrieved context carefully and use them to construct your answer.

### IMPORTANT INSTRUCTIONS ###

- Answer the question using ONLY the information found in the context below.
- If the context does not contain the information needed to answer the question, you MUST say "I'm sorry, the provided documents do not contain the answer to that question."
- DO NOT use any of your pre-existing knowledge or any external information.
- Keep your answer concise.

### CORE INSTRUCTIONS ###
1.  **Grounding:** Your entire response MUST be based solely on the information contained within the `## Context ##` provided below. Do not add information that is not present in the text.
2.  **Synthesis:** Do not just extract and repeat verbatim chunks of text. Synthesize the relevant information from one or more parts of the context into a coherent and easy-to-understand answer.
3.  **No Information Case:** If the context does not contain any relevant information to answer the query, you MUST respond with: "I'm sorry, but I could not find the information to answer your question in the provided documents." Do not try to guess or infer an answer.
4.  **Citation:** When you provide an answer, you MUST cite the source of the information. Use the identifier provided with each context snippet (e.g., `[Source: doc1, page 4]`). If multiple sources are used to formulate the answer, cite all of them.

### STYLE & TONE ###
-   Maintain a professional, neutral, and helpful tone.
-   Use clear and direct language.
-   Structure answers with bullet points or numbered lists if it improves clarity, especially for multi-part questions.

###Example###


**User Input: "What are the main benefits of using renewable energy sources?"
  Answer:"Renewable energy sources offer ....."

**User Input: " ok"
  Answer: "I'm sorry, but I could not find anyhting relevant, let me know what you want to do next."

---

## Answer ##
"""

'''
print("Initializing local embedding model...")
embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2",
    model_kwargs={'device': 'cpu'}
)
print("✅ Embedding model loaded.")

# llm = Ollama(model="gemma:2b")
# llm = Ollama(model="tinyllama")
llm = Ollama(model="gemma:2b-instruct-q4_0") # Use the quantized model



print("✅ LLM model loaded.")

# IMPORTANT: Initialize global variables to None.
# This prevents a file lock on application startup.
vectorstore = None
conversational_chain = None

def ingest_website(url: str):
    """
    Loads data from a website URL, splits it into chunks, and ADDS it to the
    persistent vector store.
    """
    global vectorstore, conversational_chain

    print(f"Loading content from website: {url}")
    loader = WebBaseLoader(url)
    documents = loader.load()
    
    # Add the source metadata to each document chunk
    for doc in documents:
        doc.metadata["source"] = url

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = text_splitter.split_documents(documents)
    
    print(f"Adding {len(texts)} new document chunks from the website to ChromaDB...")

    # Same logic as ingest_documents to add to the existing store
    if vectorstore:
        vectorstore.add_documents(documents=texts)
    else:
        # This will likely not be hit if a PDF is uploaded first, but it's good practice
        vectorstore = Chroma.from_documents(
            documents=texts, 
            embedding=embeddings,
            client=client,
            collection_name="langchain"
        )
    
    print("✅ Website content added successfully!")

    # Update the conversational_chain to use the retriever with the new data
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    conversational_chain = get_conversational_rag_chain(retriever)
    print("✅ Conversational chain has been updated with the new retriever.")

def ingest_documents(file_path: str):
    """
    Loads a PDF, splits it into chunks, and ADDS it to the
    persistent vector store without deleting previous content.
    """
    global vectorstore, conversational_chain

    # --- NO DELETION LOGIC HERE ---
    # We will only add to the existing database.

    # 1. Load and process the new document
    print(f"Loading document: {file_path}")
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    
    for doc in documents:
        doc.metadata["source"] = os.path.basename(file_path)

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = text_splitter.split_documents(documents)
    
    print(f"Adding {len(texts)} new document chunks to ChromaDB...")

    # 2. Check if the vectorstore object exists in memory
    if vectorstore:
        # If it exists, just add the new documents
        vectorstore.add_documents(documents=texts)
    else:
        # If it's the first run, create the vectorstore from scratch
        vectorstore = Chroma.from_documents(
            documents=texts, 
            embedding=embeddings,
            client=client,
            collection_name="langchain"
        )
    
    print("✅ Documents added successfully!")

    # 3. Update the conversational_chain to use the retriever with the new data
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    conversational_chain = get_conversational_rag_chain(retriever)
    print("✅ Conversational chain has been updated with the new retriever.")
    print(f"--- CHECKPOINT 1 [AFTER INGEST] --- Type of conversational_chain is: {type(conversational_chain)}")



def get_conversational_rag_chain(retriever):
    contextualize_q_system_prompt = """Given a chat history and the latest user question \
    which might reference context in the chat history, formulate a standalone question \
    which can be understood without the chat history. Do NOT answer the question, \
    just reformulate it if needed and otherwise return it as is."""
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", rag_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
    )

    # qa_system_prompt = """You are an assistant for question-answering tasks. \
    # Use the following pieces of retrieved context to answer the question. \
    # If you don't know the answer, just say that you don't know. \
    # Keep the answer concise.

    qa_system_prompt =  rag_prompt + """Use the following pieces of retrieved context to answer the question. 
    {context}"""
    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system",qa_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )

    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
    
    return rag_chain


def ingest_structured_data(file_path: str):
    """
    Dynamically loads data from any CSV file, formats each row into a sentence,
    and ADDS it to the persistent vector store.
    """
    global vectorstore, conversational_chain
    
    print(f"Loading structured data from: {file_path}")
    documents = []
    with open(file_path, mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Dynamically create a sentence from all columns in the row
            content = ". ".join([f"{key}: {value}" for key, value in row.items()])
            
            # Create a metadata dictionary from the row's data
            metadata = row.copy()
            metadata["source"] = os.path.basename(file_path)

            doc = Document(page_content=content, metadata=metadata)
            documents.append(doc)

    print(f"Adding {len(documents)} new records from CSV to ChromaDB...")
    
    if vectorstore:
        vectorstore.add_documents(documents=documents)
    else:
        vectorstore = Chroma.from_documents(
            documents=documents, 
            embedding=embeddings,
            client=client,
            collection_name="langchain"
        )
    
    print("✅ Structured data added successfully!")

    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    conversational_chain = get_conversational_rag_chain(retriever)
    print("✅ Conversational chain has been updated.")


def initialize_database():
    """Initializes the ChromaDB client."""
    global client
    print("Initializing ChromaDB client...")
    client = chromadb.PersistentClient(path=vector_db_path)
    print("✅ ChromaDB client initialized.")

def reset_database():
    """
    Deletes the vector store from disk and resets the in-memory state.
    """
    global vectorstore, conversational_chain, client
    
    # Reset in-memory variables
    vectorstore = None
    conversational_chain = None
    client = None # Reset client to ensure clean state
    
    # Delete the on-disk database
    if os.path.exists(vector_db_path):
        print(f"Deleting vector database at: {vector_db_path}")
        shutil.rmtree(vector_db_path)
    
    # Re-initialize to create a fresh, empty state
    os.makedirs(vector_db_path, exist_ok=True)
    initialize_database()
    print("✅ Database reset successfully.")

# Also, call initialize_database() once when the module is first loaded
initialize_database()