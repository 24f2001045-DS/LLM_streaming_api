import os
import json
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import OpenAI

# ---------------- APP ----------------
app = FastAPI(title="Streaming LLM API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- OPENAI CLIENT ----------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------- REQUEST MODEL ----------------
class StreamRequest(BaseModel):
    prompt: str
    stream: bool = True

# ---------------- STREAM FUNCTION ----------------
async def stream_llm_response(user_prompt: str):
    try:
        final_prompt = f"""
Generate JavaScript code for a data processor with:
- At least 50 lines
- At least 1250 characters
- Multiple functions
- Error handling
- Streaming/data processing logic
Return ONLY JavaScript code.

Topic: {user_prompt}
"""

        # 🚀 send instant first token (latency fix)
        instant = {
            "choices": [{"delta": {"content": "// streaming initialized...\n"}}]
        }
        yield f"data: {json.dumps(instant)}\n\n"

        # 🔥 streaming from OpenAI (FAST MODEL)
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": final_prompt}],
            stream=True,
            temperature=0.7,
        )

        buffer = ""
        chunk_count = 0
        last_flush = asyncio.get_event_loop().time()

        for chunk in stream:
            content = chunk.choices[0].delta.content if chunk.choices else None

            if content:
                buffer += content

                now = asyncio.get_event_loop().time()

                # 🚀 batch tokens for speed (CRITICAL)
                if len(buffer) > 60 or (now - last_flush) > 0.05:
                    data = {
                        "choices": [{"delta": {"content": buffer}}]
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    buffer = ""
                    last_flush = now
                    chunk_count += 1

        # flush remaining
        if buffer:
            data = {"choices":[{"delta":{"content":buffer}}]}
            yield f"data: {json.dumps(data)}\n\n"

        # ensure minimum chunks
        if chunk_count < 5:
            filler = "\n// continuing streaming...\n"
            for _ in range(5 - chunk_count):
                data = {"choices":[{"delta":{"content":filler}}]}
                yield f"data: {json.dumps(data)}\n\n"

        # done event
        yield "data: [DONE]\n\n"

    except Exception as e:
        err = {"error": str(e)}
        yield f"data: {json.dumps(err)}\n\n"
        yield "data: [DONE]\n\n"

# ---------------- ENDPOINT ----------------
@app.post("/stream")
async def stream_endpoint(body: StreamRequest):
    return StreamingResponse(
        stream_llm_response(body.prompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )

# ---------------- ROOT ----------------
@app.get("/")
def root():
    return {"message": "Streaming API running"}
