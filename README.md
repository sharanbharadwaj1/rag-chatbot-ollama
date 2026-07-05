# Advanced RAG Chatbot with Gemini and FastAPI along with Re Ranking Methods

This project is a complete, self-contained Retrieval-Augmented Generation (RAG) chatbot. It allows a user to upload a PDF document and ask questions about its content. The entire application, including the AI model, runs locally.

## ✨ Features

- **PDF Upload:** Ingest a PDF document to serve as the knowledge base.
- **Conversational Q&A:** Ask questions about the document in a conversational manner.
- **Chat History:** The chatbot remembers the context of the current conversation.
- **Source Display:** Shows the exact text chunks from the document used to generate the answer.
- **Dockerized:** The entire backend, including the LLM, is containerized for easy setup and portability.
- **ReRanking:** Re ranking the Source doucments for better retrieval of information. 

## 🛠️ Tech Stack

- **Backend:** FastAPI (Python)
- **AI/RAG Core:** LangChain
- **LLM Server:** Gemini 2.5 flash
- **Vector Database:** ChromaDB (local, file-based)
- **Containerization:** Docker, Docker Compose
- **Frontend:** Plain HTML, CSS, and JavaScript

##  Prerequisites

Before you begin, ensure you have the following installed on your system:

1.  **Git:** For cloning the repository.
2.  **Python:** Version 3.10 or higher.
3.  **Docker Desktop:** To run the containerized application.
4.  **Ollama:** (Required for non-Docker setup) The Ollama application must be installed and running.

---
# Gemini RAG Chatbot: Cloud Run Deployable Copy

This folder contains the Cloud Run deployable version of the original RAG chatbot. The goal of this copy was not to redesign the product from scratch, but to take an app that worked as a local project and adapt it into a containerized HTTP service that can run on Google Cloud Run with minimal behavior changes.

The resulting system keeps the original RAG flow:

- ingest PDFs, CSVs, and website content
- split content into chunks
- create embeddings locally with a Hugging Face model
- store embeddings in a persistent Chroma collection
- retrieve relevant chunks
- rerank retrieved chunks with BGE
- generate the final answer with Gemini

What changed is the deployment model, runtime wiring, and storage configuration needed to make the app work as a Cloud Run service.

## Purpose of This Copy

This version exists to answer a practical question:

How do we take a local RAG chatbot that depends on local files, local startup assumptions, and a local vector store, and make it deployable as a single Cloud Run container?

The conversion focused on:

- turning the app into a container-first service
- serving the frontend and backend from the same container
- replacing local-only assumptions with environment-driven configuration
- allowing Chroma persistence to survive container restarts
- making secrets deployment-safe
- keeping the code simple enough for learning, interviews, and prototype deployment

## What Stayed the Same

These core product behaviors were intentionally preserved:

- FastAPI application structure
- PDF ingestion through `PyPDFLoader`
- CSV ingestion through `csv.DictReader`
- website ingestion through `WebBaseLoader`
- chunking through `RecursiveCharacterTextSplitter`
- local embedding generation through `all-MiniLM-L6-v2`
- reranking through `BAAI/bge-reranker-base`
- answer generation through Gemini
- conversational retrieval with chat history awareness

In other words, this is still the same RAG chatbot. The main difference is that it now runs as a web container suitable for Cloud Run.

## What Changed for Cloud Run

The main conversion work was about deployment compatibility.

### 1. The app was packaged as a container

The backend now builds from [backend/Dockerfile](</E:/Projects/rag chatbot 7 10 2025/cloudrun_gemini_copy/backend/Dockerfile:1>).

That Dockerfile:

- uses `python:3.10-slim`
- installs system dependencies
- installs Python dependencies from `requirements.txt`
- copies the app code and frontend assets
- starts Uvicorn on port `8080`

This matters because Cloud Run expects a containerized HTTP service, not a local Python process with ad hoc startup steps.

### 2. The app now listens on Cloud Run's runtime port

Cloud Run injects a `PORT` environment variable at runtime. The container command uses:

```sh
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
```

That makes the service compatible with both:

- local Docker testing
- Cloud Run runtime expectations

### 3. The frontend is served from the same container

In [backend/app/main.py](</E:/Projects/rag chatbot 7 10 2025/cloudrun_gemini_copy/backend/app/main.py:1>), FastAPI:

- mounts static assets
- serves `index.html` at `/`
- serves API routes under `/api`

