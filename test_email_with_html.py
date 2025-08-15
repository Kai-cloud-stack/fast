#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@statement: Copyright(c) 2024 FreeTech Automated Testing CO.LTD
@file     : test_email_with_html.py
@date     : 2024-08-15
@author   : <kai.ren@freetech.com>
@describe : 测试邮件发送功能，验证HTML附件功能
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from test_framework.services.notification_service import NotificationService
from test_framework.utils.logging_system import setup_project_logging

def create_test_html_file() -> Path:
    """
    创建测试用的HTML文件
    
    Returns:
        Path: HTML文件路径
    """
    # 创建临时输出目录
    output_dir = Path("output_test")
    output_dir.mkdir(exist_ok=True)
    
    # 创建测试HTML文件
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>测试报告</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
            .pass {{ color: green; font-weight: bold; }}
            .fail {{ color: red; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>CANoe测试执行报告</h1>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <h2>测试结果</h2>
        <p class="pass">测试用例1: PASS</p>
        <p class="fail">测试用例2: FAIL</p>
        <p class="pass">测试用例3: PASS</p>
        
        <h2>统计信息</h2>
        <p>总测试用例: 3</p>
        <p>通过: 2</p>
        <p>失败: 1</p>
        <p>通过率: 66.67%</p>
    </body>
    </html>
    """
    
    html_file = output_dir / "test_execution_report.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"测试HTML文件已创建: {html_file}")
    return html_file

def test_email_with_html_attachment():
    """
    测试带HTML附件的邮件发送功能
    """
    print("开始测试邮件发送功能（带HTML附件）")
    
    # 初始化日志系统
    setup_project_logging()
    
    # 创建测试HTML文件
    html_file = create_test_html_file()
    
    # 加载配置
    config_file = Path("test_framework/config/main_config.json")
    if not config_file.exists():
        print(f"配置文件不存在: {config_file}")
        return False
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 检查邮件配置
    email_config = config.get('notification', {}).get('email', {})
    notification_config = {
        'email': email_config,
        'wechat': config.get('wechat', {})
    }
    
    if not email_config.get('enabled', False):
        print("邮件功能未启用，跳过测试")
        return True
    
    print(f"邮件配置: {email_config}")
    print(f"收件人: {email_config.get('recipients', [])}")
    
    # 创建通知服务
    notification_service = NotificationService(notification_config)
    
    # 准备测试数据
    test_results = {
        "测试执行时间": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "总测试用例": "3",
        "通过": "2",
        "失败": "1",
        "跳过": "0",
        "通过率": "66.67%",
        "HTML报告": "已生成并作为附件发送"
    }
    
    failed_keywords = {'失败'}
    
    try:
        # 发送带HTML附件的邮件
        print(f"正在发送邮件，HTML附件路径: {html_file}")
        notification_service.send_email(
            subject="CANoe测试报告（带HTML附件）",
            results=test_results,
            failed_keywords=failed_keywords,
            attachment_path=str(html_file)
        )
        
        print("✅ 邮件发送测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 邮件发送测试失败: {e}")
        return False
    
    finally:
        # 清理测试文件
        if html_file.exists():
            html_file.unlink()
            print(f"已清理测试文件: {html_file}")
        
        # 清理测试目录
        output_dir = html_file.parent
        if output_dir.exists() and output_dir.name == "output_test":
            try:
                output_dir.rmdir()
                print(f"已清理测试目录: {output_dir}")
            except OSError:
                print(f"测试目录不为空，跳过清理: {output_dir}")

def main():
    """
    主函数
    """
    print("="*60)
    print("邮件发送功能测试（HTML附件支持）")
    print("="*60)
    
    success = test_email_with_html_attachment()
    
    print("\n" + "="*60)
    if success:
        print("✅ 所有测试通过")
    else:
        print("❌ 测试失败")
    print("="*60)
    
    return success

if __name__ == "__main__":
    main()