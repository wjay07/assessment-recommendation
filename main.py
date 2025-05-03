from fastapi import FastAPI, Request
from pydantic import BaseModel
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv()

# Load the embedded CSV
df = pd.read_csv("embedded_assessments.csv")

# Decode test type codes (A, B, C, etc.)
category_map = {
    'A': 'Ability & Aptitude',
    'B': 'Biodata & Situational Judgement',
    'C': 'Competencies',
    'D': 'Development & 360',
    'E': 'Assessment Exercises',
    'K': 'Knowledge & Skills',
    'P': 'Personality & Behavior',
    'S': 'Simulations'
}

# Convert string embeddings to list
df['gemini_embedding'] = df['gemini_embedding'].apply(eval)

# FastAPI app
app = FastAPI()

# Health Check
@app.get("/status")
def health_check():
    return {"status": "healthy"}

# Request model for recommendation
class QueryRequest(BaseModel):
    query: str

# Use Gemini embedding model
def get_embedding(text):
    try:
        api_key = os.getenv("GEMINI_API_KEY")  # Retrieve API key from environment variable
        if not api_key:
            raise ValueError("API key not found in environment variables")

        genai.configure(api_key=api_key)

        response = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_query"
        )
        return response['embedding']
    except Exception as e:
        print(f"Embedding error: {e}")
        return None

@app.post("/recommend")
def recommend_assessments(request: QueryRequest):
    query_embedding = get_embedding(request.query)

    if query_embedding is None:
        return {"error": "Failed to generate embedding"}

    similarities = cosine_similarity([query_embedding], df['gemini_embedding'].tolist())[0]
    df['similarity'] = similarities
    top_results = df.sort_values(by='similarity', ascending=False).head(10)

    response = []
    for _, row in top_results.iterrows():
        # Decode test-type from string like "A, C, P"
        types = [category_map[code.strip()] for code in str(row['test']).split(',') if code.strip() in category_map]

        response.append({
            "url": row['link'],
            "adaptive_support": "Yes" if str(row['adaptive_irt']).strip().lower() == "yes" else "No",
            "description": row['description'],
            "duration": int(row['time']) if row['time'] != '' else 0,
            "remote_support": "Yes" if str(row['remote']).strip().lower() == "yes" else "No",
            "test_type": types
        })

    return {"recommended_assessments": response}
