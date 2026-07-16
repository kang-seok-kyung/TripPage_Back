# app/schemas.py
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone, timedelta
from typing import List, Any, Optional

# 한국 표준시 (KST, UTC+9) 정의
KST = timezone(timedelta(hours=9))

# ==========================================
# 1. 커뮤니티 게시판(Posts) 관련 스키마
# ==========================================

# 게시글의 공통 필드를 정의하는 기본 스키마입니다.
class PostBase(BaseModel):
    title: str = Field(..., max_length=100, description="게시글 제목")
    content: str = Field(..., description="게시글 본문 내용")
    author: str = Field("익명", max_length=50, description="작성자 닉네임")
    category: str = Field(..., description="선정된 권역/카테고리")

# 게시글 작성 요청(POST /api/posts) 시 검증에 사용합니다.
class PostCreate(PostBase):
    password: str = Field(..., min_length=1, description="수정/삭제용 평문 비밀번호")

# 게시글 수정 요청(PUT /api/posts/{post_id}) 시 검증에 사용합니다.
class PostUpdate(BaseModel):
    title: str = Field(..., max_length=100)
    content: str = Field(...)
    password: str = Field(..., description="본인 확인용 평문 비밀번호")

# 게시글 상세 조회 및 목록 응답 시 사용합니다.
# ★ 보안 요구사항: 클라이언트에게 응답할 때는 password 필드를 제외하여 평문 비밀번호 유출을 방지합니다.
class PostResponse(PostBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}

    # 💡 [옵션 1 적용] DB에 있는 UTC 시간을 완벽한 한국 시간(+09:00) 문자열로 변환하여 출력합니다.
    @field_validator('created_at', mode='before')
    @classmethod
    def convert_to_kst(cls, v):
        if isinstance(v, datetime):
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            return v.astimezone(KST) # 한국 시간대(+09:00) 정보 적용하여 반환
        return v

# 게시글 목록 조회(GET /api/posts) 시 페이지네이션 응답 구조를 정의합니다.
class PostListResponse(BaseModel):
    posts: List[PostResponse] = Field(..., description="게시글 목록 배열")
    total_pages: int = Field(..., description="총 페이지 수")

# 비밀번호 독립 검증(POST /api/posts/{post_id}/verify) 요청 시 사용합니다.
class PasswordVerifyRequest(BaseModel):
    password: str = Field(..., description="검증할 평문 비밀번호")

# 비밀번호 검증 결과 응답에 사용합니다.
class PasswordVerifyResponse(BaseModel):
    verified: bool = Field(..., description="검증 성공 여부")


# ==========================================
# 2. 챗봇(Chat) 및 추가 데이터 관련 스키마
# ==========================================

# 챗봇 질의응답 요청(POST /api/chat) 시 대화 히스토리 유지를 위해 사용합니다.
class ChatRequest(BaseModel):
    message: str = Field(..., description="사용자 입력 문구")
    history: List[Any] = Field(default=[], description="이전 대화 맥락 배열")

# 챗봇 질의응답 응답 구조입니다.
class ChatResponse(BaseModel):
    answer: str = Field(..., description="AI 답변 텍스트")

# app/schemas.py 에 추가할 코드
class PlaceResponse(BaseModel):
    id: int
    content_id: str
    content_type_id: int
    content_type: str
    title: str
    address: str
    mapx: float
    mapy: float
    image_url: Optional[str] = None
    region: str

    model_config = {"from_attributes": True}