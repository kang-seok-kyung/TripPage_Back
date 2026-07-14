# seed_places.py
import json
import os
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
import app.models as models

# 8대 데이터 매핑 정보 (SOURCE.md 기반)
JSON_FILES = [
    "구미_경북권_관광지.json", "구미_경북권_레포츠.json", "구미_경북권_문화시설.json",
    "구미_경북권_쇼핑.json", "구미_경북권_숙박.json", "구미_경북권_여행코스.json",
    "구미_경북권_음식점.json", "구미_경북권_축제공연행사.json"
]
DATA_DIR = os.path.join(os.path.dirname(__file__), "app", "data")

def seed_places():
    db: Session = SessionLocal()
    try:
        # 기존 데이터가 있으면 중복 주입 방지하기 위해 비웁니다.
        db.query(models.Place).delete()
        db.commit()
        
        imported_count = 0
        for file_name in JSON_FILES:
            file_path = os.path.join(DATA_DIR, file_name)
            if not os.path.exists(file_path):
                print(f"⚠️ 파일 없음 건너뜀: {file_name}")
                continue
                
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                region = data.get("region", "구미_경북권")
                items = data.get("items", [])
                
                db_items = []
                for item in items:
                    # SCHEMA.md 스키마 명세를 DB 컬럼 타입에 맞춰 파싱
                    db_items.append(models.Place(
                        content_id=item.get("contentid", ""),
                        content_type_id=int(item.get("contenttypeid", 0)),
                        title=item.get("title", "이름 없음"),
                        address=item.get("addr1", "") + " " + item.get("addr2", ""),
                        mapx=float(item.get("mapx", 0)) if item.get("mapx") else 0.0,
                        mapy=float(item.get("mapy", 0)) if item.get("mapy") else 0.0,
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