from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import vault, entries, ai_stub, breach_stub, export_stub
from db.database import initialize_database

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vault.router)
app.include_router(entries.router)
app.include_router(ai_stub.router)
app.include_router(breach_stub.router)
app.include_router(export_stub.router)

@app.get("/")
def root():
    return {"status": "ok"}