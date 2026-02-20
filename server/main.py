from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import ai_route

app = FastAPI()

app.include_router(ai_route.router, prefix="/api/ai",tags=["AI"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Service"}

@app.get("/health")
def health_check():
    return {"status": "ok"}



