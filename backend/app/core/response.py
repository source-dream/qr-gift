from typing import Any


def ok(data: Any = None, message: str = "ok", code: str = "SUCCESS") -> dict[str, Any]:
    return {"code": code, "message": message, "data": data}
