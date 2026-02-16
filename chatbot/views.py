from django.shortcuts import render
import json
import ollama
import time
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from recommendation.vector_search import search_similar_animals

# ==========================================
# CONFIG
# ==========================================
CHAT_MODEL = "qwen3:8b"

# Cache for repeated questions
QUERY_CACHE = {}


# ==========================================
# CHAT VIEW
# ==========================================
@csrf_exempt
def chat_view(request):

    # Login Check
    if not request.user.is_authenticated:
        return JsonResponse({'reply': "Please login first."})

    # Busy check
    if request.session.get('is_bot_thinking', False):
        return JsonResponse({
            'reply': "I am still answering your previous question. Please wait..."
        })

    if request.method == 'POST':

        # Lock session
        request.session['is_bot_thinking'] = True
        request.session.modified = True

        try:
            start_time = time.time()

            data = json.loads(request.body)
            user_message = data.get('message', '').strip().lower()

            print(f"\nQuestion: {user_message}")

            # ======================================
            # A. CHECK QUERY CACHE
            # ======================================
            if user_message in QUERY_CACHE:
                print("Returned from cache")
                return JsonResponse({'reply': QUERY_CACHE[user_message]})

            # ======================================
            # B. VECTOR SEARCH WITH FILTERS
            # ======================================
            max_price = None
            location = None

            words = user_message.split()

            # Detect price like "under 100000"
            for word in words:
                if word.isdigit():
                    max_price = int(word)

            # Detect location keywords
            for loc in ["chitwan", "butwal", "kathmandu", "pokhara"]:
                if loc in user_message:
                    location = loc

            top_results = search_similar_animals(
                user_message,
                top_k=3,
                max_price=max_price,
                location=location
            )

            # ======================================
            # C. CONTEXT BUILDING
            # ======================================
            context_text = ""
            if top_results:
                context_text = "Found animals:\n"
                for item in top_results:
                    context_text += (
                        f"- ID: {item['animal_id']}, "
                        f"{item['type']} ({item['breed']}), "
                        f"Location: {item.get('location', 'unknown')}, "
                        f"Price: NPR {item['price']}\n"
                    )

            # ======================================
            # D. GENERATION
            # ======================================
            print("Thinking...")
            response = ollama.chat(
                model=CHAT_MODEL,
                messages=[
                    {
                        'role': 'system',
                        'content': "You are a helpful livestock assistant. Use the provided context to answer the user."
                    },
                    {
                        'role': 'user',
                        'content': f"Context:\n{context_text}\n\nQuestion: {user_message}"
                    },
                ]
            )

            reply = response['message']['content']

            # Save to cache
            QUERY_CACHE[user_message] = reply

            print(f"Time: {time.time() - start_time:.2f}s")
            return JsonResponse({'reply': reply})

        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse({'reply': "Error processing request."})

        finally:
            # Unlock session
            request.session['is_bot_thinking'] = False
            request.session.modified = True

    return JsonResponse({'error': 'Invalid request'}, status=400)
