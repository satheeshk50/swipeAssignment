from fastapi import FastAPI
from app.routers import ai_route



app = FastAPI()


app.include_router(ai_route.router, prefix="/api/ai", tags=["AI"])  


@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/health")
def health_check():
    return {"status": "ok"}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8085)