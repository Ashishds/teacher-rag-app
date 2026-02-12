import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Teacher RAG API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db")
COLLECTION_NAME = "lecture_transcript"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY not set!")

# Initialize Clients
openai_client = OpenAI(api_key=OPENAI_API_KEY)
chroma_client = chromadb.PersistentClient(path=DB_PATH)
embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
    api_key=OPENAI_API_KEY if OPENAI_API_KEY else "dummy",
    model_name="text-embedding-3-small"
)
collection = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=embedding_fn
)

class QueryRequest(BaseModel):
    question: str

class Source(BaseModel):
    course: str
    lecture: str
    timestamp_start: str
    timestamp_end: str
    text: str


class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]

SYSTEM_PROMPT = """You are Andrew Ng, a senior Generative AI instructor conducting a live or recorded classroom session.

You MUST answer questions exactly the way you explain concepts in class – calm, structured, practical, and student-focused.

TEACHING STYLE (VERY IMPORTANT):
- Speak like a real instructor teaching students during a live class or mentoring session
- Clear, slow, and structured explanation
- Frequently guide the student step-by-step
- Use classroom phrases naturally (not excessively), such as:
  - "Okay, so let's understand this step by step"
  - "Now see, the idea here is very simple"
  - "This is exactly what we discussed in the lecture"
  - "Practically, how this works is…"
  - "In real-time projects, this is how you'll use it"
- Avoid dramatic roleplay or emotional exaggeration
- Sound natural, technical, and confident

GROUNDING & ACCURACY (CRITICAL RULES):
- Use ONLY the information provided from lecture transcripts (RAG context)
- Do NOT invent concepts, definitions, tools, or examples not covered in lectures
- Do NOT hallucinate timestamps, lectures, or courses
- If a topic is partially covered, explain only what was discussed and say:
  "We did not go deep into this part in the lecture"
- If a topic is NOT covered, say clearly:
  "This specific topic was not covered in detail in our lectures"

REFERENCE STYLE:
- Refer to lectures naturally, for example:
  - "In the MCP lecture, we discussed…"
  - "When we talked about A2A, the focus was…"
- Do NOT mention chunk IDs or internal references
- The system will show course, lecture title, and timestamp separately

RESPONSE STRUCTURE (FOLLOW THIS ORDER STRICTLY):
1. Classroom Opening  
   - Acknowledge the question briefly  
   - Example: "Good question, this is an important concept"

2. Core Explanation  
   - Explain the concept in simple terms first  
   - Then expand step by step using numbered points  
   - Keep it logical and linear (like a whiteboard explanation)

3. Practical / Real-Life Mapping  
   - Explain how this is used in real projects, systems, or workflows  
   - Match explanation style seen in lectures

4. (Optional) Interview Angle  
   - Only if directly relevant  
   - Keep it short and realistic

5. Closing Summary  
   - 2–3 bullet points titled **"Key Takeaways"**

LANGUAGE:
- Simple professional English
- Very light, natural Hinglish is allowed (for flow only, not slang)
- No emojis
- No marketing tone

ABSOLUTE RESTRICTIONS:
- Do NOT say "as an AI"
- Do NOT say "according to my training"
- Do NOT overly praise or motivate
- Do NOT invent confidence statements

Remember:
You are not acting.
You are teaching — exactly the way the lectures are delivered.
"""

@app.post("/query")
async def query_lecture(request: QueryRequest):
    try:
        from fastapi.responses import StreamingResponse
        import json
        import re
        
        # Define casual/general question patterns
        casual_patterns = [
            r'^(hi|hello|hey|good morning|good afternoon|good evening|greetings)',
            r'^(how are you|how\'s it going|what\'s up|wassup|sup)',
            r'^(who are you|what are you|tell me about yourself)',
            r'^(thank you|thanks|thank|ty)',
            r'^(bye|goodbye|see you|later)',
            r'^(ok|okay|alright|cool|nice)',
        ]
        
        question_lower = request.question.lower().strip()
        
        # Check if it's a general/casual question
        is_casual = any(re.match(pattern, question_lower) for pattern in casual_patterns)
        
        if is_casual:
            # Handle casual conversation without RAG
            async def generate_casual():
                casual_responses = {
                    'greeting': "Hello! I'm your AI Tutor, here to help you learn from Andrew Ng's lectures. Feel free to ask me anything about Generative AI, RAG, Fine-tuning, or any topic from the courses!",
                    'how_are_you': "I'm doing great, thank you for asking! I'm ready to help you understand any concepts from the lectures. What would you like to learn about today?",
                    'who_are_you': "I'm an AI-powered tutor based on Andrew Ng's teaching style. I can help you understand concepts from the Generative AI courses by answering your questions using the lecture transcripts. How can I assist you?",
                    'thanks': "You're very welcome! If you have more questions, I'm always here to help. Keep learning!",
                    'bye': "Goodbye! Feel free to come back anytime you have questions. Happy learning!",
                    'ok': "Great! If you have any questions about the course material, just ask away!"
                }
                
                # Determine response based on question
                if re.match(casual_patterns[0], question_lower):
                    response = casual_responses['greeting']
                elif re.match(casual_patterns[1], question_lower):
                    response = casual_responses['how_are_you']
                elif re.match(casual_patterns[2], question_lower):
                    response = casual_responses['who_are_you']
                elif re.match(casual_patterns[3], question_lower):
                    response = casual_responses['thanks']
                elif re.match(casual_patterns[4], question_lower):
                    response = casual_responses['bye']
                else:
                    response = casual_responses['ok']
                
                # Stream the response character by character
                for char in response:
                    yield f"data: {json.dumps({'type': 'content', 'data': char})}\n\n"
                
                # No sources for casual conversation
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
            return StreamingResponse(generate_casual(), media_type="text/event-stream")
        
        # Original RAG logic for course-related questions
        # 1. Retrieve Context
        results = collection.query(
            query_texts=[request.question],
            n_results=5
        )
        
        documents = results['documents'][0]
        ids = results['ids'][0]
        metadatas = results['metadatas'][0]
        
        context_str = "\n\n".join([f"[ID: {ids[i]}] {doc}" for i, doc in enumerate(documents)])
        
        # 2. Prepare sources for later
        sources = []
        for i in range(len(ids)):
            metadata = metadatas[i]
            sources.append({
                "course": metadata.get("course", "Unknown"),
                "lecture": metadata.get("lecture", "Unknown"),
                "timestamp_start": metadata.get("timestamp_start", "00:00:00.000"),
                "timestamp_end": metadata.get("timestamp_end", "00:00:00.000"),
                "text": documents[i][:200] + "..." if len(documents[i]) > 200 else documents[i]
            })
        
        # 3. Generate Streaming Answer
        async def generate():
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n{context_str}\n\nQuestion: {request.question}"}
            ]
            
            full_answer = ""
            
            # Stream the AI response
            stream = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_answer += content
                    yield f"data: {json.dumps({'type': 'content', 'data': content})}\n\n"
            
            # Add custom closing message FIRST
            closing_message = "\n\n---\n\n*You can follow my lectures where I have discussed these topics in more detail. Here are the references:*\n\n"
            yield f"data: {json.dumps({'type': 'content', 'data': closing_message})}\n\n"
            
            # THEN send sources (they will appear after the message)
            yield f"data: {json.dumps({'type': 'sources', 'data': sources})}\n\n"
            
            # End stream
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")
            
    except Exception as e:
        print(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    return {"status": "ok"}
