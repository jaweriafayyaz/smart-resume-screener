from flask import Flask, request, jsonify, render_template
import os
from dotenv import load_dotenv
from rag_pipeline import load_resumes, chunk_documents, create_vector_store, query_screener

load_dotenv()
app = Flask(__name__)
vector_store = None

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_resumes():
    global vector_store
    files = request.files.getlist("resumes")
    
    if not files:
        return jsonify({"error": "No files uploaded"}), 400
    
    pdf_paths = []
    for file in files:
        path = f"uploads/{file.filename}"
        file.save(path)
        pdf_paths.append(path)
    
    docs = load_resumes(pdf_paths)
    chunks = chunk_documents(docs)
    vector_store = create_vector_store(chunks)
    
    return jsonify({"message": f"✅ {len(files)} resume(s) uploaded and indexed!"})

@app.route("/ask", methods=["POST"])
def ask():
    global vector_store
    
    if not vector_store:
        return jsonify({"error": "Please upload resumes first!"}), 400
    
    question = request.json.get("question", "").strip()
    if not question:
        return jsonify({"error": "Please enter a question"}), 400
    
    answer, sources = query_screener(question, vector_store)
    return jsonify({"answer": answer, "sources": sources})

if __name__ == "__main__":
    os.makedirs("uploads", exist_ok=True)
    app.run(debug=True, port=5000)