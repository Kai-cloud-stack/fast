"""
Service for sending notifications like email and WeChat messages.
"""
import win32com.client as win32
import requests
from typing import List, Dict, Any, Set
from ..utils.logging_system import get_logger
from .html_templates import generate_html_email

class NotificationService:
    """
    Service for sending notifications.
    """

    def __init__(self, email_config: Dict[str, Any], wechat_config: Dict[str, Any]):
        """
        Initializes the NotificationService with email and WeChat configurations.

        Args:
            email_config (Dict[str, Any]): Configuration for sending emails.
            wechat_config (Dict[str, Any]): Configuration for sending WeChat messages.
        """
        self.email_config = email_config
        self.wechat_config = wechat_config
        self.logger = get_logger(self.__class__.__name__)

    def send_email(self, subject: str, results: Dict[str, str], failed_keywords: Set[str]) -> None:
        """
        Sends an email with the given subject and results.

        Args:
            subject (str): The subject of the email.
            results (Dict[str, str]): A dictionary containing the results to be included in the email body.
            failed_keywords (Set[str]): A set of keywords that failed.
        """
        if not self.email_config.get("recipient"):
            self.logger.warning("Email recipient not configured. Skipping email notification.")
            return

        try:
            outlook = win32.Dispatch('outlook.application')
            mail = outlook.CreateItem(0)
            mail.To = self.email_config["recipient"]
            mail.Subject = subject
            
            base_style = "padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; color: #333;"
            
            table_rows = []
            for key, value in results.items():
                style = f"{base_style} background-color: #ffdddd;" if key in failed_keywords else base_style
                table_rows.append(f'<tr><td style="{style}">{key}</td><td style="{style}">{value}</td></tr>')

            mail.HTMLBody = generate_html_email(subject, table_rows, base_style, failed_keywords)
            
            mail.Send()
            self.logger.info(f"Email sent to {self.email_config['recipient']} with subject: {subject}")

        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")

    def send_robot_message(self, content: str) -> None:
        """
        Sends a message to a WeChat robot.

        Args:
            content (str): The content of the message to be sent.
        """
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