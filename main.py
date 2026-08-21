import fcntl, sys

# 防止多实例：同时只允许一个 qiubot main.py 运行
_lock_file = open('/tmp/qiubot.lock', 'w')
try:
    fcntl.flock(_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    print('[qiubot] 已有实例在运行，退出。')
    sys.exit(0)

from ncatbot.core import BotClient
import yaml, os

# 读取配置文件（参考 config.example.yaml 创建 config.yaml）
_cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
with open(_cfg_path, encoding="utf-8") as _f:
    _cfg = yaml.safe_load(_f)

_napcat = _cfg.get("napcat", {})

bot = BotClient()
bot.run_frontend(
    ws_uri=_napcat.get("ws_uri", "ws://localhost:3001"),
    ws_token=_napcat.get("ws_token", ""),
    remote_mode=_napcat.get("remote_mode", False)
)
