import datetime
import json
import re
from typing import Any

import requests

VERSION_NUM_PATTERN = r"^\d{3}\.\d{2}\.\d{2}$"


def check_pattern(pattern: str, string: str) -> bool:
    return re.match(pattern, string) is not None


def read_json(json_file_path: str) -> dict[str, Any]:
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_json(json_file_path: str, data: dict[str, Any]) -> None:
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def convert_effective_date(effective_date: str) -> datetime.date:
    year = int(effective_date[:3]) + 1911
    month = int(effective_date[3:5])
    day = int(effective_date[5:])
    return datetime.date(year, month, day)


def line_notify(acces_token: str | None, message: str) -> None:
    if acces_token is None:
        return
    requests.post(
        "https://notify-api.line.me/api/notify",
        headers={"Authorization": f"Bearer {acces_token}"},
        data={"message": message},
    )
