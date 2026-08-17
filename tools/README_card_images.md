# 卡牌图片批量拉取工具

## 功能

从 bazaardb.gg 批量拉取所有 Item 和 Skill 卡牌的图片 URL，存储到 `plugins/bazaar_plugin/cache/card_images.json`。

## 使用方法

```bash
cd /opt/qiubot
venv/bin/python3 tools/fetch_card_images.py
```

**首次运行预计耗时**：50~80 分钟（1900+ 张卡牌，1.5~2.5s/张）

**后台运行**：
```bash
nohup venv/bin/python3 tools/fetch_card_images.py > /tmp/fetch_card_images.log 2>&1 &
tail -f /tmp/fetch_card_images.log
```

## 反爬策略

- 复用 `bazaardb_client` 的 curl_cffi + UA池 + TLS指纹伪装
- 1.5s~2.5s 随机请求间隔
- 每 100 张休息 30~60 秒
- 检测 429/403 自动暂停 5 分钟
- 增量更新，已拉取的卡牌会被跳过

## 输出格式

`card_images.json` 结构：
```json
{
  "meta": {
    "version": "17.2",
    "total": 1943,
    "fetched": 1817,
    "skipped": 0,
    "failed": 126,
    "last_update": "2026-08-17T12:30:00Z"
  },
  "cards": {
    "card-uuid-here": {
      "id": "03842226-6605-466f-9ea3-a8a2dbea67e1",
      "internalName": "Atlas",
      "name": "阿特拉斯",
      "type": "Item",
      "art": "https://s.bazaardb.gg/v1/z17.0/...@256.webp",
      "artLarge": "https://s.bazaardb.gg/v1/z17.0/...@400.webp",
      "artBlur": "data:image/webp;base64,...",
      "artKey": "Icon_Item_Atlas",
      "uri": "/card/03842226-6605-466f-9ea3-a8a2dbea67e1/Atlas"
    }
  }
}
```

## 字段说明

| 字段 | 用途 |
|------|------|
| `art` | 256px 缩略图（消息/列表） |
| `artLarge` | 400px 大图（详情页） |
| `artBlur` | base64 模糊占位图（懒加载） |
| `artKey` | GameData.db 本地资源名（备用） |

## 失败的卡牌

约 126 张卡牌拉取失败，主要是：
- DEBUG/TEMPLATE 调试卡（bazaardb 不收录）
- 删除/未实装卡（Unused Card、DELETE）
- 特殊活动门票/社区卡

这些卡不在正式游戏中出现，不影响正常使用。

## 更新频率

- 新赛季/新补丁后需要重新运行
- 脚本会跳过已有卡牌，只拉取新增的
