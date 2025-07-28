#1A only

import os
import json
import datetime
import re
import fitz
import pdfplumber
from langdetect import detect
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

def detect_language(text):
    try:
        return detect(text)
    except:
        return "unknown"

def extract_pdf_title(pdf_path):
    doc = fitz.open(pdf_path)
    # Try metadata title but clean it
    meta_title = doc.metadata.get("title", "").strip()
    if meta_title and meta_title.lower() not in ["untitled", "", os.path.splitext(os.path.basename(pdf_path))[0].lower()]:
        # Clean up common metadata artifacts
        clean_title = meta_title.replace("Microsoft Word - ", "").replace(".doc", "").replace(".docx", "")
        if clean_title and len(clean_title) > 3:
            return clean_title
    # Fallback: largest heading on first page
    page = doc[0]
    blocks = page.get_text("dict").get("blocks", [])
    largest = (None, 0)
    for block in blocks:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                size = span.get("size", 0)
                if len(text) > 3 and size > largest[1] and not text.isdigit():
                    largest = (text, size)
    if largest[0]:
        return largest[0]
    # Fallback: filename
    return os.path.splitext(os.path.basename(pdf_path))[0]


def base_outline(pdf_path):
    outline = []
    doc = fitz.open(pdf_path)
    # Collect all font sizes to determine relative heading levels
    font_sizes = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict").get("blocks", [])
        for block in blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    size = span.get("size", 0)
                    if size > 0:
                        font_sizes.append(size)
    
    if not font_sizes:
        return outline
    
    # Use more flexible font size detection
    font_sizes = sorted(set(font_sizes))
    if len(font_sizes) >= 4:
        h1_size = font_sizes[-1]  # Largest
        h2_size = font_sizes[-2]  # Second largest
        h3_size = font_sizes[-3]  # Third largest
    elif len(font_sizes) == 3:
        h1_size = font_sizes[-1]
        h2_size = font_sizes[-2]
        h3_size = font_sizes[-3]
    elif len(font_sizes) == 2:
        h1_size = font_sizes[-1]
        h2_size = font_sizes[-2]
        h3_size = font_sizes[-2]  # Same as H2
    else:
        h1_size = h2_size = h3_size = font_sizes[-1]
    
    # More lenient minimum size threshold
    min_size = max(8, min(font_sizes))
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict").get("blocks", [])
        for block in blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    size = span.get("size", 0)
                    
                    # Skip if too small or too short
                    if size < min_size or len(text) < 2:
                        continue
                    
                    # Skip garbage text
                    if (text.isdigit() or 
                        len(text) <= 3 and text.replace('.', '').replace(',', '').isdigit() or
                        text in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'] or
                        any(skip in text.lower() for skip in ["s.no", "rs.", "signature"])):
                        continue
                    
                    # Determine heading level with more flexibility
                    if size >= h1_size * 0.9:  # Allow some tolerance
                        level = "H1"
                    elif size >= h2_size * 0.9:
                        level = "H2"
                    elif size >= h3_size * 0.9:
                        level = "H3"
                    else:
                        continue
                    
                    # Less restrictive length filter
                    if len(text) > 100:  # Skip very long text
                        continue
                    
                    outline.append({"level": level, "text": text, "page": page_num + 1})
    
    return outline


def merge_fragmented_headings(outline):
    """Merge headings that appear to be fragments of the same heading"""
    if not outline:
        return outline
    
    merged = []
    i = 0
    while i < len(outline):
        current = outline[i]
        merged_text = current["text"]
        
        # Look for consecutive headings that might be fragments
        j = i + 1
        while j < len(outline) and outline[j]["page"] == current["page"]:
            next_heading = outline[j]
            # Check if they might be fragments (similar level, short text, not already contained)
            if (next_heading["level"] == current["level"] and 
                len(next_heading["text"]) < 15 and  # Shorter fragments
                not next_heading["text"].startswith(merged_text) and
                not merged_text.endswith(next_heading["text"]) and
                not merged_text.lower() in next_heading["text"].lower() and
                not next_heading["text"].lower() in merged_text.lower() and
                # Check if they form a meaningful phrase
                (merged_text + " " + next_heading["text"]).lower().replace(" ", "").isalpha()):
                merged_text += " " + next_heading["text"]
                j += 1
            else:
                break
        
        merged.append({
            "level": current["level"],
            "text": merged_text,
            "page": current["page"]
        })
        i = j
    
    return merged


def clean_headings(outline):
    """Clean up headings by removing garbage and improving quality"""
    cleaned = []
    for heading in outline:
        text = heading["text"].strip()
        
        # Skip if it's just numbers or garbage
        if (text.isdigit() or 
            len(text) <= 3 and text.replace('.', '').replace(',', '').isdigit() or
            text in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'] or
            len(text) < 3):
            continue
        
        # Skip if it's just punctuation or symbols
        if all(c in '.,;:!?()[]{}' for c in text):
            continue
        
        # Skip if it's just a single word that's too short
        if len(text.split()) == 1 and len(text) < 4:
            continue
        
        cleaned.append(heading)
    
    return cleaned


