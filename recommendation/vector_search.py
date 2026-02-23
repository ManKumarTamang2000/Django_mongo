# recommendation/vector_search.py

import numpy as np
import ollama
from django.core.cache import cache
from pymongo import MongoClient

# ==========================================
# CONFIG
# ==========================================
MONGO_LINK = "mongodb+srv://nissanlama2020_db_user:Chhaano2019@cluster0.eloxgi6.mongodb.net/"
DB_NAME = "django_project"
COLLECTIONS = ["buffaloes", "chickens", "goats"]
EMBED_MODEL = "qwen3-embedding:0.6b"

# Reuse Mongo client (IMPORTANT for performance)
_client = MongoClient(MONGO_LINK)
_db = _client[DB_NAME]


# ==========================================
# EMBEDDING
# ==========================================
def get_query_embedding(text: str) -> np.ndarray:
    """
    Generate embedding for user query using Ollama.
    """
    response = ollama.embeddings(
        model=EMBED_MODEL,
        prompt=text
    )
    return np.array(response["embedding"], dtype=float)


# ==========================================
# SIMILARITY
# ==========================================
def cosine_similarity(a, b) -> float:
    """
    Safe cosine similarity (production ready).
    """
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)

    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-10
    return float(np.dot(a, b) / denom)


# ==========================================
# METADATA SCORING (HYBRID BOOST)
# ==========================================
def metadata_score(doc, max_price=None, location=None) -> float:
    """
    Adds extra score based on filters.
    Helps move from pure semantic → hybrid recommendation.
    """
    score = 0.0

    # ✅ Price bonus
    if max_price is not None:
        price = doc.get("price_npr")
        if price and price <= max_price:
            score += 0.15

    # ✅ Location bonus
    if location:
        doc_location = doc.get("seller", {}).get("location", "").lower()
        if location.lower() in doc_location:
            score += 0.15

    return score


# ==========================================
# MAIN SEARCH
# ==========================================
def search_similar_animals(
    query_text,
    top_k=5,
    max_price=None,
    location=None
):
    """
    Hybrid semantic + metadata animal search.
    Production optimized.
    """

    # =====================
    # CACHE CHECK
    # =====================
    cache_key = f"search:{query_text}:{top_k}:{max_price}:{location}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # =====================
    # QUERY EMBEDDING
    # =====================
    query_vector = get_query_embedding(query_text)

    results = []

    # =====================
    # SEARCH ALL COLLECTIONS
    # =====================
    for col_name in COLLECTIONS:
        collection = _db[col_name]

        docs = collection.find(
            {"embedding": {"$exists": True}},
            {
                "animal_id": 1,
                "type": 1,
                "breed": 1,
                "price_npr": 1,
                "seller.location": 1,
                "embedding": 1,
            },
        )

        for doc in docs:
            emb = doc.get("embedding")
            if not emb:
                continue

            price = doc.get("price_npr")
            doc_location = doc.get("seller", {}).get("location", "").lower()

            # =====================
            # HARD FILTERS
            # =====================
            if max_price is not None and price:
                if price > max_price:
                    continue

            if location:
                if location.lower() not in doc_location:
                    continue

            # =====================
            # VECTOR SCORE
            # =====================
            vector_score = cosine_similarity(query_vector, emb)

            # =====================
            # METADATA BOOST
            # =====================
            meta_boost = metadata_score(doc, max_price, location)

            # Hybrid score (tunable weights)
            final_score = (0.8 * vector_score) + (0.2 * meta_boost)

            results.append({
                "animal_id": doc.get("animal_id"),
                "type": doc.get("type"),
                "breed": doc.get("breed"),
                "price": price,
                "location": doc_location,
                "score": float(final_score),
            })

    # =====================
    # SORT + LIMIT
    # =====================
    results.sort(key=lambda x: x["score"], reverse=True)
    top_results = results[:top_k]

    # =====================
    # CACHE STORE
    # =====================
    cache.set(cache_key, top_results, timeout=300)

    return top_results