This makes deployment simpler because there is only one service:

- one container
- one public URL
- one deployment target

### 4. Vector store persistence became configurable

The biggest deployment issue in the original local style design is that Chroma uses a persistent folder. In Cloud Run, container local disk is ephemeral, so a restart can wipe locally written data.

To solve that, this version makes the persistence path configurable through:

- `VECTOR_DB_PATH`

In [backend/app/core/rag_core.py](</E:/Projects/rag chatbot 7 10 2025/cloudrun_gemini_copy/backend/app/core/rag_core.py:27>), Chroma uses:

```python
vector_db_path = os.getenv('VECTOR_DB_PATH', '/app/local_chroma_db')
```

and later:

```python
client = chromadb.PersistentClient(path=vector_db_path)
```

That means Chroma always writes to a filesystem path, but the actual storage behind that path can differ by environment.

### 5. Upload processing was made Cloud Run-friendly

Cloud Run provides writable temporary filesystem space, but that space is not durable. This version uses `/tmp` for short-lived uploaded files in [backend/app/api/routes.py](</E:/Projects/rag chatbot 7 10 2025/cloudrun_gemini_copy/backend/app/api/routes.py:26>).

The flow is:

- receive upload
- save to `/tmp`
- parse and ingest
- delete the temporary file

This is a good fit for containerized request handling because only intermediate upload files go to temp storage, while the vector store persists elsewhere.

### 6. Gemini credentials were externalized

Instead of hardcoding secrets, the app reads:

- `GOOGLE_API_KEY`

That allows the same container image to be reused across environments while injecting the API key securely at runtime, for example through Secret Manager in GCP.

### 7. CORS became configurable

This version introduced:

- `ALLOWED_ORIGINS`

so browser access can be controlled without code edits. That helps when moving from:

- local testing
- same-origin deployment
- restricted production origins

## Architecture

At a high level, the system looks like this:

```text
Browser UI
   |
   v
FastAPI app on Cloud Run
   |
   +--> /api/upload          -> parse PDF/CSV -> chunk -> embed -> store in Chroma
   +--> /api/ingest-website  -> load URL      -> chunk -> embed -> store in Chroma
   +--> /api/chat            -> retrieve -> rerank -> Gemini -> answer
   +--> /api/reset           -> reset persisted Chroma collection
   |
   v
Persistent Chroma store at VECTOR_DB_PATH
```

### Components

#### 1. FastAPI service

The FastAPI app in [backend/app/main.py](</E:/Projects/rag chatbot 7 10 2025/cloudrun_gemini_copy/backend/app/main.py:1>) is responsible for:

- startup initialization
- CORS configuration
- serving the frontend
- exposing the API routes
- running the health endpoint

#### 2. API layer

The route layer in [backend/app/api/routes.py](</E:/Projects/rag chatbot 7 10 2025/cloudrun_gemini_copy/backend/app/api/routes.py:1>) exposes four main operations:

- `POST /api/upload`
- `POST /api/ingest-website`
- `POST /api/chat`
- `POST /api/reset`

This keeps the transport layer thin. The route handlers mostly validate inputs, manage temp files, and call the RAG core functions.

#### 3. RAG core

The RAG logic lives in [backend/app/core/rag_core.py](</E:/Projects/rag chatbot 7 10 2025/cloudrun_gemini_copy/backend/app/core/rag_core.py:1>).

It handles:

- document loading
- text splitting
- embeddings
- Chroma initialization
- retriever creation
- reranker initialization
- conversational chain assembly
- vector store reset logic

#### 4. Embeddings layer

The system uses:

- `all-MiniLM-L6-v2`

through `HuggingFaceEmbeddings`.

This means embeddings are generated inside the running container and not outsourced to an external embedding API.

#### 5. Vector store layer

The vector store is Chroma with `PersistentClient`.

This is important to understand:

- Chroma writes to a filesystem path
- locally, that path can be a Docker-mounted host directory
- on Cloud Run, that same path can be backed by a mounted Cloud Storage bucket

So the app always believes it is writing to a local directory, even though the backing storage changes between environments.

#### 6. Reranker layer

The system uses:

- `BAAI/bge-reranker-base`

through `HuggingFaceCrossEncoder` and `CrossEncoderReranker`.

This reranks the initially retrieved chunks before they are passed into Gemini. The goal is to improve relevance and reduce noisy context.

