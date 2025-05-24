from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from app.auth.routes import router as auth_router
from app.db.mongo import get_client
from app.auth.utils import handle_validation_error
from app.chat.routes import router as chat_router
from app.sessions.routes import router as sessions_router
from app.llm.openai_client import client as openai_client
app = FastAPI(title="Deep Analysis API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you should restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(chat_router, prefix="/chat", tags=["Chat"])
app.include_router(sessions_router, prefix="/sessions", tags=["Sessions"])
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors using the utility function"""
    return await handle_validation_error(request, exc)

@app.on_event("startup")
async def startup_db_client():
    # Initialize the MongoDB client when the app starts
    await get_client()

@app.on_event("shutdown")
async def shutdown_db_client():
    # Close the MongoDB client when the app shuts down
    from app.db.mongo import client
    if client:
        client.close()
    
    # Reset the OpenAI client
    global openai_client
    openai_client = None

@app.get("/")
async def root():
    return {"message": "Welcome to Deep Analysis API"}