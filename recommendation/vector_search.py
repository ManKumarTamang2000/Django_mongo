import pymongo
import numpy as np
import ollama

MONGO_LINK = "mongodb+srv://nissanlama2020_db_user:Chhaano2019@cluster0.eloxgi6.mongodb.net/"
DB_NAME = "django_project"
COLLECTIONS = ["buffaloes", "chickens", "goats"]
EMBED_MODEL = "qwen3-embedding:0.6b"


def get_query_embedding(text):
    response = ollama.embeddings(
        model=EMBED_MODEL,
        prompt=text
    )
    return np.array(response['embedding'])


def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def search_similar_animals(query_text, top_k=5):
    client = pymongo.MongoClient(MONGO_LINK)
    db = client[DB_NAME]

    query_vector = get_query_embedding(query_text)

    results = []

    for col_name in COLLECTIONS:
        collection = db[col_name]
        docs = collection.find({"embedding": {"$exists": True}})

        for doc in docs:
            emb = doc.get("embedding")
            if not emb:
                continue

            score = cosine_similarity(query_vector, np.array(emb))

            results.append({
                "animal_id": doc.get("animal_id"),
                "type": doc.get("type"),
                "breed": doc.get("breed"),
                "price": doc.get("price_npr"),
                "score": float(score)
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]
