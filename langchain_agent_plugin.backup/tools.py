"""
工具定义模块 - LangChain 1.3+ 版本

使用 @tool 装饰器定义工具
"""
import asyncio
from typing import List
from pathlib import Path
import sys

from langchain_core.tools import tool, BaseTool

# 添加项目根目录到 sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def create_tools() -> List[BaseTool]:
    """创建所有可用工具"""
    tools = []

    # ===== 1. Bazaar 游戏数据工具 =====
    try:
        from plugins.bazaar_plugin import gamedata_client
        from plugins.bazaar_plugin.data_client import BazaarDataClient
        
        # 物品/技能数据：使用 GameData.db（本地最新）
        db_path = PROJECT_ROOT / "plugins" / "bazaar_plugin" / "cache" / "GameData.db"
        game_client = gamedata_client.GameDataClient(db_path)
        game_client.load()
        
        # 玩家数据：仍使用 mrmao API（需要实时）
        player_client = BazaarDataClient()
        
        print(f"[Tools] ✓ GameData.db 已加载 ({len(game_client.items())} 物品, {len(game_client.skills())} 技能)")

        @tool
        def query_player(username: str) -> str:
            """查询 The Bazaar 玩家的战绩、段位、胜率等信息。
            
            Args:
                username: 玩家名（字符串）
                
            Returns:
                玩家战绩信息
            """
            try:
                # 同步运行异步代码
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                data = loop.run_until_complete(player_client.get_player(username))
                
                if not data:
                    return f"未找到玩家: {username}"

                # 解析 mrmao API 返回的数据结构
                current_rating = data.get("currentRating", {})
                rating = current_rating.get("rating", "未知")
                position = current_rating.get("position", "未知")

                return f"""玩家 {username} 的战绩：
当前分数: {rating}
排名: #{position}"""
            except Exception as e:
                return f"查询失败: {str(e)}"

        tools.append(query_player)
        print("[Tools] ✓ query_player 工具已加载")

        @tool
        def query_encyclopedia(item_name: str, item_type: str = "item") -> str:
            """查询 The Bazaar 游戏百科信息（物品、技能）。
            
            Args:
                item_name: 物品/技能名称（支持中文和英文）
                item_type: 类型，可选 "item"（物品）或 "skill"（技能），默认 "item"
                
            Returns:
                物品/技能的详细信息
            """
            try:
                from plugins.bazaar_plugin import formatter, matcher
                
                if item_type == "item":
                    # 从 GameData.db 查询
                    item, candidates = matcher.find_one(item_name, game_client.items(), name_field="name")
                    if not item:
                        return f"未找到物品: {item_name}"
                    # 使用 formatter 格式化输出
                    return formatter.format_item(item)
                    
                elif item_type == "skill":
                    # 从 GameData.db 查询
                    skill, candidates = matcher.find_one(item_name, game_client.skills(), name_field="name")
                    if not skill:
                        return f"未找到技能: {item_name}"
                    # 使用 formatter 格式化输出
                    return formatter.format_skill(skill)
                    
                else:
                    return f"不支持的类型: {item_type}，请使用 'item' 或 'skill'"
                    
            except Exception as e:
                return f"查询失败: {str(e)}"

        tools.append(query_encyclopedia)
        print("[Tools] ✓ query_encyclopedia 工具已加载")

        @tool
        def generate_stat_chart(username: str) -> str:
            """生成 The Bazaar 玩家的段位/胜率走势图。
            
            Args:
                username: 玩家名
                
            Returns:
                图表生成结果
            """
            try:
                from plugins.bazaar_plugin import chart
                from plugins.bazaar_plugin.data_client import CURRENT_SEASON_ID
                
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # 1. 先获取玩家统计数据（包含 ratingHistory）
                stat_data = loop.run_until_complete(player_client.get_player_stat(username, CURRENT_SEASON_ID))
                
                if not stat_data:
                    return f"未找到玩家 {username} 的数据"
                
                rating_history = stat_data.get("ratingHistory", [])
                
                if not rating_history:
                    return f"玩家 {username} 没有历史数据"
                
                # 2. 生成图表（同步函数）
                result = chart.generate_stat_chart(username, rating_history)
                
                if result:
                    # 提取文件名（兼容 Windows 和 Linux 路径）
                    import re
                    filename = re.split(r'[/\\]', result)[-1]
                    # 返回带图片标记的结果
                    return f"已生成 {username} 的走势图：\n![走势图](/charts/{filename})"
                else:
                    return f"生成失败"
            except Exception as e:
                return f"生成图表失败: {str(e)}"

        tools.append(generate_stat_chart)
        print("[Tools] ✓ generate_stat_chart 工具已加载")

        # ===== Boss 查询工具 =====
        @tool
        def query_monster(name: str) -> str:
            """查询 The Bazaar 中 Boss/怪物的信息，包括血量、等级、手牌物品列表。

            Args:
                name: Boss/怪物名称（支持英文，模糊匹配）

            Returns:
                Boss 详细信息
            """
            try:
                from plugins.bazaar_plugin import formatter, matcher
                monster, candidates = matcher.find_one(name, game_client.monsters(), name_field="name")
                if not monster:
                    if candidates:
                        names = ", ".join(c.get("name", "") for c in candidates[:5])
                        return f"未找到 Boss「{name}」，相似结果: {names}"
                    return f"未找到 Boss: {name}"
                return formatter.format_monster(monster)
            except Exception as e:
                return f"查询失败: {str(e)}"

        tools.append(query_monster)
        print("[Tools] ✓ query_monster 工具已加载")

        # ===== 附魔台查询工具 =====
        @tool
        def query_pedestal(name: str) -> str:
            """查询 The Bazaar 中附魔台（特殊遭遇地点）的信息，例如 Yetarian Tomb（冰系附魔台）。

            Args:
                name: 附魔台名称（支持英文，模糊匹配）

            Returns:
                附魔台详细信息
            """
            try:
                from plugins.bazaar_plugin import formatter, matcher
                pedestal, candidates = matcher.find_one(name, game_client.pedestals(), name_field="name")
                if not pedestal:
                    if candidates:
                        names = ", ".join(c.get("name", "") for c in candidates[:5])
                        return f"未找到附魔台「{name}」，相似结果: {names}"
                    return f"未找到附魔台: {name}"
                return formatter.format_pedestal(pedestal)
            except Exception as e:
                return f"查询失败: {str(e)}"

        tools.append(query_pedestal)
        print("[Tools] ✓ query_pedestal 工具已加载")

        # ===== 跨类型搜索工具 =====
        @tool
        def search_wiki(keyword: str) -> str:
            """在大巴扎百科中跨物品、技能、Boss、附魔台搜索关键词，返回匹配结果列表。

            Args:
                keyword: 搜索关键词（支持中英文）

            Returns:
                所有匹配结果的列表
            """
            try:
                from plugins.bazaar_plugin import matcher
                results = []

                # 搜索物品
                items = matcher.find_matches(keyword, game_client.items(), name_field="name", limit=3)
                for it in items:
                    results.append(f"[物品] {it.get('name', '')}")

                # 搜索技能
                skills = matcher.find_matches(keyword, game_client.skills(), name_field="name", limit=3)
                for sk in skills:
                    results.append(f"[技能] {sk.get('name', '')}")

                # 搜索 Boss
                monsters = matcher.find_matches(keyword, game_client.monsters(), name_field="name", limit=3)
                for m in monsters:
                    results.append(f"[Boss] {m.get('name', '')} (HP {m.get('health', 0)})")

                # 搜索附魔台
                pedestals = matcher.find_matches(keyword, game_client.pedestals(), name_field="name", limit=3)
                for p in pedestals:
                    results.append(f"[附魔台] {p.get('name', '')}")

                if not results:
                    return f"未找到与「{keyword}」相关的内容"

                return f"搜索「{keyword}」共找到 {len(results)} 条结果:\n" + "\n".join(results)
            except Exception as e:
                return f"搜索失败: {str(e)}"

        tools.append(search_wiki)
        print("[Tools] ✓ search_wiki 工具已加载")

        # ===== BPP 英雄统计工具 =====
        @tool
        def get_hero_rankings() -> str:
            """获取 The Bazaar 各英雄的强度排行榜（按10胜率排序），包含综合胜率、平均天数、结局分布等数据。数据来自 BazaarPlusPlus 社区统计（最近7天）。

            Returns:
                各英雄排行榜
            """
            try:
                from plugins.bazaar_plugin import bpp_client, formatter
                rankings = bpp_client.get_hero_rankings()
                return formatter.format_hero_rankings(rankings)
            except Exception as e:
                return f"获取排行榜失败: {str(e)}"

        tools.append(get_hero_rankings)
        print("[Tools] ✓ get_hero_rankings 工具已加载")

        @tool
        def get_hero_stats(hero_name: str) -> str:
            """获取 The Bazaar 中某个英雄的详细统计数据，包括10胜率、结局分布、对阵胜率、每日胜率走势等。

            Args:
                hero_name: 英雄名称（支持中文或英文），例如"朱尔斯"、"Jules"、"杜利"、"Dooley"

            Returns:
                该英雄的详细统计
            """
            try:
                from plugins.bazaar_plugin import bpp_client, formatter
                detail = bpp_client.get_hero_detail(hero_name)
                return formatter.format_hero_detail(detail)
            except Exception as e:
                return f"获取英雄数据失败: {str(e)}"

        tools.append(get_hero_stats)
        print("[Tools] ✓ get_hero_stats 工具已加载")

        # ===== 每日物品品质概率工具 =====
        DAY_ODDS = {
            1:  {"青铜": 100, "白银": 0,  "黄金": 0,  "钻石": 0},
            2:  {"青铜": 90,  "白银": 10, "黄金": 0,  "钻石": 0},
            3:  {"青铜": 70,  "白银": 30, "黄金": 0,  "钻石": 0},
            4:  {"青铜": 50,  "白银": 50, "黄金": 0,  "钻石": 0},
            5:  {"青铜": 25,  "白银": 75, "黄金": 0,  "钻石": 0},
            6:  {"青铜": 0,   "白银": 95, "黄金": 5,  "钻石": 0},
            7:  {"青铜": 0,   "白银": 80, "黄金": 20, "钻石": 0},
            8:  {"青铜": 0,   "白银": 60, "黄金": 40, "钻石": 0},
            9:  {"青铜": 0,   "白银": 35, "黄金": 60, "钻石": 5},
            10: {"青铜": 0,   "白银": 20, "黄金": 70, "钻石": 10},
        }

        @tool
        def query_day_odds(day: int) -> str:
            """查询 The Bazaar 游戏中某一天商店刷新时各品质物品的出现概率。
            品质从低到高依次为：青铜 < 白银 < 黄金 < 钻石。
            第10天及以后概率相同。

            Args:
                day: 游戏天数（整数，1 及以上）

            Returns:
                该天各品质物品的出现概率
            """
            key = min(day, 10)
            if key < 1:
                return "天数必须大于等于 1"
            odds = DAY_ODDS[key]
            label = f"第 {day} 天" if day <= 10 else f"第 {day} 天（第10天及以后概率相同）"
            lines = [f"🎲 {label} 物品品质概率："]
            for quality, pct in odds.items():
                if pct > 0:
                    bar = "█" * (pct // 5)
                    lines.append(f"  {quality}：{pct}% {bar}")
            return "\n".join(lines)

        tools.append(query_day_odds)
        print("[Tools] ✓ query_day_odds 工具已加载")

    except Exception as e:
        print(f"[Tools] ⚠️ 加载 Bazaar 工具失败: {e}")

    # ===== 2. 网络搜索工具 =====
    try:
        from langchain_community.tools import DuckDuckGoSearchRun
        search_tool = DuckDuckGoSearchRun()
        tools.append(search_tool)
        print("[Tools] ✓ DuckDuckGo 搜索工具已加载")
    except Exception as e:
        print(f"[Tools] ⚠️ 加载 DuckDuckGo 失败: {e}")

    # ===== 3. 计算器工具 =====
    @tool
    def calculator(expression: str) -> str:
        """执行基本数学计算。支持加减乘除、括号。
        
        Args:
            expression: 数学表达式（字符串），例如 "(100 + 50) * 2"
            
        Returns:
            计算结果
        """
        try:
            result = eval(expression, {"__builtins__": {}}, {})
            return f"{expression} = {result}"
        except Exception as e:
            return f"计算错误: {e}"

    tools.append(calculator)
    print("[Tools] ✓ calculator 工具已加载")

    print(f"[Tools] 总共加载 {len(tools)} 个工具")
    return tools


# 测试
if __name__ == "__main__":
    tools = create_tools()
    for t in tools:
        print(f"- {t.name}: {t.description[:50]}...")
