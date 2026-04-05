from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import vault, entries, ai_stub, breach_stub, export_stub

from db.database import initialize_database


app = FastAPI()

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

@app.on_event("startup")
def startup_event() -> None:
    initialize_database()

@app.get("/")
def root():
    return {"status": "ok"}

app.include_router(vault.router)
app.include_router(entries.router)
app.include_router(ai_stub.router)
app.include_router(breach_stub.router)
app.include_router(export_stub.router)