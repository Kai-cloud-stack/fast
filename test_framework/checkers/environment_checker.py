"""
环境检查器模块
Environment Checker Module

通过CAPL用例检查测试环境状态，验证环境的连通性和可用性。
"""

import logging
from typing import Dict, Any, Optional


class EnvironmentChecker:
    """
    环境检查器类
    
    负责通过CANoe/CAPL用例检查测试环境的状态，
    验证必要的服务和资源是否可访问。
    """
    
    def __init__(self, canoe_interface):
        """
        初始化环境检查器
        
        Args:
            canoe_interface: CANoe接口实例
        """
        self.canoe_interface = canoe_interface
        self.logger = logging.getLogger(__name__)
        self.check_results: Dict[str, Any] = {}
    
    def check_environment(self) -> bool:
        """
        检查测试环境
        
        Returns:
            bool: 环境检查是否通过
        """
        self.logger.info("开始环境检查")
        
        try:
            from interface.canoe_interface import CANoeInterface
            from utils.notification import send_email, send_robot_message
            
            # 初始化CANoe接口并加载配置
            self.canoe_interface = CANoeInterface(
                config_path=canoe_interface.canoe_config,
                environment=canoe_interface.test_environment
            )
            
            # 启动CANoe并初始化连接
            self.canoe_interface.initialize()
            self.canoe_interface.start_measurement()
            self.canoe_interface.select_test_cases(['Check_Environment'])
            self.canoe_interface.run_test_modules()
            self.canoe_interface.stop_measurement()
            test_results = self.canoe_interface.test_results
            if test_results.get('result') == 'fail':
                # 构建错误消息
                error_msg = f"环境检查失败: {test_results.get('error_message', '未知错误')}"
                
                # 使用通知模板发送邮件
                notification_template = {
                    'subject': "环境检查失败警告",
                    'content': error_msg,
                    'type': 'email'
                }
                send_email(**notification_template)
                
                # 使用通知模板发送机器人消息
                robot_template = {
                    'message': error_msg,
                    'type': 'robot'
                }
                send_robot_message(**robot_template)
                # 中断程序运行
                raise EnvironmentError(error_msg)

            # 实现环境检查逻辑
            # 调用CAPL用例进行环境检查
            return True
            
        except Exception as e:
            self.logger.error(f"环境检查失败: {str(e)}")
            return False
    
    def get_check_results(self) -> Dict[str, Any]:
        """获取检查结果"""
        return self.check_results