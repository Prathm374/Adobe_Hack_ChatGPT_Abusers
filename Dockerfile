FROM --platform=linux/amd64 python:3.10-slim

WORKDIR /app

# Install OS-level dependencies
RUN apt-get update && \
    apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    git \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install PaddlePaddle for paddleocr
RUN pip install paddlepaddle==2.5.0 -f https://www.paddlepaddle.org.cn/whl/linux/mkl/avx/stable.html

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download NLP model data
RUN python -m nltk.downloader punkt stopwords wordnet averaged_perceptron_tagger && \
    python -m spacy download en_core_web_sm

# Copy your main script
COPY main.py .

# Create expected folder structure
RUN mkdir -p ./Challenge_1a/sample_dataset/pdfs ./Challenge_1a/sample_dataset/outputs

# Run your script
CMD ["python", "main.py"]
