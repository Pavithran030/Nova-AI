from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.api import webhooks, recovery, audit, reports, simulate

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Nova API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router)
app.include_router(recovery.router)
app.include_router(audit.router)
app.include_router(reports.router)
app.include_router(simulate.router)

@app.get("/")
def root():
    return {"message": "Welcome to Nova API"}