#### 7. LLM layer

The answer generation model is configured through:

- `GEMINI_CHAT_MODEL`

and defaults to:

- `gemini-2.5-flash`

The LLM receives:

- the user question
- reformulated question context if needed
- chat history
- top reranked retrieved documents

## Workflow

The main workflows are document ingestion, website ingestion, chat, and startup restoration.

### Startup workflow

When the container starts:

1. FastAPI starts up.
2. `startup_event()` runs.
3. `rag_core.initialize_database()` is called.
4. Chroma is opened at `VECTOR_DB_PATH`.
5. If an existing collection is present, the retriever chain is rebuilt.
6. If the collection is empty, the app starts with no active conversational chain.

This is how the app restores previously indexed knowledge after a restart.

### PDF/CSV ingestion workflow

When a user uploads a document:

1. The file is received by `POST /api/upload`.
2. The file is written temporarily to `/tmp`.
3. The system checks the extension.
4. If PDF:
   - `PyPDFLoader` loads the document
   - each page is converted into LangChain documents
5. If CSV:
   - rows are converted into text records and metadata
6. Documents are split into chunks with:
   - `chunk_size=1000`
   - `chunk_overlap=200`
7. Each chunk is embedded locally.
8. The chunks are added to the Chroma collection.
9. The retriever chain is rebuilt.
10. The temp file is deleted.

### Website ingestion workflow

When a user submits a URL:

1. `POST /api/ingest-website` receives the URL.
2. `WebBaseLoader` downloads the content.
3. The content is converted into LangChain documents.
4. The source metadata is set to the URL.
5. The documents are chunked.
6. Chunks are embedded locally.
7. Chunks are stored in Chroma.
8. The retriever chain is rebuilt.

### Chat workflow

When a user asks a question:

1. `POST /api/chat` receives the query and chat history.
2. Chat history is converted into LangChain message objects.
3. The retrieval chain reformulates the latest question if needed.
4. Chroma retrieves the top candidate chunks.
5. The BGE reranker compresses and reranks them.
6. The final context is passed into Gemini.
7. Gemini generates the answer using only retrieved context.
8. The API returns:
   - answer text
   - supporting source chunks

### Reset workflow

When `POST /api/reset` is called:

1. The current Chroma data is reset.
2. The vector store is reinitialized.
3. The conversational chain is cleared and rebuilt as needed.

This is useful during demos and experimentation, but in a real production system it would need stronger access control.

## Why This Works on Cloud Run

Cloud Run works well for the HTTP service layer because this app is:

- packaged as a container
- served over HTTP
- started with a single process
- configured through environment variables

The Cloud Run friendly parts are:

- Dockerized service
- `PORT`-aware startup
- temporary file usage in `/tmp`
- secret-based API key injection
- frontend and backend unified in one service

## Why This Is Still a Prototype-Style Deployment

This version is deployable, but it is not a fully cloud-native production architecture yet.

The main compromise is the vector store:

- Chroma persists to a filesystem path
- Cloud Run itself is ephemeral
- so persistence is simulated by mounting external storage into that path

That is enough for a learning deployment or demo, but it creates scaling and consistency limitations.

### Important constraints

Deploy this copy with:

- `concurrency=1`
- `max-instances=1`

Those limits are intentional. They reduce the risk of multiple requests or multiple instances competing over a filesystem-backed Chroma store.

## Local vs Cloud Storage Behavior

This is one of the most important ideas in this project.

### Local Docker

In local Docker, Chroma writes to a path inside the container, for example:

```text
/mnt/chroma/local_chroma_db
```

Docker maps that path to a folder on your machine:

```text
./local_chroma_db
```

So from Chroma's perspective it is writing to a normal local directory.

### Cloud Run

In Cloud Run, Chroma still writes to a normal-looking directory path. The difference is that the path is backed by mounted external cloud storage.

So:

- the app sees a folder
- Chroma writes files into that folder
- the underlying storage is not the container's ephemeral disk

This is why the same code can work locally and in Cloud Run without changing the Chroma API calls.

## Deployment Resources

This Cloud Run copy includes:

- [deploy_cloudrun.ps1](</E:/Projects/rag chatbot 7 10 2025/cloudrun_gemini_copy/deploy_cloudrun.ps1:1>) for a helper deployment script
- [docker-compose.yml](</E:/Projects/rag chatbot 7 10 2025/cloudrun_gemini_copy/docker-compose.yml:1>) for local Docker testing
- [backend/.env.example](</E:/Projects/rag chatbot 7 10 2025/cloudrun_gemini_copy/backend/.env.example:1>) for example runtime configuration

