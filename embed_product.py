import pymongo
import ollama
import time

# ==========================================
# 1. CONFIGURATION
# ==========================================
# PASTE YOUR MONGODB CONNECTION STRING HERE 
MONGO_LINK = "mongodb+srv://nissanlama2020_db_user:nissan12345@cluster0.eloxgi6.mongodb.net/"

# Database and Collection Names
DB_NAME = "django_project"
COLLECTION_NAME = "products"

# The AI Model
EMBED_MODEL = "qwen3-embedding:0.6b"

def start_embedding():
    # --- Connect to MongoDB ---
    try:
        client = pymongo.MongoClient(MONGO_LINK)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        print(f"Connected to database: {DB_NAME}")
    except Exception as e:
        print(f"Connection Failed: {e}")
        return

    print("Starting embedding process...")
    print("Looking for products without embeddings...")

    # --- The Loop ---
    # Find documents that DO NOT have an 'embedding' field yet
    products_to_process = collection.find({"embedding": {"$exists": False}})
    
    count = 0
    for product in products_to_process:
        # 1. Get the data fields
        # We combine Name + Description + Category to give the AI more info
        name = product.get('name', '')
        description = product.get('description', '')
        category = product.get('category', '')
        
        # Combine them into one string
        text_to_embed = f"{name} {description} {category}".strip()

        # 2. Skip if empty
        if not text_to_embed:
            print(f"Skipping {name}: No text to embed.")
            continue

        print(f"Processing: {name}...")

        try:
            # 3. Generate Embedding
            response = ollama.embeddings(
                model=EMBED_MODEL,
                prompt=text_to_embed
            )
            
            # 4. Save back to MongoDB
            collection.update_one(
                {'_id': product['_id']},
                {'$set': {'embedding': response['embedding']}}
            )
            count += 1
            print("Done!")

        except Exception as e:
            print(f"Error: {e}")

    print(f"\n Finished! Processed {count} documents.")

# ==========================================
# SAFETY GUARD
# ==========================================
if __name__ == "__main__":
    start_embedding()