#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NotificationService 调用示例
演示如何使用通知服务发送邮件和微信消息
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from test_framework.services.notification_service import NotificationService

def main():
    """
    NotificationService 使用示例
    """
    
    # 1. 配置邮件参数
    email_config = {
        "recipient": "test@example.com",  # 收件人邮箱
        "sender": "sender@example.com"    # 发件人邮箱（可选）
    }
    
    # 2. 配置微信机器人参数
    wechat_config = {
        "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_webhook_key"
    }
    
    # 3. 创建通知服务实例
    notification_service = NotificationService(email_config, wechat_config)
    
    # 4. 发送邮件示例
    print("=== 邮件发送示例 ===")
    
    # 测试结果数据
    test_results = {
        "Test_SWDL": "PASS",
        "Test_InnerReleaseVersion": "PASS", 
        "Test_ExternalReleaseVersion": "FAIL",
        "Test_DiagnosticSessionJump": "PASS",
        "Test_DiagServicePositiveResponse": "FAIL",
        "Test_WriteEraseSecurityConst": "PASS"
    }
    
    # 失败的测试用例关键字
    failed_keywords = {"Test_ExternalReleaseVersion", "Test_DiagServicePositiveResponse"}
    
    # 发送测试结果邮件
    try:
        notification_service.send_email(
            subject="CANoe 自动化测试结果报告",
            results=test_results,
            failed_keywords=failed_keywords
        )
        print("✓ 邮件发送成功")
    except Exception as e:
        print(f"✗ 邮件发送失败: {e}")
    
    # 5. 发送微信机器人消息示例
    print("\n=== 微信机器人消息发送示例 ===")
    
    # 构建微信消息内容
    wechat_message = f"""
🤖 CANoe 自动化测试通知

📊 测试结果统计:
• 总测试用例: {len(test_results)}
• 通过: {len([r for r in test_results.values() if r == 'PASS'])}
• 失败: {len([r for r in test_results.values() if r == 'FAIL'])}

❌ 失败的测试用例:
{chr(10).join([f'• {key}' for key in failed_keywords])}

⏰ 测试时间: 2024-01-01 10:00:00
"""
    
    # 发送微信消息
    try:
        notification_service.send_robot_message(wechat_message)
        print("✓ 微信消息发送成功")
    except Exception as e:
        print(f"✗ 微信消息发送失败: {e}")
    
    # 6. 批量通知示例
    print("\n=== 批量通知示例 ===")
    
    def send_batch_notifications(subject: str, results: dict, failed_keywords: set):
        """
        批量发送通知（邮件 + 微信）
        """
        # 发送邮件
        try:
            notification_service.send_email(subject, results, failed_keywords)
            print("✓ 批量通知 - 邮件发送成功")
        except Exception as e:
            print(f"✗ 批量通知 - 邮件发送失败: {e}")
        
        # 发送微信消息
        try:
            # 简化的微信消息
            simple_message = f"""
📋 {subject}

结果: {len([r for r in results.values() if r == 'PASS'])}通过 / {len([r for r in results.values() if r == 'FAIL'])}失败
"""
            notification_service.send_robot_message(simple_message)
            print("✓ 批量通知 - 微信消息发送成功")
        except Exception as e:
            print(f"✗ 批量通知 - 微信消息发送失败: {e}")
    
    # 执行批量通知
    send_batch_notifications(
        subject="每日自动化测试报告",
        results=test_results,
        failed_keywords=failed_keywords
    )
    
    # 7. 错误处理示例
    print("\n=== 错误处理示例 ===")
    
    # 创建一个配置不完整的通知服务
    incomplete_email_config = {"recipient": ""}  # 空收件人
    incomplete_wechat_config = {"webhook_url": ""}  # 空webhook
    
    incomplete_service = NotificationService(incomplete_email_config, incomplete_wechat_config)
    
    # 测试错误处理
    try:
        incomplete_service.send_email("测试邮件", {"test": "result"}, set())
        print("✓ 邮件错误处理正常")
    except Exception as e:
        print(f"✗ 邮件错误处理异常: {e}")
    
    try:
        incomplete_service.send_robot_message("测试微信消息")
        print("✓ 微信错误处理正常")
    except Exception as e:
        print(f"✗ 微信错误处理异常: {e}")

if __name__ == "__main__":
    print("NotificationService 调用示例")
    print("=" * 50)
    
    # 注意：实际使用时需要配置真实的邮箱和微信webhook地址
    print("⚠️  注意：此示例使用模拟配置，实际使用时请配置真实的邮箱和微信webhook地址")
    print()
    
    main()
    
    print("\n" + "=" * 50)
    print("示例执行完成")