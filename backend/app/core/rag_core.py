import os
import shutil
import chromadb # NEW IMPORT

from langchain_community.llms import Ollama
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# from app.core.prompts import rag_prompt
# --- Initialize Core Components ---
vector_db_path = "local_chroma_db"
client = chromadb.PersistentClient(path=vector_db_path)


rag_prompt = '''
"""
 ## ROLE & GOAL ##
You are an advanced AI assistant specializing in information retrieval and synthesis. Your primary goal is to provide accurate, concise, and helpful answers to user queries by synthesizing information exclusively from the provided context. You are forbidden from using any prior knowledge or information outside of this context.

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


def ingest_documents(file_path: str):
    global vectorstore, conversational_chain

    # 1. Release any existing objects holding a file lock.
    # 1. Clear out the old data using the ChromaDB client
    try:
        # LangChain's default collection name is "langchain"
        print("Deleting existing collection: langchain")
        client.delete_collection(name="langchain")
    except ValueError:
        print("Collection 'langchain' not found, skipping deletion.")
        pass # Collection doesn't exist on the first run, which is fine
    except chromadb.errors.NotFoundError:
        print("Collection 'langchain' did not exist. Skipping deletion.")
        pass # If the collection doesn't exist, that's fine. We just continue.
    except Exception as e:
        print(f"An unexpected error occurred during collection deletion: {e}")
        raise
    
    # 3. Load and process the new document.
    print(f"Loading document: {file_path}")
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = text_splitter.split_documents(documents)
    
    print("Ingesting documents into ChromaDB...")
    
    # 4. Create and assign the new vectorstore.
    # 3. Create a new vector store with the new documents
    vectorstore = Chroma.from_documents(
        documents=texts, 
        embedding=embeddings,
        client=client, # Use the persistent client
        collection_name="langchain" # Specify the collection name
    )
    # vectorstore.persist()
    print("✅ Documents ingested and persisted successfully!")

    # 5. Create and assign the new conversational_chain.
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    conversational_chain = get_conversational_rag_chain(retriever)
    print("✅ Conversational chain has been updated with the new document retriever.")

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