from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, matchmaking, game, leaderboard, questions


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(matchmaking.router)  
app.include_router(game.router)
app.include_router(leaderboard.router)
app.include_router(questions.router)

@app.get("/api/v1/health")
def root():
    return {"version": 1, "message": "all services running"}

if __name__ == "__main__":
    import uvicorn
    import os
    os.environ["APP_ENV"] = "dev"
    uvicorn.run(app, host="0.0.0.0", port=8000)