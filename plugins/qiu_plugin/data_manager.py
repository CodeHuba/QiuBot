"""
丘Bot 数据管理模块

提供简单的数据持久化功能
"""

import json
import os
from typing import Any, Dict, Optional
from pathlib import Path


class DataManager:
    """数据管理器"""

    def __init__(self, data_dir: str = "data"):
        """
        初始化数据管理器

        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

    def _get_file_path(self, key: str) -> Path:
        """获取数据文件路径"""
        return self.data_dir / f"{key}.json"

    def save(self, key: str, data: Any) -> bool:
        """
        保存数据

        Args:
            key: 数据键名
            data: 要保存的数据

        Returns:
            是否保存成功
        """
        try:
            file_path = self._get_file_path(key)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存数据失败: {e}")
            return False

    def load(self, key: str, default: Any = None) -> Any:
        """
        加载数据

        Args:
            key: 数据键名
            default: 默认值

        Returns:
            加载的数据，如果不存在则返回默认值
        """
        try:
            file_path = self._get_file_path(key)
            if not file_path.exists():
                return default

            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载数据失败: {e}")
            return default

    def delete(self, key: str) -> bool:
        """
        删除数据

        Args:
            key: 数据键名

        Returns:
            是否删除成功
        """
        try:
            file_path = self._get_file_path(key)
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception as e:
            print(f"删除数据失败: {e}")
            return False

    def exists(self, key: str) -> bool:
        """
        检查数据是否存在

        Args:
            key: 数据键名

        Returns:
            是否存在
        """
        return self._get_file_path(key).exists()

    def list_keys(self) -> list:
        """
        列出所有数据键名

        Returns:
            键名列表
        """
        return [f.stem for f in self.data_dir.glob("*.json")]


class UserDataManager:
    """用户数据管理器"""

    def __init__(self, data_dir: str = "data/users"):
        """
        初始化用户数据管理器

        Args:
            data_dir: 用户数据目录
        """
        self.data_manager = DataManager(data_dir)

    def get_user_data(self, user_id: str) -> Dict:
        """
        获取用户数据

        Args:
            user_id: 用户ID

        Returns:
            用户数据字典
        """
        return self.data_manager.load(user_id, {
            "user_id": user_id,
            "nickname": "",
            "level": 1,
            "exp": 0,
            "last_active": None,
            "custom_data": {}
        })

    def save_user_data(self, user_id: str, data: Dict) -> bool:
        """
        保存用户数据

        Args:
            user_id: 用户ID
            data: 用户数据

        Returns:
            是否保存成功
        """
        return self.data_manager.save(user_id, data)

    def update_user_field(self, user_id: str, field: str, value: Any) -> bool:
        """
        更新用户数据字段

        Args:
            user_id: 用户ID
            field: 字段名
            value: 字段值

        Returns:
            是否更新成功
        """
        data = self.get_user_data(user_id)
        data[field] = value
        return self.save_user_data(user_id, data)

    def get_all_users(self) -> list:
        """
        获取所有用户ID

        Returns:
            用户ID列表
        """
        return self.data_manager.list_keys()


class GroupDataManager:
    """群组数据管理器"""

    def __init__(self, data_dir: str = "data/groups"):
        """
        初始化群组数据管理器

        Args:
            data_dir: 群组数据目录
        """
        self.data_manager = DataManager(data_dir)

    def get_group_data(self, group_id: str) -> Dict:
        """
        获取群组数据

        Args:
            group_id: 群组ID

        Returns:
            群组数据字典
        """
        return self.data_manager.load(group_id, {
            "group_id": group_id,
            "name": "",
            "enabled": True,
            "settings": {},
            "custom_data": {}
        })

    def save_group_data(self, group_id: str, data: Dict) -> bool:
        """
        保存群组数据

        Args:
            group_id: 群组ID
            data: 群组数据

        Returns:
            是否保存成功
        """
        return self.data_manager.save(group_id, data)

    def is_group_enabled(self, group_id: str) -> bool:
        """
        检查群组是否启用

        Args:
            group_id: 群组ID

        Returns:
            是否启用
        """
        data = self.get_group_data(group_id)
        return data.get("enabled", True)

    def set_group_enabled(self, group_id: str, enabled: bool) -> bool:
        """
        设置群组启用状态

        Args:
            group_id: 群组ID
            enabled: 是否启用

        Returns:
            是否设置成功
        """
        data = self.get_group_data(group_id)
        data["enabled"] = enabled
        return self.save_group_data(group_id, data)


# 使用示例
if __name__ == "__main__":
    # 测试数据管理器
    dm = DataManager("test_data")

    # 保存数据
    dm.save("test", {"name": "丘bot", "version": "1.0.0"})

    # 加载数据
    data = dm.load("test")
    print("加载的数据:", data)

    # 测试用户数据管理器
    udm = UserDataManager("test_data/users")

    # 获取用户数据
    user_data = udm.get_user_data("123456")
    print("用户数据:", user_data)

    # 更新用户字段
    udm.update_user_field("123456", "nickname", "测试用户")
    print("更新后:", udm.get_user_data("123456"))

    # 清理测试数据
    import shutil
    if os.path.exists("test_data"):
        shutil.rmtree("test_data")
    print("测试完成，已清理测试数据")
