import time
import pymongo
import ollama

# ==========================================
# 1. SETUP
# ==========================================
#  PASTE YOUR CONNECTION STRING HERE 
MONGO_LINK = "mongodb+srv://nissanlama2020_db_user:nissan12345@cluster0.eloxgi6.mongodb.net/"

# The new model you want to use
EMBED_MODEL = "qwen3-embedding:0.6b"

WATCH_LIST = {
    "products": "description",
    "recommendations": "content",
}

def start_watching():
    # Connect to Database
    try:
        client = pymongo.MongoClient(MONGO_LINK)
        db = client["django_project"] 
        print(f"Connected to database: {db.name}")
        print(f"Using Embedding Model: {EMBED_MODEL}")
    except Exception as e:
        print(f" Connection Failed: {e}")
        return

    # ==========================================
    # 2. THE WATCHER LOOP
    # ==========================================
    print("Auto-Embedder is running... (Press Ctrl+C to stop)")
    print(" Waiting for items without embeddings...")

    while True:
        try:
            for collection_name, text_field in WATCH_LIST.items():
                collection = db[collection_name]
                
                # Find items MISSING "embedding"
                items_to_fix = collection.find({"embedding": {"$exists": False}})
                
                for item in items_to_fix:
                    text_content = item.get(text_field)
                    
                    if text_content:
                        print(f"⚡ Processing: {item.get('name', 'Item')}...")
                        try:
                            # Using the NEW Model here
                            response = ollama.embeddings(
                                model=EMBED_MODEL, 
                                prompt=text_content
                            )
                            collection.update_one(
                                {"_id": item["_id"]},
                                {"$set": {"embedding": response['embedding']}}
                            )
                            print("Done!")
                        except Exception as err:
                            print(f"Failed: {err}")
                    else:
                        collection.update_one(
                            {"_id": item["_id"]}, 
                            {"$set": {"embedding": []}}
                        )

            time.sleep(1)

        except Exception as e:
            print(f" Error in loop: {e}")
            time.sleep(1)

# ==========================================
# 3. SAFETY GUARD
# ==========================================
if __name__ == "__main__":
    start_watching()                