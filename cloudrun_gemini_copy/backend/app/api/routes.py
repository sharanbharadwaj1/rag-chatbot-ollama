import os
import shutil
import traceback
from typing import List, Tuple
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

from app.core import rag_core

router = APIRouter()


class ChatRequest(BaseModel):
    query: str
    chat_history: List[Tuple[str, str]] = []


class ChatResponse(BaseModel):
    answer: str
    source_documents: list


class WebsiteRequest(BaseModel):
    url: str


@router.post('/upload', status_code=201)
async def upload_document(file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename or '')[1]
    temp_file_path = os.path.join('/tmp', f'{uuid4().hex}{suffix}')
    with open(temp_file_path, 'wb') as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        if file.filename.lower().endswith('.pdf'):
            rag_core.ingest_documents(temp_file_path, source_name=file.filename)
            return {'message': f"PDF '{file.filename}' ingested successfully."}
        elif file.filename.lower().endswith('.csv'):
            rag_core.ingest_structured_data(temp_file_path, source_name=file.filename)
            return {'message': f"CSV '{file.filename}' ingested successfully."}
        else:
            raise HTTPException(status_code=400, detail='Unsupported file type. Please upload a PDF or CSV.')
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f'Failed to process file: {str(e)}')
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@router.post('/chat')
async def chat_with_rag(request: ChatRequest):
    if rag_core.conversational_chain is None:
        raise HTTPException(status_code=400, detail='No document has been uploaded yet. Please upload a document first.')

    try:
        formatted_history = []
        for human, ai in request.chat_history:
            formatted_history.append(HumanMessage(content=human))
            formatted_history.append(AIMessage(content=ai))

        invoke_payload = {
            'input': request.query,
            'chat_history': formatted_history,
        }
        result = rag_core.conversational_chain.invoke(invoke_payload)
        sources = [{'content': doc.page_content, 'metadata': doc.metadata} for doc in result['context']]
        return {
            'answer': result['answer'],
            'sources': sources,
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/ingest-website', status_code=201)
async def ingest_website_endpoint(request: WebsiteRequest):
    try:
        rag_core.ingest_website(request.url)
        return {'message': f"Content from URL '{request.url}' ingested successfully."}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f'Failed to ingest website: {str(e)}')


@router.post('/reset', status_code=200)
async def reset_knowledge_base():
    try:
        rag_core.reset_database()
        return {'message': 'Knowledge base has been reset successfully.'}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f'Failed to reset database: {str(e)}')
