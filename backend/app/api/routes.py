from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
import shutil
import os
from typing import List, Tuple
from langchain_core.messages import HumanMessage, AIMessage
import traceback
import sys

# Import our new chain object
# from app.core.rag_core import *
from app.core import rag_core


router = APIRouter()

# MODIFIED: Pydantic model now includes chat_history
class ChatRequest(BaseModel):
    query: str
    # The history is a list of (human_message, ai_message) tuples
    chat_history: List[Tuple[str, str]] = []

class ChatResponse(BaseModel):
    answer: str
    source_documents: list

class WebsiteRequest(BaseModel):
    url: str

@router.post("/upload", status_code=201)
async def upload_document(file: UploadFile = File(...)):

    temp_file_path = f"temp_{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        if file.filename.lower().endswith(".pdf"):
            rag_core.ingest_documents(temp_file_path)
            return {"message": f"PDF '{file.filename}' ingested successfully."}
        elif file.filename.lower().endswith(".csv"):
            rag_core.ingest_structured_data(temp_file_path)
            return {"message": f"CSV '{file.filename}' ingested successfully."}
        else:
            print(f"Unsupported file type: {file.filename}")
            raise HTTPException(status_code=400, detail="Unsupported file type. Please upload a PDF or CSV.")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")
    finally:
        os.remove(temp_file_path)
@router.post("/chat")
async def chat_with_rag(request: ChatRequest):

    print(f"--- CHECKPOINT 2 [AT CHAT START] --- Type of conversational_chain is: {type(rag_core.conversational_chain)}")

    # --- START OF FIX ---
    # Add a check to see if the chain has been initialized
    if rag_core.conversational_chain is None:
        raise HTTPException(status_code=400, detail="No document has been uploaded yet. Please upload a document first.")
    # --- END OF FIX ---

    try:
        formatted_history = []
        for human, ai in request.chat_history:
            formatted_history.append(HumanMessage(content=human))
            formatted_history.append(AIMessage(content=ai))
        
        # This dictionary MUST contain the 'input' key
        invoke_payload = {
            "input": request.query,
            "chat_history": formatted_history
        }
        
        # Optional: Print the payload for debugging
        # print("Invoking chain with payload:", invoke_payload)
        
        result = rag_core.conversational_chain.invoke(invoke_payload)
        
        # The new chain returns context under the 'context' key
        sources = [{"content": doc.page_content, "metadata": doc.metadata} for doc in result['context']]
        
        return {
            "answer": result['answer'], 
            "sources": sources,
        }
    except Exception as e:
        print(f"Error during chat: {e}")
        # For better debugging, you might want to log the full traceback
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest-website", status_code=201)
async def ingest_website_endpoint(request: WebsiteRequest):
    """Endpoint to ingest data from a website URL."""
    try:
        rag_core.ingest_website(request.url)
        return {"message": f"Content from URL '{request.url}' ingested successfully."}
    except Exception as e:
        # For better debugging, you might want to log the full traceback
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to ingest website: {str(e)}")
    
@router.post("/reset", status_code=200)
async def reset_knowledge_base():
    """Endpoint to reset the knowledge base."""
    try:
        rag_core.reset_database()
        return {"message": "Knowledge base has been reset successfully."}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to reset database: {str(e)}")