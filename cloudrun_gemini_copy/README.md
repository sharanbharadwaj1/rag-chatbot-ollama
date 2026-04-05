# Gemini-Only Cloud Run Copy

This folder is the Cloud Run deployment version of your RAG chatbot. It keeps the core chatbot behavior the same:

- FastAPI backend
- PDF / CSV / website ingestion
- `RecursiveCharacterTextSplitter` with `chunk_size=1000` and `chunk_overlap=200`
- local Hugging Face embeddings
- Chroma vector store
- BGE reranker
- Gemini answer generation

What changed is only the deployment plumbing:

- Ollama-specific startup was removed
- the frontend is served by FastAPI from the same container
- `VECTOR_DB_PATH` is configurable so Cloud Run can mount durable storage
- uploads use `/tmp` for short-lived processing
- the app restores the Chroma collection on startup if the mounted storage already contains data
- CORS can now be controlled with `ALLOWED_ORIGINS`

## Important Constraint

Because this copy intentionally preserves filesystem-backed Chroma, deploy it as a learning setup with:

- `concurrency=1`
- `max-instances=1`

That keeps the single-writer behavior safe enough for a prototype deployment. For a truly scalable production design, the next upgrade is replacing Chroma-on-filesystem with a managed vector database.

## Deployment Checklist

1. Install and log into the Google Cloud CLI.
2. Create or choose a GCP project.
3. Enable billing on that project.
4. Enable these APIs:
   - Cloud Run API
   - Cloud Build API
   - Artifact Registry API
   - Secret Manager API
5. Create an Artifact Registry Docker repo.
6. Create a Cloud Storage bucket for Chroma persistence.
7. Create a Secret Manager secret for `GOOGLE_API_KEY`.
8. Build the image.
9. Deploy to Cloud Run with the mounted bucket.
10. Open the service URL and test the UI.

## Fastest Path

Run the helper script after filling in your values:

- [deploy_cloudrun.ps1](E:/Projects/rag%20chatbot%207%2010%202025/cloudrun_gemini_copy/deploy_cloudrun.ps1)

## Manual Commands

### Build and push the container

```powershell
gcloud builds submit .\backend --tag REGION-docker.pkg.dev/PROJECT_ID/REPO_NAME/rag-chatbot-gemini:latest
```

### Deploy to Cloud Run

```powershell
gcloud run deploy rag-chatbot-gemini `
  --image REGION-docker.pkg.dev/PROJECT_ID/REPO_NAME/rag-chatbot-gemini:latest `
  --platform managed `
  --region REGION `
  --allow-unauthenticated `
  --port 8080 `
  --memory 4Gi `
  --cpu 2 `
  --timeout 300 `
  --concurrency 1 `
  --max-instances 1 `
  --min-instances 1 `
  --execution-environment gen2 `
  --update-env-vars VECTOR_DB_PATH=/mnt/chroma/local_chroma_db,ALLOWED_ORIGINS=* `
  --update-secrets GOOGLE_API_KEY=google-api-key:latest `
  --add-volume name=chroma-data,type=cloud-storage,bucket=YOUR_CHROMA_BUCKET `
  --add-volume-mount volume=chroma-data,mount-path=/mnt/chroma
```

## Environment Variables

- `GOOGLE_API_KEY`: Gemini API key
- `VECTOR_DB_PATH`: Chroma persistence directory
- `CHROMA_COLLECTION_NAME`: defaults to `langchain`
- `GEMINI_CHAT_MODEL`: defaults to `gemini-2.5-flash`
- `ALLOWED_ORIGINS`: comma-separated CORS origins

## Notes

- Visiting `/` serves the UI.
- The frontend calls `/api/*` on the same host.
- Uploaded PDFs and CSVs are processed in `/tmp` and then indexed into Chroma.
- Chroma persistence lives in the mounted Cloud Storage path.

## Next Upgrade Path

If you later want proper horizontal scale, replace filesystem-backed Chroma with `pgvector` or another managed vector database.
