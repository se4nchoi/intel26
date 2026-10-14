import json
from pathlib import Path


def read_mountains() -> list:
    # UTF-8 인코딩으로 파일 열기
    current_dir = Path(__file__).resolve().parent.parent
    file_path = current_dir / "mountains.ini"

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def write_mountains(data: list) -> None:
    # UTF-8 인코딩으로 파일 열기
    current_dir = Path(__file__).resolve().parent.parent
    file_path = current_dir / "mountains.ini"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
