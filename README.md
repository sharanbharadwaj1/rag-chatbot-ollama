# Local RAG Chatbot with Ollama and FastAPI

This project is a complete, self-contained Retrieval-Augmented Generation (RAG) chatbot. It allows a user to upload a PDF document and ask questions about its content. The entire application, including the AI model, runs locally.

## ✨ Features

- **PDF Upload:** Ingest a PDF document to serve as the knowledge base.
- **Conversational Q&A:** Ask questions about the document in a conversational manner.
- **Chat History:** The chatbot remembers the context of the current conversation.
- **Source Display:** Shows the exact text chunks from the document used to generate the answer.
- **Dockerized:** The entire backend, including the Ollama LLM, is containerized for easy setup and portability.

## 🛠️ Tech Stack

- **Backend:** FastAPI (Python)
- **AI/RAG Core:** LangChain
- **LLM Server:** Ollama (running `gemma:2b`)
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

## 🚀 Running the Application (Recommended Method: Docker)

This is the simplest and most reliable way to run the entire application.

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/YourUsername/YourRepoName.git](https://github.com/YourUsername/YourRepoName.git)
    cd YourRepoName
    ```

2.  **Ensure Docker Desktop is Running.**

3.  **Build and Run the Container:**
    From the project's root directory, run the following command. This will build the Docker image (which includes Python, Ollama, and all dependencies) and start the service.
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

3.  **Ollama Setup (in a new terminal):**
    Ensure the Ollama desktop application is running, or run `ollama serve` from a terminal. You must also have the required model downloaded:
    ```bash
    ollama pull gemma:2b-instruct-q4_0
    ```



Your Goal	                Command to Run
Start the application	    docker-compose up -d
Stop the application	    docker-compose down
Start after changing code	docker-compose up --build
