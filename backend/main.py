from backend.routes import upload,plots,summary
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.get('/')
def greet():
    return "Hello"
app.head('/')
async def head_root():
    return {}

app.include_router(upload.router)
app.include_router(plots.router)
app.include_router(summary.router)
