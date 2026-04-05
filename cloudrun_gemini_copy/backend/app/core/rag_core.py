import csv
import os
import shutil

import chromadb
from dotenv import load_dotenv
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.retrievers.contextual_compression import ContextualCompressionRetriever
from langchain.retrievers.document_compressors.cross_encoder_rerank import CrossEncoderReranker
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

client = None
vectorstore = None
conversational_chain = None
reranker_model = None
vector_db_path = os.getenv('VECTOR_DB_PATH', '/app/local_chroma_db')
collection_name = os.getenv('CHROMA_COLLECTION_NAME', 'langchain')

rag_prompt = '''
## ROLE & GOAL ##
You are an expert assistant for question-answering tasks.
Your task is to answer the user's question based ONLY on the provided context.

Read the retrieved context carefully and use them to construct your answer.

### IMPORTANT INSTRUCTIONS ###
- Answer the question using ONLY the information found in the context below.
- If the context does not contain the information needed to answer the question, you MUST say "I'm sorry, the provided documents do not contain the answer to that question."
- DO NOT use any of your pre-existing knowledge or any external information.
- Keep your answer concise.
'''

print('Initializing local embedding model...')
embeddings = HuggingFaceEmbeddings(
    model_name='all-MiniLM-L6-v2',
    model_kwargs={'device': 'cpu'}
)
print('Embedding model loaded.')

print('Connecting to Google Gemini API...')
llm = ChatGoogleGenerativeAI(
    model=os.getenv('GEMINI_CHAT_MODEL', 'gemini-2.5-flash'),
    google_api_key=os.getenv('GOOGLE_API_KEY')
)
print('Gemini connected.')
print('LLM model loaded.')


def _split_documents(documents):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    return text_splitter.split_documents(documents)


def _get_store():
    global vectorstore
    if vectorstore is None:
        vectorstore = Chroma(
            client=client,
            collection_name=collection_name,
            embedding_function=embeddings,
        )
    return vectorstore


def _get_reranker_model():
    global reranker_model
    if reranker_model is None:
        print('Loading BGE reranker model...')
        reranker_model = HuggingFaceCrossEncoder(model_name='BAAI/bge-reranker-base')
        print('Reranker model loaded.')
    return reranker_model


def ingest_website(url: str):
    print(f'Loading content from website: {url}')
    loader = WebBaseLoader(url)
    documents = loader.load()

    for doc in documents:
        doc.metadata['source'] = url

    texts = _split_documents(documents)
    store = _get_store()
    store.add_documents(documents=texts)
    print(f'Added {len(texts)} website chunks to ChromaDB.')
    update_retriever()


def ingest_documents(file_path: str, source_name: str | None = None):
    print(f'Loading document: {file_path}')
    loader = PyPDFLoader(file_path)
    documents = loader.load()

    source_label = source_name or os.path.basename(file_path)
    for doc in documents:
        doc.metadata['source'] = source_label

    texts = _split_documents(documents)
    store = _get_store()
    store.add_documents(documents=texts)
    print(f'Added {len(texts)} PDF chunks to ChromaDB.')
    update_retriever()


def ingest_structured_data(file_path: str, source_name: str | None = None):
    print(f'Loading structured data from: {file_path}')
    documents = []
    source_label = source_name or os.path.basename(file_path)
    with open(file_path, mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            content = '. '.join([f'{key}: {value}' for key, value in row.items()])
            metadata = row.copy()
            metadata['source'] = source_label
            documents.append(Document(page_content=content, metadata=metadata))

    store = _get_store()
    store.add_documents(documents=documents)
    print(f'Added {len(documents)} CSV records to ChromaDB.')
    update_retriever()


def get_conversational_rag_chain(retriever):
    contextualize_q_system_prompt = '''Given a chat history and the latest user question
which might reference context in the chat history, formulate a standalone question
which can be understood without the chat history. Do NOT answer the question,
just reformulate it if needed and otherwise return it as is.'''
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ('system', contextualize_q_system_prompt),
            MessagesPlaceholder('chat_history'),
            ('human', '{input}'),
        ]
    )
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
    )

    qa_system_prompt = rag_prompt + 'Use the following pieces of retrieved context to answer the question.\n{context}'
    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ('system', qa_system_prompt),
            MessagesPlaceholder('chat_history'),
            ('human', '{input}'),
        ]
    )

    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
    return create_retrieval_chain(history_aware_retriever, question_answer_chain)


def initialize_database():
    global client, vectorstore, conversational_chain
    print(f'Initializing ChromaDB client at: {vector_db_path}')
    os.makedirs(vector_db_path, exist_ok=True)
    client = chromadb.PersistentClient(path=vector_db_path)
    vectorstore = Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings,
    )

    try:
        if vectorstore._collection.count() > 0:
            update_retriever()
            print('Existing Chroma collection restored.')
        else:
            conversational_chain = None
            print('Chroma collection is empty.')
    except Exception:
        conversational_chain = None
        print('Chroma collection not ready yet.')


def reset_database():
    global vectorstore, conversational_chain, client

    print('Resetting ChromaDB...')
    try:
        if client:
            client.reset()
    except Exception:
        shutil.rmtree(vector_db_path, ignore_errors=True)
        os.makedirs(vector_db_path, exist_ok=True)

    vectorstore = None
    conversational_chain = None
    initialize_database()
    print('Database reset successfully.')


def update_retriever():
    global conversational_chain, vectorstore

    if vectorstore is None:
        print('Vectorstore not initialized. Cannot update retriever.')
        return

    base_retriever = vectorstore.as_retriever(search_kwargs={'k': 10})
    compressor = CrossEncoderReranker(model=_get_reranker_model(), top_n=3)
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=base_retriever
    )
    conversational_chain = get_conversational_rag_chain(compression_retriever)
    print('Conversational chain updated with Re-ranker.')