## Environment Variables

This version uses the following key environment variables:

- `GOOGLE_API_KEY`: Gemini API key
- `VECTOR_DB_PATH`: persistent Chroma directory
- `CHROMA_COLLECTION_NAME`: Chroma collection name
- `GEMINI_CHAT_MODEL`: Gemini model identifier
- `ALLOWED_ORIGINS`: comma-separated browser origins for CORS
- `PORT`: runtime HTTP port provided by Cloud Run

## Endpoints

- `GET /`: frontend UI
- `GET /healthz`: health check
- `POST /api/upload`: ingest PDF or CSV
- `POST /api/ingest-website`: ingest website content
- `POST /api/chat`: ask questions against indexed knowledge
- `POST /api/reset`: reset the knowledge base

## Tradeoffs and Limitations

This deployment is intentionally practical rather than perfect.

### Strengths

- simple deployment model
- single service to run and test
- same container works locally and in Cloud Run
- keeps the original RAG behavior mostly unchanged
- good for demos, learning, and interview discussion

### Limitations

- filesystem-backed Chroma is not ideal for horizontal scaling
- startup may be slow because local models initialize inside the container
- multiple writers are risky
- `reset` should not be exposed publicly in a serious production setup
- upload and ingestion are synchronous request-time operations

## Recommended Next Upgrade

If this system needs to become properly production-grade, the first major redesign should be the vector store layer.

Recommended direction:

- replace filesystem-backed Chroma with a managed vector database
- on GCP, `pgvector` on Cloud SQL is a strong next step

That upgrade would allow:

- safer concurrent access
- cleaner scaling behavior
- removal of the mounted-filesystem compromise
- a more cloud-native production architecture

After that, the next improvements would be:

- async ingestion jobs
- stronger authentication and authorization
- structured logging and monitoring
- tighter CORS and API security
- better rollout and rollback controls

## Summary

This Cloud Run copy is best understood as a deployment adaptation layer around the existing RAG chatbot.

It did not change the core user-facing product. Instead, it changed the operational shape of the application so it could be:

- built as a container
- run as a web service
- configured by environment
- connected to persistent storage
- deployed to Cloud Run with minimal code disruption

That makes it a strong prototype deployment and a useful bridge between local RAG development and cloud-hosted serving.
............................
## 🚀 Running the Application (Recommended Method: Docker)

This is the simplest and most reliable way to run the entire application.

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/YourUsername/YourRepoName.git](https://github.com/YourUsername/YourRepoName.git)
    cd YourRepoName
    ```

2.  **Ensure Docker Desktop is Running.**

3.  **Build and Run the Container:**
    From the project's root directory, run the following command. This will build the Docker image (which includes Pythonband all dependencies) and start the service.
    ```bash
    docker-compose up --build
    ```
    The first build will take several minutes. Subsequent starts will be much faster.

4.  **Start the Frontend:**
    The backend is now running inside Docker on port 8000. To see the UI, you still need to serve the frontend files. Open a **new, separate terminal**, navigate to the `frontend` directory, and run:
    ```bash
    python -m http.server 8081
    ```

5.  **Access the Chatbot:**
    Open your web browser and navigate to:
    **`http://localhost:8081`**

## 🛑 Stopping the Application

-   To stop the frontend server, press `Ctrl+C` in its terminal.
-   To stop the backend Docker container, run the following command from the project's root directory:
    ```bash
    docker-compose down
    ```

---

## 🔧 Local Setup (Without Docker)

This method requires manually managing the backend, frontend, and Ollama servers in separate terminals.

1.  **Backend Setup:**
    ```bash
    cd backend
    python -m venv venv
    # Activate the virtual environment
    # Windows:
    .\venv\Scripts\activate
    # Mac/Linux:
    source venv/bin/activate
    pip install -r requirements.txt
    # Run the backend server
    uvicorn app.main:app --host 0.0.0.0 --port 8000
    ```

2.  **Frontend Setup (in a new terminal):**
    ```bash
    cd frontend
    python -m http.server 8081
    ```





Your Goal	                Command to Run
Start the application	    docker-compose up -d
Stop the application	    docker-compose down
Start after changing code	docker-compose up --build
