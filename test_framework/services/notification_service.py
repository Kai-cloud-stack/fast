"""
通知服务模块
Notification Service Module

负责发送邮件通知。
"""

import logging
from typing import Dict, Any, List, Optional
import requests
import json
try:
    import win32com.client as win32
except ImportError:
    win32 = None


class NotificationService:
    """
    通知服务类
    
    负责发送各种类型的邮件通知。
    """
    
    def __init__(self, email_config: Optional[Dict[str, Any]] = None, wechat_config: Optional[Dict[str, Any]] = None):
        """
        初始化通知服务
        
        Args:
            email_config: 邮件配置字典，包含收件人等信息
            wechat_config: 微信配置字典，包含webhook地址等信息
        """
        self.logger = logging.getLogger(__name__)
        self.email_config = email_config or {}
        self.wechat_config = wechat_config or {}
        
        # 从配置中获取微信设置
        self.webhook_url = self.wechat_config.get('webhook_url', '')
        self.wechat_timeout = self.wechat_config.get('timeout', 10)
        self.wechat_retry_count = self.wechat_config.get('retry_count', 3)
        self.default_mentioned_users = self.wechat_config.get('default_mentioned_users', [])
        self.wechat_enabled = self.wechat_config.get('enable_notification', True)
    
    def send_email(self, recipient: str, data: Dict[str, Any], subject: str, failed_cases: Optional[List[str]] = None) -> bool:
        """
        发送邮件通知
        
        Args:
            recipient: 收件人邮箱地址
            data: 要发送的数据字典
            subject: 邮件主题
            failed_cases: 失败的测试用例列表
            
        Returns:
            bool: 发送是否成功
        """
        if win32 is None:
            self.logger.error("win32com.client 模块未安装，无法发送邮件")
            return False
            
        try:
            outlook = win32.Dispatch('outlook.application')
            mail = outlook.CreateItem(0)
            mail.Subject = subject
            mail.To = recipient
            
            failed_keywords = set(failed_cases) if failed_cases else set()
            
            # 生成表格内容
            table_rows = []
            for key, value in data.items():
                is_failed = any(fk in key for fk in failed_keywords)
                
                # 合并基础样式和标红样式
                base_style = "padding: 6px 10px; border-bottom: 1px solid #eee;"
                value_style = "color:red; font-weight:bold;" if is_failed else ""
                
                table_rows.append(f'''
                    <tr>
                        <td style="{base_style}">{key}</td>
                        <td style="{base_style} {value_style}">{value}</td>
                    </tr>
                ''')
            
            # 根据邮件类型选择不同的HTML模板
            html_body = self._generate_html_template(subject, table_rows, base_style, failed_keywords)
            
            mail.HTMLBody = html_body
            mail.Send()
            
            self.logger.info(f"邮件发送成功，收件人: {recipient}")
            return True
            
        except Exception as e:
            self.logger.error(f"邮件发送失败: {str(e)}")
            return False
    
    def _generate_html_template(self, subject: str, table_rows: List[str], base_style: str, failed_keywords: set) -> str:
        """
        生成HTML邮件模板
        
        Args:
            subject: 邮件主题
            table_rows: 表格行数据
            base_style: 基础样式
            failed_keywords: 失败关键词集合
            
        Returns:
            str: HTML邮件内容
        """
        # 根据主题选择不同的模板样式
        if "Error" in subject or "错误" in subject:
            return self._generate_error_template(subject, table_rows, base_style, failed_keywords)
        elif "Version" in subject or "版本" in subject:
            return self._generate_version_template(subject, table_rows, base_style, failed_keywords)
        elif "测试结果" in subject or "Test Result" in subject:
            return self._generate_test_result_template(subject, table_rows, base_style, failed_keywords)
        else:
            return self._generate_default_template(subject, table_rows, base_style, failed_keywords)
    
    def _generate_error_template(self, subject: str, table_rows: List[str], base_style: str, failed_keywords: set) -> str:
        """
        生成错误通知邮件模板
        """
        return f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{subject}</title>
        </head>
        <body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 20px auto; background-color: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <!-- 头部 -->
                <div style="background: linear-gradient(135deg, #ff6b6b, #ee5a52); color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                    <h1 style="margin: 0; font-size: 24px; text-align: center;">⚠️ 系统错误通知</h1>
                    <p style="margin: 10px 0 0 0; text-align: center; opacity: 0.9;">{subject}</p>
                </div>
                
                <!-- 内容区域 -->
                <div style="padding: 30px;">
                    <div style="background-color: #fff5f5; border-left: 4px solid #ff6b6b; padding: 15px; margin-bottom: 20px; border-radius: 0 4px 4px 0;">
                        <p style="margin: 0; color: #d63031; font-weight: bold;">检测到系统异常，请及时处理！</p>
                    </div>
                    
                    <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                        <thead>
                            <tr style="background-color: #f8f9fa;">
                                <th style="{base_style} font-weight: bold; color: #495057;">错误项目</th>
                                <th style="{base_style} font-weight: bold; color: #495057;">详细信息</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(table_rows)}
                        </tbody>
                    </table>
                </div>
                
                <!-- 页脚 -->
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px; text-align: center; border-top: 1px solid #dee2e6;">
                    <p style="margin: 0; color: #6c757d; font-size: 14px;">FAST 自动化测试平台</p>
                    <p style="margin: 5px 0 0 0; color: #dc3545; font-size: 12px;">异常项：{len(failed_keywords)} | 发送时间：{self._get_current_time()}</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _generate_version_template(self, subject: str, table_rows: List[str], base_style: str, failed_keywords: set) -> str:
        """
        生成版本信息邮件模板
        """
        return f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{subject}</title>
        </head>
        <body style="margin: 0; padding: 0; background-color: #f0f2f5; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
            <div style="max-width: 700px; margin: 30px auto; background-color: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
                <!-- 头部 -->
                <div style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 25px; text-align: center;">
                    <h1 style="margin: 0; font-size: 26px; font-weight: 300;">📋 版本信息报告</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9; font-size: 16px;">{subject}</p>
                </div>
                
                <!-- 统计卡片 -->
                <div style="padding: 20px; background: linear-gradient(90deg, #f093fb 0%, #f5576c 100%); margin: 0;">
                    <div style="display: flex; justify-content: space-around; text-align: center;">
                        <div style="color: white;">
                            <div style="font-size: 24px; font-weight: bold;">{len(table_rows)}</div>
                            <div style="font-size: 12px; opacity: 0.9;">总检查项</div>
                        </div>
                        <div style="color: white;">
                            <div style="font-size: 24px; font-weight: bold; color: #ffeb3b;">{len(failed_keywords)}</div>
                            <div style="font-size: 12px; opacity: 0.9;">异常项</div>
                        </div>
                    </div>
                </div>
                
                <!-- 内容区域 -->
                <div style="padding: 30px;">
                    <table style="width: 100%; border-collapse: collapse; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                        <thead>
                            <tr style="background: linear-gradient(135deg, #667eea, #764ba2); color: white;">
                                <th style="{base_style} font-weight: 500;">组件名称</th>
                                <th style="{base_style} font-weight: 500;">版本状态</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(table_rows)}
                        </tbody>
                    </table>
                </div>
                
                <!-- 页脚 -->
                <div style="background: linear-gradient(135deg, #f093fb, #f5576c); color: white; padding: 20px; text-align: center;">
                    <p style="margin: 0; font-size: 16px; font-weight: 500;">FAST 自动化测试平台</p>
                    <p style="margin: 8px 0 0 0; font-size: 13px; opacity: 0.9;">报告生成时间：{self._get_current_time()}</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _generate_test_result_template(self, subject: str, table_rows: List[str], base_style: str, failed_keywords: set) -> str:
        """
        生成测试结果邮件模板
        """
        success_count = len(table_rows) - len(failed_keywords)
        success_rate = (success_count / len(table_rows) * 100) if table_rows else 0
        
        return f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{subject}</title>
        </head>
        <body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            <div style="max-width: 800px; margin: 20px auto; background-color: white; border-radius: 16px; overflow: hidden; box-shadow: 0 8px 32px rgba(0,0,0,0.1);">
                <!-- 头部 -->
                <div style="background: linear-gradient(135deg, #4facfe, #00f2fe); color: white; padding: 30px; text-align: center;">
                    <h1 style="margin: 0; font-size: 28px; font-weight: 600;">🧪 测试结果报告</h1>
                    <p style="margin: 15px 0 0 0; font-size: 18px; opacity: 0.95;">{subject}</p>
                </div>
                
                <!-- 统计面板 -->
                <div style="padding: 25px; background: linear-gradient(135deg, #667eea, #764ba2);">
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; text-align: center;">
                        <div style="background: rgba(255,255,255,0.2); padding: 20px; border-radius: 12px; color: white;">
                            <div style="font-size: 32px; font-weight: bold; margin-bottom: 8px;">{len(table_rows)}</div>
                            <div style="font-size: 14px; opacity: 0.9;">总测试项</div>
                        </div>
                        <div style="background: rgba(255,255,255,0.2); padding: 20px; border-radius: 12px; color: white;">
                            <div style="font-size: 32px; font-weight: bold; margin-bottom: 8px; color: #4ade80;">{success_count}</div>
                            <div style="font-size: 14px; opacity: 0.9;">成功项</div>
                        </div>
                        <div style="background: rgba(255,255,255,0.2); padding: 20px; border-radius: 12px; color: white;">
                            <div style="font-size: 32px; font-weight: bold; margin-bottom: 8px; color: #f87171;">{len(failed_keywords)}</div>
                            <div style="font-size: 14px; opacity: 0.9;">失败项</div>
                        </div>
                    </div>
                    <div style="margin-top: 20px; text-align: center; color: white;">
                        <div style="font-size: 24px; font-weight: bold;">成功率: {success_rate:.1f}%</div>
                    </div>
                </div>
                
                <!-- 详细结果 -->
                <div style="padding: 30px;">
                    <h3 style="color: #374151; margin-bottom: 20px; font-size: 20px;">详细测试结果</h3>
                    <table style="width: 100%; border-collapse: collapse; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
                        <thead>
                            <tr style="background: linear-gradient(135deg, #667eea, #764ba2); color: white;">
                                <th style="{base_style} font-weight: 600; font-size: 16px;">测试用例</th>
                                <th style="{base_style} font-weight: 600; font-size: 16px;">执行结果</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(table_rows)}
                        </tbody>
                    </table>
                </div>
                
                <!-- 页脚 -->
                <div style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 25px; text-align: center;">
                    <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">FAST 自动化测试平台</div>
                    <div style="font-size: 14px; opacity: 0.9;">测试完成时间：{self._get_current_time()}</div>
                    <div style="font-size: 12px; opacity: 0.8; margin-top: 8px;">本报告由系统自动生成</div>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _generate_default_template(self, subject: str, table_rows: List[str], base_style: str, failed_keywords: set) -> str:
        """
        生成默认邮件模板
        """
        return f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{subject}</title>
        </head>
        <body style="margin: 0; padding: 20px; background-color: #f7f8fc; font-family: 'Helvetica Neue', Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); overflow: hidden;">
                <!-- 头部 -->
                <div style="background: linear-gradient(135deg, #74b9ff, #0984e3); color: white; padding: 25px; text-align: center;">
                    <h1 style="margin: 0; font-size: 24px; font-weight: 400;">📊 系统通知</h1>
                    <p style="margin: 12px 0 0 0; font-size: 16px; opacity: 0.9;">{subject}</p>
                </div>
                
                <!-- 内容 -->
                <div style="padding: 25px;">
                    <table style="width: 100%; border-collapse: collapse; border-radius: 6px; overflow: hidden; border: 1px solid #e9ecef;">
                        <thead>
                            <tr style="background-color: #f8f9fa;">
                                <th style="{base_style} font-weight: 600; color: #495057;">项目</th>
                                <th style="{base_style} font-weight: 600; color: #495057;">信息</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(table_rows)}
                        </tbody>
                    </table>
                </div>
                
                <!-- 页脚 -->
                <div style="background-color: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #dee2e6;">
                    <p style="margin: 0; color: #6c757d; font-size: 14px; font-weight: 500;">FAST 自动化测试平台</p>
                    <p style="margin: 8px 0 0 0; color: #868e96; font-size: 12px;">异常项：{len(failed_keywords)} | 发送时间：{self._get_current_time()}</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _get_current_time(self) -> str:
        """
        获取当前时间字符串
        
        Returns:
            str: 格式化的当前时间
        """
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def send_wechat_notification(self, content: str, mentioned_mobile_list: List[str] = None) -> bool:
        """
        发送微信机器人通知
        
        Args:
            content: 通知内容
            mentioned_mobile_list: 需要@的用户手机号列表，传入["@all"]可@所有人
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 检查微信通知是否启用
            if not self.wechat_enabled:
                self.logger.info("微信通知功能已禁用")
                return False
                
            # 从配置中获取企业微信机器人webhook地址
            webhook_url = self.webhook_url
            if not webhook_url:
                self.logger.error("未配置微信webhook地址")
                return False
            
            # 构建消息数据
            data = {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }
            
            # 如果指定了需要@的用户
            if mentioned_mobile_list:
                data["text"]["mentioned_mobile_list"] = mentioned_mobile_list
            
            # 发送请求
            response = requests.post(
                webhook_url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
                timeout=self.wechat_timeout
            )
            
            # 检查响应
            if response.status_code == 200:
                result = response.json()
                if result.get("errcode") == 0:
                    self.logger.info("微信通知发送成功")
                    return True
                else:
                    self.logger.error(f"微信通知发送失败: {result.get('errmsg', '未知错误')}")
                    return False
            else:
                self.logger.error(f"微信通知请求失败: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"微信通知网络请求异常: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"微信通知发送异常: {str(e)}")
            return False
    
    def send_wechat_test_result(self, test_results: List[Dict[str, Any]], 
                               mentioned_mobile_list: List[str] = None) -> bool:
        """
        发送测试结果到微信群
        
        Args:
            test_results: 测试结果列表，每个元素包含name和result字段
            mentioned_mobile_list: 需要@的用户手机号列表
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 统计测试结果
            total_tests = len(test_results)
            failed_tests = [test for test in test_results if "失败" in str(test.get('result', '')) or "Failed" in str(test.get('result', '')) or "❌" in str(test.get('result', ''))]
            success_tests = total_tests - len(failed_tests)
            success_rate = (success_tests / total_tests * 100) if total_tests > 0 else 0
            
            # 构建消息内容
            content = f"🧪 CANoe自动化测试结果报告\n\n"
            content += f"📊 测试统计:\n"
            content += f"• 总测试项: {total_tests}\n"
            content += f"• 成功项: {success_tests}\n"
            content += f"• 失败项: {len(failed_tests)}\n"
            content += f"• 成功率: {success_rate:.1f}%\n\n"
            
            # 如果有失败的测试，列出详情
            if failed_tests:
                content += f"❌ 失败测试项:\n"
                for test in failed_tests[:5]:  # 最多显示5个失败项
                    content += f"• {test.get('name', '未知测试')}\n"
                if len(failed_tests) > 5:
                    content += f"• ... 还有{len(failed_tests) - 5}个失败项\n"
                content += "\n"
            
            content += f"⏰ 测试完成时间: {self._get_current_time()}\n"
            content += f"🤖 FAST自动化测试平台"
            
            # 使用配置的默认提醒用户，如果为空则不@任何人
            if mentioned_mobile_list is None:
                mentioned_mobile_list = self.default_mentioned_users or []
            
            return self.send_wechat_notification(content, mentioned_mobile_list)
            
        except Exception as e:
            self.logger.error(f"发送微信测试结果失败: {str(e)}")
            return False
    
    def send_wechat_error_notification(self, error_info: Dict[str, Any], 
                                     mentioned_mobile_list: List[str] = None) -> bool:
        """
        发送错误通知到微信群
        
        Args:
            error_info: 错误信息字典
            mentioned_mobile_list: 需要@的用户手机号列表
            
        Returns:
            bool: 发送是否成功
        """
        try:
            content = f"⚠️ CANoe系统异常通知\n\n"
            content += f"🔴 错误类型: {error_info.get('error_type', '未知错误')}\n"
            content += f"📝 错误描述: {error_info.get('error_message', '无详细信息')}\n"
            
            if error_info.get('component'):
                content += f"🔧 相关组件: {error_info['component']}\n"
            
            if error_info.get('timestamp'):
                content += f"⏰ 发生时间: {error_info['timestamp']}\n"
            else:
                content += f"⏰ 发生时间: {self._get_current_time()}\n"
            
            content += f"\n🚨 请及时处理！\n"
            content += f"🤖 FAST自动化测试平台"
            
            # 使用配置的默认提醒用户，如果为空则不@任何人
            if mentioned_mobile_list is None:
                mentioned_mobile_list = self.default_mentioned_users or []
            
            return self.send_wechat_notification(content, mentioned_mobile_list)
            
        except Exception as e:
            self.logger.error(f"发送微信错误通知失败: {str(e)}")
            return False
    
    def send_error_notification(self, error_info: Dict[str, Any]) -> bool:
        """
        发送错误通知
        
        Args:
            error_info: 错误信息
            
        Returns:
            bool: 发送是否成功
        """
        self.logger.info("发送错误通知邮件")
        
        try:
            # 使用send_email方法发送错误通知
            recipient = self.email_config.get('recipient', '')
            subject = "测试框架错误通知"
            
            if recipient:
                return self.send_email(recipient, error_info, subject)
            else:
                self.logger.warning("未配置收件人邮箱地址")
                return False
            
        except Exception as e:
            self.logger.error(f"发送错误通知失败: {str(e)}")
            return False
    
    def send_test_result_notification(self, test_results: Dict[str, Any], failed_cases: Optional[List[str]] = None) -> bool:
        """
        发送测试结果通知
        
        Args:
            test_results: 测试结果数据
            failed_cases: 失败的测试用例列表
            
        Returns:
            bool: 发送是否成功
        """
        try:
            recipient = self.email_config.get('recipient', '')
            subject = "Version Error or Not read Version" if failed_cases else "测试结果报告"
            
            if recipient:
                return self.send_email(recipient, test_results, subject, failed_cases)
            else:
                self.logger.warning("未配置收件人邮箱地址")
                return False
                
        except Exception as e:
            self.logger.error(f"发送测试结果通知失败: {str(e)}")
            return False