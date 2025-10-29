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
# --- To use Ollama as the RAGAs judge ---
from ragas.llms import LangchainLLM
from langchain_ollama.llms import Ollama

# --- Configuration ---
# Make sure your chatbot is running and accessible at this URL
CHATBOT_API_URL = "http://localhost:8000/api/chat"
# Path to your evaluation dataset
EVAL_DATASET_PATH = "evaluation_dataset.csv"
# Ollama model to use for RAGAs evaluation
RAGAS_OLLAMA_MODEL = "gemma:2b-instruct-q4_0" # Make sure this model is pulled in Ollama

# --- Configure RAGAs to use your local Ollama ---
# Initialize the Langchain LLM with your Ollama model
ollama_llm = Ollama(model=RAGAS_OLLAMA_MODEL)
# Wrap it for RAGAs
ragas_langchain_llm = LangchainLLM(llm=ollama_llm)

# --- Load Your Golden Dataset ---
print(f"Loading evaluation dataset from: {EVAL_DATASET_PATH}")
try:
    # Adjust reading based on your file format (CSV or JSON)
    if EVAL_DATASET_PATH.endswith(".csv"):
        eval_df = pd.read_csv(EVAL_DATASET_PATH)
    elif EVAL_DATASET_PATH.endswith(".json"):
        eval_df = pd.read_json(EVAL_DATASET_PATH)
    else:
        raise ValueError("Unsupported dataset file format. Use .csv or .json")

    # --- Data Cleaning & Preparation ---
    # Ensure required columns exist
    required_columns = ['question', 'ground_truth_answer', 'ground_truth_context']
    for col in required_columns:
        if col not in eval_df.columns:
            raise ValueError(f"Missing required column in dataset: '{col}'")

    # Handle potential NaN/empty values if necessary
    eval_df.fillna("", inplace=True) # Replace NaN with empty strings

    # Convert ground_truth_context to a list of strings if it's not already
    # This assumes context snippets are stored as a single string or need simple splitting.
    # Adjust this logic if your context is stored differently (e.g., JSON list in CSV).
    if isinstance(eval_df['ground_truth_context'].iloc[0], str):
         # Basic example: treat the whole string as one context item
        eval_df['ground_truth_context'] = eval_df['ground_truth_context'].apply(lambda x: [x] if x else [])


    print(f"Loaded {len(eval_df)} evaluation examples.")

except FileNotFoundError:
    print(f"Error: Evaluation dataset not found at {EVAL_DATASET_PATH}")
    exit()
except Exception as e:
    print(f"Error loading or processing dataset: {e}")
    exit()


# --- Function to Query Your Chatbot ---
def get_chatbot_response(question):
    """Calls your chatbot API and returns the answer and retrieved contexts."""
    try:
        response = requests.post(CHATBOT_API_URL, json={"query": question, "chat_history": []}, timeout=120) # Increased timeout
        response.raise_for_status()
        data = response.json()
        contexts = [str(source.get('content', '')) for source in data.get('sources', [])] # Ensure contexts are strings
        answer = str(data.get('answer', '')) # Ensure answer is a string
        return {"answer": answer, "contexts": contexts}
    except requests.exceptions.Timeout:
        print(f"API call timed out for question: '{question}'")
        return {"answer": "Error: API call timed out.", "contexts": []}
    except requests.exceptions.RequestException as e:
        print(f"API call failed for question '{question}': {e}")
        return {"answer": "Error: API call failed.", "contexts": []}
    except Exception as e:
        print(f"Unexpected error processing question '{question}': {e}")
        return {"answer": "Error: Unexpected processing error.", "contexts": []}

# --- Run Chatbot for Each Question ---
print("Querying chatbot for each question in the dataset...")
results_list = []
for index, row in eval_df.iterrows():
    question = str(row['question']) # Ensure question is string
    print(f"  Processing question {index+1}/{len(eval_df)}: {question[:50]}...")
    response_data = get_chatbot_response(question)
    results_list.append({
        "question": question,
        "answer": response_data['answer'],
        "contexts": response_data['contexts'],
        "ground_truth": str(row['ground_truth_answer']) # RAGAs expects 'ground_truth'
        # Context Recall requires this column, ensure it's a list of strings
        # "ground_truth_context": row['ground_truth_context']
    })

results_df = pd.DataFrame(results_list)

# --- Convert to Hugging Face Dataset ---
print("Converting results to RAGAs dataset format...")
try:
    ragas_dataset = Dataset.from_pandas(results_df)
except Exception as e:
    print(f"Error converting DataFrame to Dataset: {e}")
    print("DataFrame sample:")
    print(results_df.head())
    exit()

# --- Define Metrics & Run Evaluation ---
# Context Recall needs 'ground_truth_context' in the dataset. Uncomment if you have it.
metrics_to_evaluate = [
    faithfulness,
    answer_relevancy,
    context_precision,
    # context_recall,
]

print("Running RAGAs evaluation (this may take a while)...")
try:
    # Pass the configured Ollama LLM to RAGAs
    score = evaluate(
        ragas_dataset,
        metrics=metrics_to_evaluate,
        llm=ragas_langchain_llm,      # Use Ollama
        embeddings=None             # Use default embeddings for metrics like answer_relevancy
                                    # Or configure your specific embedding model if needed
        # raise_exceptions=False      # Set to False to see partial results even if some rows fail
    )
    print("Evaluation complete.")
    evaluation_results_df = score.to_pandas()
    print("\n--- Evaluation Results ---")
    print(evaluation_results_df)

    # Calculate and print average scores
    print("\n--- Average Scores ---")
    average_scores = evaluation_results_df[[m.name for m in metrics_to_evaluate]].mean()
    print(average_scores)


    # Save results
    results_filename = "evaluation_results.csv"
    evaluation_results_df.to_csv(results_filename, index=False)
    print(f"\nResults saved to {results_filename}")

except Exception as e:
    print(f"An error occurred during RAGAs evaluation: {e}")
    import traceback
    traceback.print_exc()