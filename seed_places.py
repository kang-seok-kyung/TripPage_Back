# seed_places.py (Render 배포 안정성 강화 버전)
import json
import os
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
import app.models as models

JSON_FILES = [
    "구미_경북권_관광지.json", "구미_경북권_레포츠.json", "구미_경북권_문화시설.json",
    "구미_경북권_쇼핑.json", "구미_경북권_숙박.json", "구미_경북권_여행코스.json",
    "구미_경북권_음식점.json", "구미_경북권_축제공연행사.json"
]
DATA_DIR = os.path.join(os.path.dirname(__file__), "app", "data")

TYPE_MAP = {
    12: "관광지",
    14: "문화시설",
    15: "축제공연행사",
    25: "여행코스",
    28: "레포츠",
    32: "숙박",
    38: "쇼핑",
    39: "음식점"
}

def safe_float(val):
    try: return float(val) if val else 0.0
    except ValueError: return 0.0

def safe_int(val):
    try: return int(val) if val else 0
    except ValueError: return 0

def seed_places():
    # ★ [핵심 보완] 배포 환경에서 빈 DB일 경우, 테이블부터 안전하게 자동 생성합니다.
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    try:
        db.query(models.Place).delete()
        db.commit()
        
        imported_count = 0
        for file_name in JSON_FILES:
            file_path = os.path.join(DATA_DIR, file_name)
            if not os.path.exists(file_path):
                continue
                
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                region = data.get("region", "구미_경북권")
                items = data.get("items", [])
                
                db_items = []
                for item in items:
                    db_items.append(models.Place(
                        content_id=str(item.get("contentid", "")),
                        content_type_id=safe_int(item.get("contenttypeid", 0)),
                        content_type=TYPE_MAP.get(safe_int(item.get("contenttypeid", 0)), "기타"),
                        title=item.get("title", "이름 없음"),
                        address=item.get("addr1", "") + " " + item.get("addr2", ""),
                        mapx=safe_float(item.get("mapx", 0.0)),
                        mapy=safe_float(item.get("mapy", 0.0)),
                        image_url=item.get("firstimage") if item.get("firstimage") else None,
                        region=region
                    ))
                
                db.bulk_save_objects(db_items)
                db.commit()
                imported_count += len(db_items)
                print(f"✅ {file_name} -> {len(db_items)}개 데이터 적재 완료")
                
        print(f"🎉 총 {imported_count}개의 8대 공공데이터가 SQLite DB에 완벽히 적재되었습니다!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 데이터 적재 오류 발생: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_places()