import os
import requests

NOTES_DIR = "./notes"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "tinyllama:latest"

def load_notes():
    if not os.path.exists(NOTES_DIR):
        os.makedirs(NOTES_DIR)
        print(f"Created '{NOTES_DIR}' folder. Drop .txt files in there.")
        return ""
    
    context = ""
    for filename in os.listdir(NOTES_DIR):
        if filename.endswith(".txt") or filename.endswith(".md"):
            filepath = os.path.join(NOTES_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    context += f"\n[{filename}]\n{f.read()}\n"
            except Exception as e:
                print(f"Skipped {filename}: {e}")
    return context

def ask(question):
    notes = load_notes()
    
    prompt = (
        "You are a private offline assistant. "
        "Answer using the notes below. "
        "If the notes don't have the answer, say so and use general knowledge.\n\n"
        f"Notes:\n{notes}\n\n"
        f"Question: {question}\nAnswer:"
    )
    
    try:
        res = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }, timeout=60)
        return res.json().get("response", "No response.")
    except requests.exceptions.ConnectionError:
        return "Can't connect. Run 'ollama serve' in another tab first."
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    print("\n=== Local Note Chat (offline) ===")
    print("Type 'quit' to exit\n")
    
    while True:
        question = input("You: ").strip()
        if not question:
            continue
        if question.lower() == "quit":
            break
        print(f"\nAssistant: {ask(question)}\n")
