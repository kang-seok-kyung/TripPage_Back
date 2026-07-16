# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
import app.models as models
# ★ chat 대신 변경된 places 라우터를 로드합니다.
from app.routers import posts, places

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG
)

origins = [
    "http://localhost:5173",                 # 로컬 개발용
    "https://trip-page.netlify.app"          # 💡 실제 배포된 Netlify 프론트엔드 주소 추가!
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ★ 라우터 등록 갱신
app.include_router(posts.router)
app.include_router(places.router)  # ★ 깔끔하게 변경 완료!

@app.get("/")
def read_root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}!",
        "status": "Running"
    }