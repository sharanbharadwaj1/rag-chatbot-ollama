param(
    [string]$ProjectId = 'YOUR_PROJECT_ID',
    [string]$Region = 'us-central1',
    [string]$RepoName = 'rag-chatbot-repo',
    [string]$ServiceName = 'rag-chatbot-gemini',
    [string]$BucketName = 'YOUR_CHROMA_BUCKET',
    [string]$GeminiSecretName = 'google-api-key',
    [string]$AllowedOrigins = '*'
)

$ErrorActionPreference = 'Stop'

if ($ProjectId -eq 'YOUR_PROJECT_ID' -or $BucketName -eq 'YOUR_CHROMA_BUCKET') {
    throw 'Fill in ProjectId and BucketName before running this script.'
}

$Image = "$Region-docker.pkg.dev/$ProjectId/$RepoName/$ServiceName`:latest"

Write-Host 'Setting active project...'
gcloud config set project $ProjectId

Write-Host 'Enabling required APIs...'
gcloud services enable run.googleapis.com
 gcloud services enable cloudbuild.googleapis.com
 gcloud services enable artifactregistry.googleapis.com
 gcloud services enable secretmanager.googleapis.com

Write-Host 'Creating Artifact Registry repo if needed...'
gcloud artifacts repositories create $RepoName --repository-format=docker --location=$Region --description='RAG chatbot images' 2>$null

Write-Host 'Building container image...'
gcloud builds submit .\backend --tag $Image

Write-Host 'Deploying to Cloud Run...'
gcloud run deploy $ServiceName `
  --image $Image `
  --platform managed `
  --region $Region `
  --allow-unauthenticated `
  --port 8080 `
  --memory 4Gi `
  --cpu 2 `
  --timeout 300 `
  --concurrency 1 `
  --max-instances 1 `
  --min-instances 1 `
  --execution-environment gen2 `
  --update-env-vars "VECTOR_DB_PATH=/mnt/chroma/local_chroma_db,ALLOWED_ORIGINS=$AllowedOrigins" `
  --update-secrets "GOOGLE_API_KEY=$GeminiSecretName:latest" `
  --add-volume "name=chroma-data,type=cloud-storage,bucket=$BucketName" `
  --add-volume-mount "volume=chroma-data,mount-path=/mnt/chroma"

Write-Host 'Done. Get the URL with:'
Write-Host "gcloud run services describe $ServiceName --region $Region --format='value(status.url)'"
