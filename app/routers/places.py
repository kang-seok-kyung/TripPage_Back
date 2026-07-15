# app/routers/places.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_  # ★ 키워드 조건 검색(OR 조건)을 위해 새로 추가된 필수 임포트
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

# ========================================================
# 1. 관광지/맛집 데이터 조회 (기존 기능 100% 원본 유지!)
# ========================================================
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

# ========================================================
# 2. 챗봇 질의응답 (RAG 고도화 버전으로 완벽 교체!)
# ========================================================
@router.post("/chat", response_model=schemas.ChatResponse)
def chat_with_ai(req: schemas.ChatRequest, db: Session = Depends(get_db)):
    user_msg = req.message
    
    # --------------------------------------------------------
    # [개발용 가상 테스트 가드 모드]
    # --------------------------------------------------------
    if not settings.OPENAI_API_KEY or "your-actual-openai" in settings.OPENAI_API_KEY:
        # 가상 모드에서도 새로 추가된 content_type 컬럼을 활용해 10개 노출
        db_places = db.query(models.Place).limit(10).all()
        fallback = f"[개발용 DB 연동 테스트 모드]\n질문: {user_msg}\n\nDB 연동 확인된 상위 10개 데이터:\n"
        for p in db_places:
            fallback += f"- [{p.content_type}] {p.title} (주소: {p.address})\n"
        return {"answer": fallback}

    # --------------------------------------------------------
    # [OpenAI 정식 구동 모드]
    # --------------------------------------------------------
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # [STEP 2-1] AI를 이용해 질문 분석 및 검색 조건 JSON 파라미터 추출
        analysis_prompt = (
            "당신은 사용자의 질문을 분석하여 데이터베이스 검색용 JSON 쿼리 파라미터를 생성하는 분석기입니다.\n"
            "반드시 아래의 JSON 형식 규칙을 엄격하게 지켜 응답하세요. 다른 설명이나 텍스트는 절대 포함하지 마십시오.\n\n"
            "응답 포맷 (JSON Only):\n"
            "{\n"
            "  \"region\": \"대구\" 또는 \"구미\" 또는 \"안동\" 또는 \"경주\" 또는 \"포항\" 또는 \"고령\" 등 광역/기초 자치단체 핵심 단어 (없으면 null),\n"
            "  \"district\": \"남구\" 또는 \"중구\" 또는 \"선산읍\" 등 세부 구/군/읍/면 단어 (없으면 null),\n"
            "  \"content_type\": \"음식점\" 또는 \"관광지\" 또는 \"숙박\" 또는 \"축제공연행사\" (질문과 무관하거나 없으면 null),\n"
            "  \"keyword\": \"곱창\", \"카페\", \"갈비\", \"공원\" 등 제목이나 주소에서 찾을 구체적인 핵심 키워드 단어 1개 (없으면 null)\n"
            "}"
        )
        
        analysis_res = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": analysis_prompt},
                {"role": "user", "content": f"질문: {user_msg}"}
            ],
            response_format={"type": "json_object"}  # JSON 포맷 강제 옵션
        )
        
        # AI 분석 결과 파싱
        search_params = json.loads(analysis_res.choices[0].message.content)
        print(f"🔍 AI 분석 검색 조건: {search_params}")  # 터미널 디버깅용 출력

        # [STEP 2-2] 추출된 조건을 바탕으로 SQLAlchemy DB 쿼리 조합 및 실행
        query = db.query(models.Place)
        
        if search_params.get("region"):
            query = query.filter(models.Place.address.contains(search_params["region"]))
        if search_params.get("district"):
            query = query.filter(models.Place.address.contains(search_params["district"]))
        if search_params.get("content_type"):
            query = query.filter(models.Place.content_type == search_params["content_type"])
        if search_params.get("keyword"):
            kw = search_params["keyword"]
            query = query.filter(
                or_(
                    models.Place.title.contains(kw),
                    models.Place.address.contains(kw)
                )
            )

        # ★ 참고 자료(인풋)로 쓸 후보 데이터는 최대 10개 넉넉하게 추출!
        db_places = query.limit(10).all()
        
        # [안전장치] 만약 필터 조건이 너무 세서 검색결과가 없다면, 광역지역 데이터만 10개 살리기
        if not db_places and search_params.get("region"):
            db_places = db.query(models.Place).filter(
                models.Place.address.contains(search_params["region"])
            ).limit(10).all()
            
        # 이마저도 없으면 기본 상위 10개 보장
        if not db_places:
            db_places = db.query(models.Place).limit(10).all()

        # [STEP 2-3] 추출된 10개의 고품질 데이터를 주입하되, 최종 답변은 3~4개로 엄선하도록 AI 제어
        chatbot_context = [
            {"장소명": p.title, "분류": p.content_type, "주소": p.address}
            for p in db_places
        ]
        context_str = json.dumps(chatbot_context, ensure_ascii=False)
        
        system_prompt = (
            "당신은 대구/구미/경북권 여행 및 맛집 전문 가이드 AI입니다.\n"
            "사용자의 질문에 부합하도록, 하단에 제공된 [실시간 DB 장소 목록] 중에서 알맞은 장소를 매칭하여 강력하게 추천해 주어야 합니다.\n"
            "절대 가상의 정보나 허구의 주소를 지어내어 답변하지 마세요.\n"
            "★ 중요 가이드라인: 제공된 목록(최대 10개) 중에서 사용자의 질문 의도에 가장 완벽하게 부합하는 최적의 장소 3~4곳만 엄선하여 가독성 있게 소개해 주세요.\n"
            "목록에 적절한 장소가 없다면, 목록에 있는 다른 대안 장소를 제안하거나 정중히 다른 조건으로 질문해 달라고 안내하세요.\n\n"
            f"[실시간 연동 DB 장소 목록]\n{context_str}"
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        for chat in req.history:
            messages.append(chat)
        messages.append({"role": "user", "content": user_msg})
        
        # 최종 답변 생성 (gpt-5-mini 적용 및 temperature 무관에 따른 옵션 배제)
        response = client.chat.completions.create(
            model="gpt-5-mini", 
            messages=messages
        )
        return {"answer": response.choices[0].message.content}
        
    except Exception as e:
        print(f"⚠️ 챗봇 처리 도중 에러 발생: {e}")
        # API 장애 대비용 가벼운 4개짜리 기본 가이드 목록 출력 안전망
        fallback_msg = "[안내] 실시간 추천 비서에 일시적인 정체가 발생하여 임시 추천 목록을 제공합니다.\n\n"
        for p in db_places[:4]:
            fallback_msg += f"- [{p.content_type}] {p.title} (주소: {p.address})\n"
        return {"answer": fallback_msg}