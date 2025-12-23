from django.shortcuts import render
import json
import ollama
import numpy as np
import pymongo
import time
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# ==========================================
# 1. SETUP & CACHE
# ==========================================
try:
    client_host = settings.DATABASES['default']['CLIENT']['host']
    client = pymongo.MongoClient(client_host)
    db = client["django_project"]
except Exception as e:
    print(f"Database warning: {e}")


EMBED_MODEL = "qwen3-embedding:0.6b"
CHAT_MODEL = "qwen3:8b" 

# Global Cache (Keeps database in RAM for speed)
PRODUCT_CACHE = []

def load_products_into_memory():
    global PRODUCT_CACHE
    PRODUCT_CACHE = []
    try:
        collections = ["products"]
        for col_name in collections:
            items = list(db[col_name].find({"embedding": {"$exists": True}}))
            for item in items:
                vec = np.array(item['embedding'])
                PRODUCT_CACHE.append({
                    "data": item,
                    "vector": vec,
                    "norm": np.linalg.norm(vec)
                })
        print(f" Cache refreshed: {len(PRODUCT_CACHE)} items.")
    except:
        pass

# Load data once when server starts
load_products_into_memory()

# ==========================================
# 2. CHAT VIEW (WITH BUSY LOCK)
# ==========================================
@csrf_exempt
def chat_view(request):
    #  Login Check
    if not request.user.is_authenticated:
        return JsonResponse({'reply': " Please login first."})

    #  BUSY CHECK: Is the bot currently working for this user?
    # If 'True', we reject the new message immediately.
    if request.session.get('is_bot_thinking', False):
        return JsonResponse({
            'reply': " I am still answering your previous question. Please wait..."
        })

    if request.method == 'POST':
        # LOCK THE SESSION
        request.session['is_bot_thinking'] = True
        request.session.modified = True 

        try:
            start_time = time.time()
            
            # Auto-Refresh Cache if empty
            if not PRODUCT_CACHE:
                load_products_into_memory()

            data = json.loads(request.body)
            user_message = data.get('message', '')
            print(f"\n Question: {user_message}")

            # --- A. Embedding ---
            response_embed = ollama.embeddings(model=EMBED_MODEL, prompt=user_message)
            query_vector = np.array(response_embed['embedding'])
            query_norm = np.linalg.norm(query_vector)

            # --- B. Fast Search ---
            matches = []
            for entry in PRODUCT_CACHE:
                score = np.dot(query_vector, entry['vector']) / (query_norm * entry['norm'])
                if score > 0.25:
                    matches.append((score, entry['data']))

            matches.sort(key=lambda x: x[0], reverse=True)
            top_results = matches[:3]

            # --- C. Context ---
            context_text = ""
            if top_results:
                context_text = "Found items:\n"
                for score, item in top_results:
                    context_text += f"- {item.get('name')}: {item.get('description')}\n"

            # --- D. Generation ---
            print(" Thinking...")
            response = ollama.chat(model=CHAT_MODEL, messages=[
                {'role': 'system', 'content': "You are a helpful assistant. Use context to answer."},
                {'role': 'user', 'content': f"Context:\n{context_text}\n\nQuestion: {user_message}"},
            ])

            print(f"Time: {time.time() - start_time:.2f}s")
            return JsonResponse({'reply': response['message']['content']})

        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse({'reply': "Error processing request."})
        
        finally:
            #  UNLOCK THE SESSION
            # This runs when the bot is done (or if it crashes), allowing the user to type again.
            request.session['is_bot_thinking'] = False
            request.session.modified = True

    return JsonResponse({'error': 'Invalid request'}, status=400)