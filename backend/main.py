"""
Mental Health Services API - Main Application

FastAPI application for intelligent mental health service discovery.
Provides AI-powered search and recommendations for mental health services
using LangGraph workflows and vector similarity search.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import health

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

@app.get("/", tags=["Root"])
async def root():
    """
    Welcome endpoint for the Mental Health Services API.
    
    Returns basic API information and status.
    
    Returns:
        dict: Welcome message and API details
    """
    return {
        "message": "Mental Health Services API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "services_count": 599,
        "status": "operational"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)