# app/routers/places.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from openai import OpenAI
import json
from typing import Optional, List

from app.database import get_db
import app.models as models
import app.schemas as schemas
from app.config import settings

# ★ 태그 이름을 명세서와 DB에 맞게 'places'로 직관적으로 변경합니다.
router = APIRouter(
    prefix="/api",
    tags=["places"]
)

TYPE_CODE_MAP = {
    "관광지": 12, "문화시설": 14, "축제공연행사": 15, "축제": 15,
    "여행코스": 25, "레포츠": 28, "숙박": 32, "쇼핑": 38, "음식점": 39, "맛집": 39
}

LICENSE_FOOTNOTE = (
    "\n\n---\n"
    "이 서비스는 한국관광공사 Tour API(TourAPI 4.0)의 데이터를 활용하였습니다.\n"
    "출처: 한국관광공사 (https://www.data.go.kr/data/15101578/openapi.do)\n"
    "라이선스: 공공누리 제3유형"
)

# 1. 관광지/맛집 데이터 조회 (GET /api/data/places)
@router.get("/data/places", response_model=List[schemas.PlaceResponse])
def get_places(type: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(models.Place)
    if type:
        code = TYPE_CODE_MAP.get(type)
        if code:
            query = query.filter(models.Place.content_type_id == code)
        else:
            raise HTTPException(status_code=400, detail="유효하지 않은 타입 필터입니다.")
    return query.all()

# 2. 챗봇 질의응답 (POST /api/chat)
@router.post("/chat", response_model=schemas.ChatResponse)
def chat_with_ai(req: schemas.ChatRequest, db: Session = Depends(get_db)):
    db_places = db.query(models.Place).limit(5).all()
    chatbot_context = [
        {"장소명": p.title, "타입코드": p.content_type_id, "주소": p.address, "위치": f"({p.mapx}, {p.mapy})"}
        for p in db_places
    ]

    if not settings.OPENAI_API_KEY or "your-actual-openai" in settings.OPENAI_API_KEY:
        user_msg = req.message
        fallback = f"[개발용 DB 연동 테스트 모드]\n질문: {user_msg}\n\nDB 연동 확인된 상위 5개 데이터:\n"
        for p in db_places[:5]:
            fallback += f"- {p.title} (주소: {p.address})\n"
        return {"answer": fallback + LICENSE_FOOTNOTE}

    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        context_str = json.dumps(chatbot_context, ensure_ascii=False)
        
        system_prompt = (
            "당신은 구미_경북권 종합 가이드 AI입니다. 제공된 정형화된 DB 레코드를 토대로 질문에 명확하게 답하세요.\n"
            f"[구미_경북권 실시간 DB 장소 목록]\n{context_str}"
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        for chat in req.history:
            messages.append(chat)
        messages.append({"role": "user", "content": req.message})
        
        response = client.chat.completions.create(model="gpt-5-mini", messages=messages)
        return {"answer": response.choices[0].message.content + LICENSE_FOOTNOTE}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))