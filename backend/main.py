from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import health  # Import your route

app = FastAPI(
    title="Mental Health Services Chatbot API",
    description="API for mental health services chatbot with LangGraph integration",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)

@app.get("/")
async def root():
    return {"message": "Mental Health Services Chatbot API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)