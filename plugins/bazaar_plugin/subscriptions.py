"""
订阅管理 - 读写 subscriptions.json
格式:
{
  "group:123456": ["user1", "user2"],
  "private:ADMIN_QQ_NUMBER": ["user3"]
}
"""
import json
from pathlib import Path

SUBS_FILE = Path(__file__).parent / "cache" / "subscriptions.json"


def _load() -> dict[str, list[str]]:
    if not SUBS_FILE.exists():
        return {}
    try:
        return json.loads(SUBS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: dict[str, list[str]]):
    SUBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUBS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def add_subscription(chat_key: str, username: str) -> bool:
    """添加订阅。返回 True 表示新增,False 表示已存在。"""
    data = _load()
    subs = data.get(chat_key, [])
    username = username.strip().lower()
    if username in subs:
        return False
    subs.append(username)
    data[chat_key] = subs
    _save(data)
    return True


def remove_subscription(chat_key: str, username: str) -> bool:
    """取消订阅。返回 True 表示成功移除,False 表示本来就不存在。"""
    data = _load()
    subs = data.get(chat_key, [])
    username = username.strip().lower()
    if username not in subs:
        return False
    subs.remove(username)
    if not subs:
        data.pop(chat_key, None)
    else:
        data[chat_key] = subs
    _save(data)
    return True


def get_subscriptions(chat_key: str) -> list[str]:
    """获取指定聊天的订阅列表。"""
    data = _load()
    return data.get(chat_key, [])


def get_all_subscriptions() -> dict[str, list[str]]:
    """获取全部订阅。"""
    return _load()
