# Adobe Hackathon Challenge 1A – Persona-Driven Document Intelligence (Dockerized)

This repository contains the Dockerized solution for *Challenge 1A* of the Adobe India Hackathon. It processes PDF documents to extract structured document intelligence (titles, outlines, OCR content, language detection, etc.) and outputs it in a structured JSON format.

---

## 📁 Directory Structure

Adobe_Hack_ChatGPT_Abusers/
├── main.py # Main Python script
├── requirements.txt # Python dependencies
├── Dockerfile # Docker configuration
├── Challenge_1a/
│ └── sample_dataset/
│ ├── pdfs/ # Input PDFs (Mount point)
│ └── outputs/ # Output JSONs (Mount point)

yaml
Copy
Edit

---

## 🐳 Docker Build Instructions

1. *Make sure Docker is installed* and running on your system.

2. *Build the Docker image* using:

```bash
docker build --platform linux/amd64 -t challenge1a_solution:latest .
🚀 Run the Container
To process all PDFs from Challenge_1a/sample_dataset/pdfs and generate corresponding .json outputs in Challenge_1a/sample_dataset/outputs:

bash
Copy
Edit
docker run --rm \
  -v $(pwd)/Challenge_1a/sample_dataset/pdfs:/app/Challenge_1a/sample_dataset/pdfs \
  -v $(pwd)/Challenge_1a/sample_dataset/outputs:/app/Challenge_1a/sample_dataset/outputs \
  --platform linux/amd64 \
  challenge1a_solution:latest
⚠ If you're using macOS on Apple Silicon (M1/M2), the --platform linux/amd64 flag ensures compatibility with dependencies like PyMuPDF.

🧠 Features
📑 Extracts title from PDF metadata or first-page headings

🧾 Auto-detects and organizes document structure (H1, H2, H3)

🧠 Merges fragmented headings and removes noise

🗣 Detects language per page using langdetect

📊 Extracts tables with pdfplumber

🔍 OCR fallback using pytesseract when no text is found

📦 Outputs structured JSONs for each PDF

🧪 Sample Output Format
Each PDF generates a file like final_output_<pdf_name>.json in the outputs/ directory.

json
Copy
Edit
{
  "metadata": {
    "input_document": "sample.pdf",
    "timestamp": "2025-07-27T14:35:00"
  },
  "document": {
    "title": "Sample Title",
    "outline": [
      {"level": "H1", "text": "Introduction", "page": 1},
      ...
    ]
  },
  "pages": [
    {
      "document": "sample.pdf",
      "page": 1,
      "language": "en",
      "ocr_used": false,
      "text": "Page content here..."
    },
    ...
  ]
}
🛠 Dependencies
Included in requirements.txt:

PyMuPDF

pdfplumber

pdf2image

pytesseract

langdetect

deep-translator

transformers

sentence-transformers

spacy, nltk, pandas, networkx, jsonlines, etc.

💡 Notes
Internet is required the first time the sentence-transformers model is downloaded.

You can cache the HuggingFace models for future offline usage if needed.

Ensure Tesseract and poppler dependencies are available in the Docker base image (handled in the Dockerfile).
