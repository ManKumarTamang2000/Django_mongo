import pymongo
import ollama
import time

# ==========================================
# 1. CONFIGURATION
# ==========================================
MONGO_LINK = "mongodb+srv://nissanlama2020_db_user:Chhaano2019@cluster0.eloxgi6.mongodb.net/"

DB_NAME = "django_project"

# All collections to process
COLLECTIONS = ["buffaloes", "chickens", "goats"]

# The AI Model
EMBED_MODEL = "qwen3-embedding:0.6b"


def process_collection(collection):
    print(f"\nProcessing collection: {collection.name}")
    products_to_process = collection.find({"embedding": {"$exists": False}})
    
    count = 0
    for product in products_to_process:
        animal_id = product.get('animal_id', '')
        animal_type = product.get('type', '')
        breed = product.get('breed', '')
        gender = product.get('gender', '')
        location = product.get('seller', {}).get('location', '')

        text_to_embed = f"{animal_type} {breed} {gender} {location}".strip()

        if not text_to_embed:
            print(f"Skipping {animal_id}: No text to embed.")
            continue

        print(f"Processing: {animal_id}...")

        try:
            response = ollama.embeddings(
                model=EMBED_MODEL,
                prompt=text_to_embed
            )

            collection.update_one(
                {'_id': product['_id']},
                {'$set': {'embedding': response['embedding']}}
            )
            count += 1
            print("Done!")

        except Exception as e:
            print(f"Error: {e}")

    print(f"Finished {collection.name}: {count} documents.")


def start_embedding():
    try:
        client = pymongo.MongoClient(MONGO_LINK)
        db = client[DB_NAME]
        print(f"Connected to database: {DB_NAME}")
    except Exception as e:
        print(f"Connection Failed: {e}")
        return

    print("Starting embedding process...")

    for col_name in COLLECTIONS:
        collection = db[col_name]
        process_collection(collection)

    print("\nAll collections processed.")


# ==========================================
# AUTO EMBEDDING LOGIC
# ==========================================
if __name__ == "__main__":
    print("Initial embedding for existing data...")
    start_embedding()   # Run once for all existing data

    print("\nSwitching to auto-embedding mode (new data only)...")

    while True:
        time.sleep(45)  # check every 2 minutes
        start_embedding()
