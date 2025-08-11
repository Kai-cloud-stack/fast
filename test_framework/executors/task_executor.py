"""
任务执行器模块
Task Executor Module

解析和管理测试任务配置，协调测试任务的执行。
"""

import logging
from typing import Dict, Any, List, Optional


class TaskExecutor:
    """
    任务执行器类
    
    负责解析任务配置文件，管理测试任务的执行顺序和参数。
    """
    
    def __init__(self, config_manager):
        """
        初始化任务执行器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.task_config: Optional[Dict[str, Any]] = None
        self.test_cases: List[Dict[str, Any]] = []
    
    def parse_task_config(self) -> List[Dict[str, Any]]:
        """
        解析任务配置
        
        Returns:
            List[Dict[str, Any]]: 测试用例列表
        """
        self.logger.info("开始解析任务配置")
        
        try:
            # The config is already loaded by main_controller
            self.task_config = self.config_manager.task_config
            if not self.task_config:
                self.logger.error("任务配置未加载")
                return []

            self.test_cases = self.task_config.get("test_cases", [])
            
            self.logger.info(f"解析到 {len(self.test_cases)} 个测试用例")
            return self.test_cases
            
        except Exception as e:
            self.logger.error(f"解析任务配置失败: {str(e)}")
            return []
    
    def should_flash(self) -> bool:
        """
        判断是否需要执行刷写操作
        
        Returns:
            bool: 是否需要刷写
        """
        if not self.task_config:
            return False
        
        flash_config = self.task_config.get("flash_config", {})
        return flash_config.get("enabled", False)
    
    def get_test_cases(self) -> List[Dict[str, Any]]:
        """获取测试用例列表"""
        return self.test_cases