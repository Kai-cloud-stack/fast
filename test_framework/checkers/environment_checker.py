"""
环境检查器模块
Environment Checker Module

通过CAPL用例检查测试环境状态，验证环境的连通性和可用性。
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.utils.logging_system import get_logger


class EnvironmentChecker:
    """
    环境检查器类
    
    负责通过CANoe/CAPL用例检查测试环境的状态，
    验证必要的服务和资源是否可访问。
    """
    
    def __init__(self, canoe_interface, notification_service, config: Dict[str, Any] = None):
        """
        初始化环境检查器
        
        Args:
            canoe_interface: CANoe接口实例
            notification_service: 通知服务实例
            config: 配置字典
        """
        self.canoe_interface = canoe_interface
        self.notification_service = notification_service
        self.config = config or {}
        self.logger = get_logger(__name__)
        self.check_results: Dict[str, Any] = {}
    
    def check_environment(self) -> Dict[str, Any]:
        """
        检查测试环境并返回结果.
        
        首先加载CheckBaseTest.tse并执行Check_Environment用例进行环境检查，
        检查通过后再加载配置文件中的tse文件。
        
        Returns:
            Dict[str, Any]: 环境检查的测试结果.
        """
        self.logger.info("开始环境检查")
        
        try:
            # 启动CANoe并初始化连接
            self.canoe_interface.initialize()
            
            # 第一步：加载CheckBaseTest.tse进行环境检查
            self.logger.info("加载CheckBaseTest.tse进行环境检查")
            # 从配置中获取CheckBaseTest.tse路径
            canoe_config = self.config.get('canoe', {})
            check_base_tse_path = canoe_config.get('check_base_tse_path', 'CheckBaseTest.tse')
            
            # 加载CheckBaseTest.tse
            if not self.canoe_interface.load_test_setup(check_base_tse_path):
                self.logger.error("加载CheckBaseTest.tse失败")
                return {"result": "fail", "error_message": "加载CheckBaseTest.tse失败"}
            
            # 选择Check_Environment用例
            self.canoe_interface.select_test_cases(['Check_Environment'])
            self.canoe_interface.start_measurement()
            
            # 运行环境检查用例
            self.canoe_interface.run_test_modules()
            self.canoe_interface.stop_measurement()
            
            # 获取环境检查结果
            env_check_results = self.canoe_interface.test_results
            self.logger.info(f"环境检查结果: {env_check_results}")
            
            # 检查环境检查是否通过
            if not self._is_environment_check_passed(env_check_results):
                self.logger.error("环境检查未通过，停止后续操作")
                return {"result": "fail", "error_message": "环境检查未通过", "check_results": env_check_results}
            
            self.logger.info("环境检查通过，开始加载配置文件中的tse")
            
            # 第二步：环境检查通过后，加载配置文件中的tse
            # 这里需要从配置中获取tse路径，暂时使用默认的第一个tse
            if not self.canoe_interface.load_test_setup():
                self.logger.error("加载配置文件中的tse失败")
                return {"result": "fail", "error_message": "加载配置文件中的tse失败"}
            
            self.check_results = {
                "result": "pass", 
                "message": "环境检查通过，已成功加载配置tse",
                "env_check_results": env_check_results
            }
            self.logger.info(f"环境检查完成: {self.check_results}")
            return self.check_results
            
        except Exception as e:
            self.logger.error(f"环境检查期间发生异常: {str(e)}")
            # 返回一个表示失败的字典
            return {"result": "fail", "error_message": f"环境检查期间发生异常: {str(e)}"}
    
    def _is_environment_check_passed(self, check_results: Dict[str, Any]) -> bool:
        """
        判断环境检查是否通过
        
        Args:
            check_results: 环境检查结果
            
        Returns:
            bool: 环境检查是否通过
        """
        # 如果结果为空或者包含错误信息，则认为检查失败
        if not check_results or "error" in str(check_results).lower():
            return False
            
        # 检查是否有失败的测试用例
        # 这里需要根据实际的测试结果格式进行判断
        # 假设测试结果中包含pass/fail信息
        if isinstance(check_results, dict):
            if check_results.get("result") == "fail":
                return False
            # 检查是否有测试用例失败
            for key, value in check_results.items():
                if isinstance(value, str) and "fail" in value.lower():
                    return False
                elif isinstance(value, dict) and value.get("result") == "fail":
                    return False
        
        return True
    
    def get_check_results(self) -> Dict[str, Any]:
        """获取检查结果"""
        return self.check_results
