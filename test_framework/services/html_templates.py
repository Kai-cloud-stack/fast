"""
HTML邮件模板生成器
"""

from datetime import datetime
from typing import List, Dict, Set, Any

def _get_current_time() -> str:
    """获取当前时间字符串"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _generate_base_template(subject: str, header: str, content: str, footer: str) -> str:
    """生成基础HTML邮件模板"""
    return f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{subject}</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <div style="max-width: 800px; margin: 20px auto; background-color: white; border-radius: 16px; overflow: hidden; box-shadow: 0 8px 32px rgba(0,0,0,0.1);">
            {header}
            {content}
            {footer}
        </div>
    </body>
    </html>
    """

def _generate_table(table_rows: List[str], headers: List[str], base_style: str) -> str:
    """生成HTML表格"""
    header_html = "".join(f'<th style="{base_style} font-weight: 600; font-size: 16px;">{h}</th>' for h in headers)
    return f"""
    <div style="padding: 30px;">
        <table style="width: 100%; border-collapse: collapse; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
            <thead>
                <tr style="background: linear-gradient(135deg, #667eea, #764ba2); color: white;">
                    {header_html}
                </tr>
            </thead>
            <tbody>
                {''.join(table_rows)}
            </tbody>
        </table>
    </div>
    """

def _generate_error_template(subject: str, table_rows: List[str], base_style: str, failed_keywords: Set) -> str:
    """生成错误通知邮件模板"""
    header = f"""
    <div style="background: linear-gradient(135deg, #ff6b6b, #ee5a52); color: white; padding: 20px; border-radius: 8px 8px 0 0;">
        <h1 style="margin: 0; font-size: 24px; text-align: center;">⚠️ 系统错误通知</h1>
        <p style="margin: 10px 0 0 0; text-align: center; opacity: 0.9;">{subject}</p>
    </div>
    """
    content = f"""
    <div style="padding: 30px;">
        <div style="background-color: #fff5f5; border-left: 4px solid #ff6b6b; padding: 15px; margin-bottom: 20px; border-radius: 0 4px 4px 0;">
            <p style="margin: 0; color: #d63031; font-weight: bold;">检测到系统异常，请及时处理！</p>
        </div>
        {_generate_table(table_rows, ["错误项目", "详细信息"], base_style)}
    </div>
    """
    footer = f"""
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px; text-align: center; border-top: 1px solid #dee2e6;">
        <p style="margin: 0; color: #6c757d; font-size: 14px;">FAST 自动化测试平台</p>
        <p style="margin: 5px 0 0 0; color: #dc3545; font-size: 12px;">异常项：{len(failed_keywords)} | 发送时间：{_get_current_time()}</p>
    </div>
    """
    return _generate_base_template(subject, header, content, footer)

def _generate_test_result_template(subject: str, table_rows: List[str], base_style: str, failed_keywords: Set) -> str:
    """生成测试结果邮件模板"""
    success_count = len(table_rows) - len(failed_keywords)
    success_rate = (success_count / len(table_rows) * 100) if table_rows else 0
    
    header = f"""
    <div style="background: linear-gradient(135deg, #4facfe, #00f2fe); color: white; padding: 30px; text-align: center;">
        <h1 style="margin: 0; font-size: 28px; font-weight: 600;">🧪 测试结果报告</h1>
        <p style="margin: 15px 0 0 0; font-size: 18px; opacity: 0.95;">{subject}</p>
    </div>
    """
    content = f"""
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
    {_generate_table(table_rows, ["测试用例", "执行结果"], base_style)}
    """
    footer = f"""
    <div style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 25px; text-align: center;">
        <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">FAST 自动化测试平台</div>
        <div style="font-size: 14px; opacity: 0.9;">测试完成时间：{_get_current_time()}</div>
        <div style="font-size: 12px; opacity: 0.8; margin-top: 8px;">本报告由系统自动生成</div>
    </div>
    """
    return _generate_base_template(subject, header, content, footer)

def _generate_default_template(subject: str, table_rows: List[str], base_style: str, failed_keywords: Set) -> str:
    """生成默认邮件模板"""
    header = f"""
    <div style="background: linear-gradient(135deg, #74b9ff, #0984e3); color: white; padding: 25px; text-align: center;">
        <h1 style="margin: 0; font-size: 24px; font-weight: 400;">📊 系统通知</h1>
        <p style="margin: 12px 0 0 0; font-size: 16px; opacity: 0.9;">{subject}</p>
    </div>
    """
    content = _generate_table(table_rows, ["项目", "信息"], base_style)
    footer = f"""
    <div style="background-color: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #dee2e6;">
        <p style="margin: 0; color: #6c757d; font-size: 14px; font-weight: 500;">FAST 自动化测试平台</p>
        <p style="margin: 8px 0 0 0; color: #868e96; font-size: 12px;">异常项：{len(failed_keywords)} | 发送时间：{_get_current_time()}</p>
    </div>
    """
    return _generate_base_template(subject, header, content, footer)

def generate_html_email(subject: str, table_rows: List[str], base_style: str, failed_keywords: Set) -> str:
    """
    生成HTML邮件模板
    """
    if "Error" in subject or "错误" in subject:
        return _generate_error_template(subject, table_rows, base_style, failed_keywords)
    elif "测试结果" in subject or "Test Result" in subject:
        return _generate_test_result_template(subject, table_rows, base_style, failed_keywords)
    else:
        return _generate_default_template(subject, table_rows, base_style, failed_keywords)