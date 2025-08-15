"""
Service for sending notifications like email and WeChat messages.
"""
import platform
import requests
import sys
from pathlib import Path
from typing import List, Dict, Any, Set, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.utils.logging_system import get_logger
from test_framework.services.html_templates import generate_html_email

# 条件导入Windows特有的模块
if platform.system() == 'Windows':
    try:
        import win32com.client as win32
        WIN32_AVAILABLE = True
    except ImportError:
        WIN32_AVAILABLE = False
        win32 = None
else:
    WIN32_AVAILABLE = False
    win32 = None

class NotificationService:
    """
    Service for sending notifications.
    """

    def __init__(self, notification_config: Dict[str, Any]):
        """
        Initializes the NotificationService with notification configurations.

        Args:
            notification_config (Dict[str, Any]): Configuration for notifications including email and WeChat.
        """
        self.notification_config = notification_config
        self.email_config = notification_config.get('email', {})
        self.wechat_config = notification_config.get('wechat', {})
        self.logger = get_logger(self.__class__.__name__)
        
        # 检查邮件配置是否启用
        self.email_enabled = self.email_config.get('enabled', False)
        # 检查微信配置是否启用  
        self.wechat_enabled = self.wechat_config.get('enable_notification', False)

    def send_email(self, subject: str, results: Dict[str, str], failed_keywords: Set[str]) -> None:
        """
        Sends an email with the given subject and results.

        Args:
            subject (str): The subject of the email.
            results (Dict[str, str]): A dictionary containing the results to be included in the email body.
            failed_keywords (Set[str]): A set of keywords that failed.
        """
        # 检查邮件功能是否启用
        if not self.email_enabled:
            self.logger.info("Email notification is disabled. Skipping email sending.")
            return
            
        # 支持单个收件人(recipient)和多个收件人(recipients)配置
        recipients = self.email_config.get("recipients") or [self.email_config.get("recipient")]
        recipients = [r for r in recipients if r]  # 过滤空值
        
        if not recipients:
            self.logger.warning("Email recipients not configured. Skipping email notification.")
            return

        try:
            outlook = win32.Dispatch('outlook.application')
            mail = outlook.CreateItem(0)
            mail.To = "; ".join(recipients)  # 多个收件人用分号分隔
            mail.Subject = subject
            
            base_style = "padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; color: #333;"
            
            table_rows = []
            for key, value in results.items():
                # 根据测试结果状态设置不同颜色
                result_status = str(value).upper() if hasattr(value, 'name') else str(value).upper()
                
                if 'PASS' in result_status or '通过' in str(value):
                    # PASS - 绿色背景
                    style = f"{base_style} background-color: #d4edda; color: #155724; border-left: 4px solid #28a745;"
                elif 'FAIL' in result_status or '失败' in str(value) or key in failed_keywords:
                    # FAIL - 红色背景
                    style = f"{base_style} background-color: #f8d7da; color: #721c24; border-left: 4px solid #dc3545;"
                elif 'SKIP' in result_status or '跳过' in str(value):
                    # SKIP - 灰色背景
                    style = f"{base_style} background-color: #f8f9fa; color: #6c757d; border-left: 4px solid #6c757d;"
                else:
                    # 默认样式
                    style = base_style
                
                table_rows.append(f'<tr><td style="{style}">{key}</td><td style="{style}">{value}</td></tr>')

            mail.HTMLBody = generate_html_email(subject, table_rows, base_style, failed_keywords)
            
            mail.Send()
            self.logger.info(f"Email sent to {len(recipients)} recipients ({', '.join(recipients)}) with subject: {subject}")

        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")

    def send_robot_message(self, content: str) -> None:
        """
        Sends a message to a WeChat robot.

        Args:
            content (str): The content of the message to be sent.
        """
        # 检查微信功能是否启用
        if not self.wechat_enabled:
            self.logger.info("WeChat notification is disabled. Skipping WeChat message sending.")
            return
            
        if not self.wechat_config.get("webhook_url"):
            self.logger.warning("WeChat webhook URL not configured. Skipping WeChat notification.")
            return

        headers = {"Content-Type": "application/json"}
        data = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        try:
            response = requests.post(self.wechat_config["webhook_url"], headers=headers, json=data, timeout=10)
            response.raise_for_status()
            self.logger.info("WeChat message sent successfully.")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to send WeChat message: {e}")

