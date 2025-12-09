import os
import re
from pathlib import Path
import uuid
import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db")
DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
COLLECTION_NAME = "lecture_transcript"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHUNK_SIZE = 1000  # Approximate tokens

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables!")

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)


def parse_webvtt_content(content):
    """
    Parse WEBVTT format and return list of segments with timestamps and text.
    
    Returns:
        List of dicts: [{"timestamp": "00:01:16.720 --> 00:01:20.360", "text": "..."}, ...]
    """
    segments = []
    lines = content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for timestamp pattern: 00:01:16.720 --> 00:01:20.360
        if '-->' in line:
            timestamp = line
            text_lines = []
            i += 1
            
            # Collect text until next timestamp or empty line
            while i < len(lines):
                text_line = lines[i].strip()
                if not text_line or '-->' in text_line:
                    break
                text_lines.append(text_line)
                i += 1
            
            if text_lines:
                segments.append({
                    "timestamp": timestamp,
                    "text": ' '.join(text_lines)
                })
        else:
            i += 1
    
    return segments


def create_chunks_from_segments(segments, chunk_size=CHUNK_SIZE):
    """
    Combine segments into chunks of approximately chunk_size characters.
    Each chunk keeps track of the timestamp range it covers.
    """
    chunks = []
    current_chunk = []
    current_text = ""
    start_timestamp = None
    end_timestamp = None
    
    for segment in segments:
        # If adding this segment would exceed chunk size, save current chunk
        if current_text and len(current_text) + len(segment['text']) > chunk_size:
            chunks.append({
                "text": current_text,
                "timestamp_start": start_timestamp,
                "timestamp_end": end_timestamp
            })
            current_chunk = []
            current_text = ""
            start_timestamp = None
        
        # Add segment to current chunk
        if not start_timestamp:
            start_timestamp = segment['timestamp'].split('-->')[0].strip()
        end_timestamp = segment['timestamp'].split('-->')[1].strip()
        
        current_text += " " + segment['text'] if current_text else segment['text']
    
    # Add final chunk
    if current_text:
        chunks.append({
            "text": current_text,
            "timestamp_start": start_timestamp,
            "timestamp_end": end_timestamp
        })
    
    return chunks


def ingest_data():
    """
    Ingest all lecture files from data/ folder with proper metadata.
    """
    print(f"\n{'='*60}")
    print("Starting Data Ingestion")
    print(f"{'='*60}\n")
    
    # Initialize ChromaDB
    print(f"Initializing ChromaDB at: {DB_PATH}")
    chroma_client = chromadb.PersistentClient(path=DB_PATH)
    
    # Delete existing collection if it exists
    try:
        chroma_client.delete_collection(name=COLLECTION_NAME)
        print(f"✓ Deleted existing collection: {COLLECTION_NAME}")
    except:
        print(f"No existing collection to delete")
    
    # Create new collection
    embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
        api_key=OPENAI_API_KEY,
        model_name="text-embedding-3-small"
    )
    collection = chroma_client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn
    )
    print(f"✓ Created new collection: {COLLECTION_NAME}\n")
    
    # Walk through data directory
    all_documents = []
    all_metadatas = []
    all_ids = []
    
    data_path = Path(DATA_PATH)
    if not data_path.exists():
        raise ValueError(f"Data directory not found: {DATA_PATH}")
    
    print(f"Scanning data directory: {DATA_PATH}\n")
    
    # Process each course folder
    course_folders = [d for d in data_path.iterdir() if d.is_dir()]
    print(f"Found {len(course_folders)} course(s):\n")
    
    for course_folder in course_folders:
        course_name = course_folder.name
        print(f"\n📚 Processing Course: {course_name}")
        print(f"{'-'*60}")
        
        # Get all .txt files in this course
        lecture_files = list(course_folder.glob("*.txt"))
        print(f"   Found {len(lecture_files)} lecture(s)")
        
        for lecture_file in lecture_files:
            # Extract lecture title from filename (remove .txt)
            lecture_title = lecture_file.stem
            print(f"\n   📖 Lecture: {lecture_title}")
            
            # Read and parse WEBVTT content
            try:
                with open(lecture_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse WEBVTT segments
                segments = parse_webvtt_content(content)
                print(f"      ➜ Parsed {len(segments)} segments")
                
                # Create chunks
                chunks = create_chunks_from_segments(segments)
                print(f"      ➜ Created {len(chunks)} chunks")
                
                # Add chunks to collection data
                for idx, chunk in enumerate(chunks):
                    all_documents.append(chunk['text'])
                    all_metadatas.append({
                        "course": course_name,
                        "lecture": lecture_title,
                        "timestamp_start": chunk['timestamp_start'],
                        "timestamp_end": chunk['timestamp_end'],
                        "chunk_index": idx
                    })
                    all_ids.append(str(uuid.uuid4()))
                
            except Exception as e:
                print(f"      ✗ Error processing {lecture_file.name}: {e}")
                continue
    
    # Add all documents to ChromaDB in batches
    print(f"\n\n{'='*60}")
    print(f"Adding {len(all_documents)} chunks to ChromaDB...")
    print(f"{'='*60}\n")
    
    batch_size = 50
    total_batches = (len(all_documents) + batch_size - 1) // batch_size
    
    for i in range(0, len(all_documents), batch_size):
        end_idx = min(i + batch_size, len(all_documents))
        batch_docs = all_documents[i:end_idx]
        batch_metas = all_metadatas[i:end_idx]
        batch_ids = all_ids[i:end_idx]
        
        batch_num = i // batch_size + 1
        print(f"Processing batch {batch_num}/{total_batches} (chunks {i+1} to {end_idx})...")
        
        try:
            collection.add(
                documents=batch_docs,
                metadatas=batch_metas,
                ids=batch_ids
            )
            print(f"✓ Batch {batch_num} added successfully")
        except Exception as e:
            print(f"✗ Error adding batch {batch_num}: {e}")
    
    print(f"\n{'='*60}")
    print("✅ Ingestion Complete!")
    print(f"{'='*60}")
    print(f"Total Chunks Indexed: {len(all_documents)}")
    print(f"Collection Name: {COLLECTION_NAME}")
    print(f"Database Path: {DB_PATH}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    ingest_data()
