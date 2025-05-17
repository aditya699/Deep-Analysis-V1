from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from app.auth.routes import router as auth_router
from app.db.mongo import get_client
from app.auth.utils import handle_validation_error

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

@app.get("/")
async def root():
    return {"message": "Welcome to Deep Analysis API"}