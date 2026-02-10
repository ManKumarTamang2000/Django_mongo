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
    db = None


EMBED_MODEL = "qwen3-embedding:0.6b"
CHAT_MODEL = "qwen3:8b"

# Global Cache (Keeps database in RAM for speed)
PRODUCT_CACHE = []
QUERY_CACHE = {}  # New: cache for repeated questions


def load_products_into_memory():
    global PRODUCT_CACHE
    PRODUCT_CACHE = []
    try:
        collections = ["buffaloes"]
        for col_name in collections:
            items = list(db[col_name].find({"embedding": {"$exists": True}}))
            for item in items:
                vec = np.array(item['embedding'])
                norm = np.linalg.norm(vec)

                # Normalize vector once (faster later)
                if norm != 0:
                    vec = vec / norm

                PRODUCT_CACHE.append({
                    "data": item,
                    "vector": vec,
                })
        print(f"Cache refreshed: {len(PRODUCT_CACHE)} items.")
    except Exception as e:
        print(f"Cache load error: {e}")


# Load data once when server starts
load_products_into_memory()

# ==========================================
# 2. CHAT VIEW (WITH BUSY LOCK)
# ==========================================
@csrf_exempt
def chat_view(request):

    # Login Check
    if not request.user.is_authenticated:
        return JsonResponse({'reply': "Please login first."})

    # BUSY CHECK
    if request.session.get('is_bot_thinking', False):
        return JsonResponse({
            'reply': "I am still answering your previous question. Please wait..."
        })

    if request.method == 'POST':

        # LOCK SESSION
        request.session['is_bot_thinking'] = True
        request.session.modified = True

        try:
            start_time = time.time()

            # Auto-refresh cache
            if not PRODUCT_CACHE:
                load_products_into_memory()

            data = json.loads(request.body)
            user_message = data.get('message', '').strip().lower()

            print(f"\nQuestion: {user_message}")

            # ======================================
            # A. CHECK QUERY CACHE (FAST RESPONSE)
            # ======================================
            if user_message in QUERY_CACHE:
                print("Returned from cache")
                return JsonResponse({'reply': QUERY_CACHE[user_message]})

            # ======================================
            # B. EMBEDDING
            # ======================================
            response_embed = ollama.embeddings(
                model=EMBED_MODEL,
                prompt=user_message
            )
            query_vector = np.array(response_embed['embedding'])
            query_norm = np.linalg.norm(query_vector)

            if query_norm != 0:
                query_vector = query_vector / query_norm

            # ======================================
            # C. FAST SEARCH (COSINE SIM)
            # ======================================
            matches = []
            for entry in PRODUCT_CACHE:
                score = np.dot(query_vector, entry['vector'])
                if score > 0.25:
                    matches.append((score, entry['data']))

            matches.sort(key=lambda x: x[0], reverse=True)
            top_results = matches[:3]

            # ======================================
            # D. CONTEXT BUILDING
            # ======================================
            context_text = ""
            if top_results:
                context_text = "Found items:\n"
                for score, item in top_results:
                    context_text += f"- {item.get('name')}: {item.get('description')}\n"

            # ======================================
            # E. GENERATION
            # ======================================
            print("Thinking...")
            response = ollama.chat(
                model=CHAT_MODEL,
                messages=[
                    {
                        'role': 'system',
                        'content': "You are a helpful assistant. Use context to answer."
                    },
                    {
                        'role': 'user',
                        'content': f"Context:\n{context_text}\n\nQuestion: {user_message}"
                    },
                ]
            )

            reply = response['message']['content']

            # Save to query cache
            QUERY_CACHE[user_message] = reply

            print(f"Time: {time.time() - start_time:.2f}s")
            return JsonResponse({'reply': reply})

        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse({'reply': "Error processing request."})

        finally:
            # UNLOCK SESSION
            request.session['is_bot_thinking'] = False
            request.session.modified = True

    return JsonResponse({'error': 'Invalid request'}, status=400)
