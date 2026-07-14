# app/routers/posts.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import math
from typing import Optional

from app.database import get_db
import app.models as models
import app.schemas as schemas

router = APIRouter(
    prefix="/api/posts",
    tags=["posts"]
)

# 1. 게시글 작성 (POST /api/posts)
@router.post("", response_model=schemas.PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(post: schemas.PostCreate, db: Session = Depends(get_db)):
    # 평문 비밀번호를 그대로 DB에 저장 (교육 목적 의도된 설계)
    db_post = models.Post(
        title=post.title,
        content=post.content,
        author=post.author,
        password=post.password,  
        category=post.category
    )
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post

# 2. 게시글 목록 조회 (GET /api/posts)
@router.get("", response_model=schemas.PostListResponse)
def read_posts(
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(10, ge=1, le=100, description="페이지당 게시글 수"),
    category: Optional[str] = Query(None, description="권역/카테고리 필터"),
    db: Session = Depends(get_db)
):
    query = db.query(models.Post)
    
    # 카테고리(권역) 필터링 적용
    if category:
        query = query.filter(models.Post.category == category)
        
    # 총 게시글 수 계산 및 총 페이지 수 계산
    total_count = query.count()
    total_pages = math.ceil(total_count / limit) if total_count > 0 else 1
    
    # 최신순 정렬 및 페이지네이션(Offset, Limit) 적용
    posts = query.order_by(models.Post.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {"posts": posts, "total_pages": total_pages}

# 3. 게시글 상세 조회 (GET /api/posts/{post_id})
@router.get("/{post_id}", response_model=schemas.PostResponse)
def read_post(post_id: int, db: Session = Depends(get_db)):
    db_post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    return db_post

# 4. 비밀번호 독립 검증 (POST /api/posts/{post_id}/verify)
@router.post("/{post_id}/verify", response_model=schemas.PasswordVerifyResponse)
def verify_password(post_id: int, req: schemas.PasswordVerifyRequest, db: Session = Depends(get_db)):
    db_post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    
    # 평문 비밀번호 직접 비교
    is_verified = (db_post.password == req.password)
    return {"verified": is_verified}

# 5. 게시글 수정 (PUT /api/posts/{post_id})
@router.put("/{post_id}", response_model=schemas.PostResponse)
def update_post(post_id: int, post_update: schemas.PostUpdate, db: Session = Depends(get_db)):
    db_post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    
    # ★ 백엔드 보안 요구사항: 수정 처리 전 다시 한번 비밀번호 검증 필수
    if db_post.password != post_update.password:
        raise HTTPException(status_code=403, detail="비밀번호가 일치하지 않습니다.")
        
    db_post.title = post_update.title
    db_post.content = post_update.content
    
    db.commit()
    db.refresh(db_post)
    return db_post

# 6. 게시글 삭제 (DELETE /api/posts/{post_id})
@router.delete("/{post_id}")
def delete_post(post_id: int, req: schemas.PasswordVerifyRequest, db: Session = Depends(get_db)):
    db_post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
        
    # ★ 백엔드 보안 요구사항: 삭제 처리 전 다시 한번 비밀번호 검증 필수
    if db_post.password != req.password:
        raise HTTPException(status_code=403, detail="비밀번호가 일치하지 않습니다.")
        
    db.delete(db_post)
    db.commit()
    return {"message": "게시글이 성공적으로 삭제되었습니다."}