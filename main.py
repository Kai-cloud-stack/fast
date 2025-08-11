#!/usr/bin/env python3
"""
测试框架主入口文件
Test Framework Main Entry Point

演示如何使用测试框架的主控制器。
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from test_framework.core.main_controller import MainController


def main():
    """主函数"""
    try:
        # 配置文件路径
        config_path = project_root / "test_framework" / "config" / "main_config.json"
        
        # 创建主控制器
        controller = MainController(str(config_path))
        
        # 运行测试框架
        success = controller.run()
        
        if success:
            print("测试框架执行成功")
            return 0
        else:
            print("测试框架执行失败")
            return 1
            
    except KeyboardInterrupt:
        print("\n用户中断执行")
        return 1
    except Exception as e:
        print(f"执行过程中发生错误: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)