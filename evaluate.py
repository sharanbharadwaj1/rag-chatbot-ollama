# evaluate.py (Modern Version for Gemini + Ragas 1.0+)

import os
import requests
import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision,
)
from dotenv import load_dotenv

# --- New Imports ---
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from ragas.llms import LangchainLLMWrapper # This is the new Ragas 1.0+ import
from langchain_groq import ChatGroq
# --- Configuration ---
CHATBOT_API_URL = "http://localhost:8000/api/chat"
EVAL_DATASET_PATH = "evaluation_dataset.csv"

# --- Load API Key from .env in the /backend folder ---
load_dotenv(dotenv_path=".env")
# if os.getenv("GOOGLE_API_KEY") is None:
#     print("Error: GOOGLE_API_KEY not found. Please check your backend/.env file.")
#     exit()

# --- Configure RAGAs to use Google Gemini ---
# print("Connecting to Google Gemini (for RAGAs judge)...")
# gemini_llm = ChatGoogleGenerativeAI(
#     model="gemini-2.5-flash", # Fast and powerful
#     google_api_key=os.getenv("GOOGLE_API_KEY")
# )
# Wrap it for RAGAs
# ragas_llm = LangchainLLMWrapper(gemini_llm)
# print("✅ Connected to Gemini.")


# --- Configure RAGAs to use Groq ---
print("Connecting to Groq (for RAGAs judge)...")
if os.getenv("GROQ_API_KEY") is None:
    print("Error: GROQ_API_KEY not found. Please check your backend/.env file.")
    exit()

groq_llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY")
)
ragas_llm = LangchainLLMWrapper(groq_llm)
print("✅ Connected to Groq.")

# --- Configure RAGAs to use Local Embeddings ---
print("Loading local embedding model (for RAGAs metrics)...")
local_embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
print("✅ Local embeddings loaded.")


# --- Load Your Golden Dataset ---
print(f"Loading evaluation dataset from: {EVAL_DATASET_PATH}")
try:
    eval_df = pd.read_csv(EVAL_DATASET_PATH)
    # Ensure required columns exist
    required_columns = ['question', 'ground_truth_answer']
    for col in required_columns:
        if col not in eval_df.columns:
            raise ValueError(f"Missing required column in dataset: '{col}'")

    eval_df.fillna("", inplace=True)
    print(f"Loaded {len(eval_df)} evaluation examples.")

except FileNotFoundError:
    print(f"Error: Evaluation dataset not found at {EVAL_DATASET_PATH}")
    exit()
except Exception as e:
    print(f"Error loading or processing dataset: {e}")
    exit()

import time
# --- Function to Query Your Chatbot ---
def get_chatbot_response(question):
    """Calls your chatbot API and returns the answer and retrieved contexts."""
    try:
        response = requests.post(CHATBOT_API_URL, json={"query": question, "chat_history": []}, timeout=120)
        response.raise_for_status()
        data = response.json()
        contexts = [str(source.get('content', '')) for source in data.get('sources', [])]
        answer = str(data.get('answer', ''))
        return {"answer": answer, "contexts": contexts}
    except Exception as e:
        print(f"API call failed for question '{question}': {e}")
        return {"answer": "Error: API call failed.", "contexts": []}

# --- Run Chatbot for Each Question ---
print("Querying chatbot for each question in the dataset...")
results_list = []
for index, row in eval_df.iterrows():
    question = str(row['question'])
    print(f"  Processing question {index+1}/{len(eval_df)}: {question[:50]}...")

    # --- ADD THESE TWO LINES ---
    if index > 0: # Don't wait before the *first* request
        time.sleep(27) # Wait 7 seconds (to stay under 10 reqs/min)


    response_data = get_chatbot_response(question)
    
    results_list.append({
        "question": question,
        "answer": response_data['answer'],
        "contexts": response_data['contexts'],
        "ground_truth": str(row['ground_truth_answer']) # RAGAs expects 'ground_truth'
    })

results_df = pd.DataFrame(results_list)

# --- Convert to Hugging Face Dataset ---
print("Converting results to RAGAs dataset format...")
ragas_dataset = Dataset.from_pandas(results_df)

# --- Define Metrics & Run Evaluation ---
metrics_to_evaluate = [
    faithfulness,
    answer_relevancy,
    context_precision,
    # context_recall, # This metric requires 'ground_truth_context' column
]

print("Running RAGAs evaluation (this may take a while)...")
try:
    score = evaluate(
        ragas_dataset,
        metrics=metrics_to_evaluate,
        llm=ragas_llm,                # Use Gemini
        embeddings=local_embeddings   # Use local embeddings
    )
    print("Evaluation complete.")
    evaluation_results_df = score.to_pandas()
    print("\n--- Evaluation Results ---")
    print(evaluation_results_df)

    print("\n--- Average Scores ---")
    average_scores = evaluation_results_df[[m.name for m in metrics_to_evaluate]].mean()
    print(average_scores)

    results_filename = "evaluation_results.csv"
    evaluation_results_df.to_csv(results_filename, index=False)
    print(f"\nResults saved to {results_filename}")

except Exception as e:
    print(f"An error occurred during RAGAs evaluation: {e}")
    import traceback
    traceback.print_exc()