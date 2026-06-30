#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试插件导入"""

import sys
import traceback

try:
    from plugins.qiu_plugin import QiuPlugin
    print("✓ QiuPlugin 导入成功")
    print(f"  插件名称: {QiuPlugin.name}")
    print(f"  插件版本: {QiuPlugin.version}")
except Exception as e:
    print(f"✗ QiuPlugin 导入失败")
    print(f"  错误类型: {type(e).__name__}")
    print(f"  错误信息: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n所有测试通过！")
