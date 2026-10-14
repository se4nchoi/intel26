from pathlib import Path
from sqlmodel import SQLModel, Field, Session, create_engine, select

DB_PATH = Path(__file__).resolve().parent.parent / "mountains.db"
engine = create_engine(f"sqlite:///{DB_PATH}")


# 1. 모델 정의
class Mountain(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    location: str | None = None
    height: str | None = None


# 2. 테이블 생성
SQLModel.metadata.create_all(engine)


# 3. DB CRUD 함수 정의
def get_mountain_by_name(name: str) -> Mountain | None:
    """이름으로 특정 산행지 1건 조회"""
    with Session(engine) as session:
        statement = select(Mountain).where(Mountain.name == name)
        return session.exec(statement).first()


def get_all_mountains() -> list[Mountain]:
    """전체 산행지 목록 조회"""
    with Session(engine) as session:
        statement = select(Mountain)
        return session.exec(statement).all()


def add_mountain_to_db(name: str, location: str, height: str) -> bool:
    """산행지 등록 (중복 시 False 반환)"""
    with Session(engine) as session:
        # 중복 검사
        exists = session.exec(select(Mountain).where(Mountain.name == name)).first()
        if exists:
            return False

        new_mountain = Mountain(name=name, location=location, height=height)
        session.add(new_mountain)
        session.commit()
        return True


def delete_mountain_from_db(name: str) -> bool:
    """산행지 삭제 (존재하지 않으면 False 반환)"""
    with Session(engine) as session:
        target = session.exec(select(Mountain).where(Mountain.name == name)).first()
        if not target:
            return False

        session.delete(target)
        session.commit()
        return True