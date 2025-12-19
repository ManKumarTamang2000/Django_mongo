from django.shortcuts import render
import json
import ollama
import numpy as np
import pymongo
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# ==========================================
# 1. SETUP DATABASE CONNECTION
# ==========================================
try:
    client_host = settings.DATABASES['default']['CLIENT']['host']
    client = pymongo.MongoClient(client_host)
    db = client["django_project"] 
    # We will define collections inside the loop later
except Exception as e:
    print(f"Database connection warning: {e}")

# Define the model name in one place so it matches the other script
EMBED_MODEL = "qwen3-embedding:0.6b"

# ==========================================
# 2. MATH HELPER
# ==========================================
def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# ==========================================
# 3. CHAT VIEW
# ==========================================
@csrf_exempt
def chat_view(request):
    if request.method == 'POST':
        try:
            # --- Step A: Get User Message ---
            data = json.loads(request.body)
            user_message = data.get('message', '')

            # --- Step B: Convert User Message to Numbers ---
            # Using the NEW Model
            response_embed = ollama.embeddings(model=EMBED_MODEL, prompt=user_message)
            query_vector = response_embed['embedding']

            # --- Step C: Search Database (Products & Recommendations) ---
            best_match = None
            highest_score = -1
            match_type = ""
            
            # Collections to search
            collections_to_search = ["products", "recommendations"]

            for col_name in collections_to_search:
                collection = db[col_name]
                for item in collection.find():
                    if "embedding" in item:
                        score = cosine_similarity(query_vector, item['embedding'])
                        if score > highest_score:
                            highest_score = score
                            best_match = item
                            match_type = col_name

            # --- Step D: Create Context ---
            context_text = ""
            if best_match and highest_score > 0.4:
                # Handle different field names
                name = best_match.get('name') or best_match.get('title') or "Unknown"
                desc = best_match.get('description') or best_match.get('content') or ""
                price = best_match.get('price', '')
                
                context_text = (
                    f"Found relevant {match_type} in database:\n"
                    f"Item: {name}\n"
                    f"Info: {desc}\n"
                    f"{'Price: ' + str(price) if price else ''}"
                )

            # --- Step E: Send to Qwen ---
            final_system_instruction = (
                "You are a helpful assistant for a farming website. "
                "Use the provided context info to answer the user's question if relevant."
            )

            response = ollama.chat(model='qwen3:8b', messages=[
                {'role': 'system', 'content': final_system_instruction},
                {'role': 'user', 'content': f"Context Info: {context_text}\n\nUser Question: {user_message}"},
            ])

            return JsonResponse({'reply': response['message']['content']})

        except Exception as e:
            print(f"Error: {e}") 
            return JsonResponse({'reply': f"Error: {str(e)}"})
            
    return JsonResponse({'error': 'Invalid request'}, status=400)