"""
环境检查器模块
Environment Checker Module

通过CAPL用例检查测试环境状态，验证环境的连通性和可用性。
"""

import logging
from ..utils.logging_system import get_logger
from typing import Dict, Any, Optional


class EnvironmentChecker:
    """
    环境检查器类
    
    负责通过CANoe/CAPL用例检查测试环境的状态，
    验证必要的服务和资源是否可访问。
    """
    
    def __init__(self, canoe_interface, notification_service):
        """
        初始化环境检查器
        
        Args:
            canoe_interface: CANoe接口实例
            notification_service: 通知服务实例
        """
        self.canoe_interface = canoe_interface
        self.notification_service = notification_service
        self.logger = get_logger(__name__)
        self.check_results: Dict[str, Any] = {}
    
    def check_environment(self) -> Dict[str, Any]:
        """
        检查测试环境并返回结果.
        
        Returns:
            Dict[str, Any]: 环境检查的测试结果.
        """
        self.logger.info("开始环境检查")
        
        try:
            # 启动CANoe并初始化连接
            self.canoe_interface.initialize()
            self.canoe_interface.start_measurement()
            self.canoe_interface.select_test_cases(['Check_Environment'])
            self.canoe_interface.run_test_modules()
            self.canoe_interface.stop_measurement()
            self.check_results = self.canoe_interface.test_results
            self.logger.info(f"环境检查完成: {self.check_results}")
            return self.check_results
            
        except Exception as e:
            self.logger.error(f"环境检查期间发生异常: {str(e)}")
            # 返回一个表示失败的字典
            return {"result": "fail", "error_message": f"环境检查期间发生异常: {str(e)}"}
    
    def get_check_results(self) -> Dict[str, Any]:
        """获取检查结果"""
        return self.check_results
