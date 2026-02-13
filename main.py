import time
import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import openai
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import openai, os, json, asyncio

app = FastAPI()

# 🔥 ENABLE CORS HERE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all (safe for testing)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


openai.api_key = os.getenv("OPENAI_API_KEY")

# helper function to stream chunks
async def stream_llm(prompt: str):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )

        for chunk in response:
            if chunk.choices[0].delta.content:
                data = {
                    "choices": [
                        {
                            "delta": {
                                "content": chunk.choices[0].delta.content
                            }
                        }
                    ]
                }

                yield f"data: {json.dumps(data)}\n\n"
                await asyncio.sleep(0.01)

        yield "data: [DONE]\n\n"

    except Exception as e:
        error_data = {"error": str(e)}
        yield f"data: {json.dumps(error_data)}\n\n"


@app.post("/stream")
async def stream_endpoint(request: Request):
    body = await request.json()
    prompt = body.get("prompt", "")

    return StreamingResponse(
        stream_llm(prompt),
        media_type="text/event-stream"
    )