def fallback_form_outline(pdf_path):
    outline = []
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        lines = page.get_text("text").splitlines()
        for line in lines:
            m = re.match(r'^\s*(?:S\.?No\.?|\d+)[\.)]\s*(.+)', line)
            if m:
                text = m.group(1).strip()
                if text:
                    outline.append({"level": "H2", "text": text, "page": page_num + 1})
    return outline

def fallback_uppercase_outline(pdf_path):
    outline = []
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict").get("blocks", [])
        for block in blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    size = span.get("size", 0)
                    if len(text) > 3 and text.strip():
                        upper_ratio = sum(1 for c in text if c.isupper()) / len(text)
                        if upper_ratio > 0.7 and size > 12:
                            outline.append({"level": "H1", "text": text, "page": page_num + 1})
    return outline

def fallback_table_fields(pdf_path):
    outline = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for table in tables:
                if table and len(table) > 0:
                    header = table[0]
                    title = " | ".join(cell for cell in header if cell and cell.strip())
                    if title:
                        outline.append({"level": "H2", "text": title, "page": page_idx + 1})
    return outline

def extract_outline(pdf_path):
    title = extract_pdf_title(pdf_path)
    
    # Try base outline first
    outline = base_outline(pdf_path)
    
    # Always try fallbacks to get more headings
    fallback_outline = fallback_form_outline(pdf_path)
    if fallback_outline:
        outline.extend(fallback_outline)
    
    fallback_outline = fallback_uppercase_outline(pdf_path)
    if fallback_outline:
        outline.extend(fallback_outline)
    
    fallback_outline = fallback_table_fields(pdf_path)
    if fallback_outline:
        outline.extend(fallback_outline)
    
    # Filter only H1, H2, H3 and remove duplicates
    seen = set()
    filtered_outline = []
    for heading in outline:
        if heading["level"] in ("H1", "H2", "H3"):
            text_key = heading["text"].lower().strip()
            if text_key not in seen:
                seen.add(text_key)
                filtered_outline.append(heading)
    
    # Clean up headings
    filtered_outline = clean_headings(filtered_outline)
    
    # Merge fragmented headings
    filtered_outline = merge_fragmented_headings(filtered_outline)
    
    # Sort by page and then by level for better organization
    filtered_outline.sort(key=lambda x: (x["page"], {"H1": 1, "H2": 2, "H3": 3}[x["level"]]))
    
    return title, filtered_outline

def extract_pages_with_ocr(pdf_path):
    sections = []
    doc = fitz.open(pdf_path)
    with pdfplumber.open(pdf_path) as plumber_pdf:
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Try PyMuPDF 'text' extraction
            text = page.get_text("text").strip()
            # If too little text, try 'blocks' extraction
            if not text or len(text) < 20:
                blocks = page.get_text("blocks")
                block_texts = [b[4].strip() for b in blocks if len(b) > 4 and b[4].strip()]
                text = "\n".join(block_texts)
            # If still not enough, try pdfplumber
            if not text or len(text) < 20:
                if page_num < len(plumber_pdf.pages):
                    plumber_text = plumber_pdf.pages[page_num].extract_text()
                    if plumber_text:
                        text = plumber_text.strip()
            # Extract tables with pdfplumber and append as CSV
            table_texts = []
            if page_num < len(plumber_pdf.pages):
                tables = plumber_pdf.pages[page_num].extract_tables()
                for table in tables:
                    if table:
                        # Convert table to CSV-style string
                        csv_rows = [", ".join(cell if cell is not None else "" for cell in row) for row in table]
                        table_texts.append("\n".join(csv_rows))
            if table_texts:
                text = (text + "\n\n[Extracted Tables:]\n" + "\n\n".join(table_texts)).strip() if text else "[Extracted Tables:]\n" + "\n\n".join(table_texts)
            # If still no text, use OCR
            if not text or len(text) < 10:
                images = convert_from_path(pdf_path, first_page=page_num + 1, last_page=page_num + 1)
                if images:
                    text = pytesseract.image_to_string(images[0])
                    ocr_used = True
                else:
                    text = ""
                    ocr_used = False
            else:
                ocr_used = False
            lang = detect_language(text) if text else "unknown"
            sections.append({
                "document": os.path.basename(pdf_path),
                "page": page_num + 1,
                "language": lang,
                "ocr_used": ocr_used,
                "text": text
            })
    return sections

def main():
    input_dir = "./Challenge_1a/sample_dataset/pdfs"
    output_dir = "./Challenge_1a/sample_dataset/outputs"
    timestamp = datetime.datetime.now(datetime.UTC).isoformat()

    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith(".pdf")]

    for pdf in pdf_files:
        path = os.path.join(input_dir, pdf)
        title, outline = extract_outline(path)
        pages = extract_pages_with_ocr(path)
        output = {
            "metadata": {
                "input_document": pdf,
                "timestamp": timestamp
            },
            "document": {"title": title, "outline": outline},
            "pages": pages
        }
        os.makedirs(output_dir, exist_ok=True)
        # Use the PDF filename (without extension) for the output JSON
        base_name = os.path.splitext(pdf)[0]
        output_path = os.path.join(output_dir, f"final_output_{base_name}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()