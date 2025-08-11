"""
配置管理器模块
Config Manager Module

负责管理系统配置文件的读取、验证和访问，支持主配置文件和任务配置文件的管理。
"""

import json
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """
    配置管理器类
    
    负责加载、验证和管理系统配置文件，包括主配置文件和任务配置文件。
    提供配置参数的统一访问接口。
    """
    
    def __init__(self, config_path: str):
        """
        初始化配置管理器
        
        Args:
            config_path: 主配置文件路径
        """
        self.config_path = Path(config_path)
        self.main_config: Optional[Dict[str, Any]] = None
        self.task_config: Optional[Dict[str, Any]] = None
        self.logger = logging.getLogger(__name__)
        
        # 配置文件路径
        self.main_config_path = self.config_path
        self.task_config_path = self.config_path.parent / "task_config.json"
        
        # 配置验证规则
        self._init_validation_rules()
    
    def _init_validation_rules(self) -> None:
        """初始化配置验证规则"""
        self.main_config_required_fields = {
            "canoe": ["base_path", "configuration_path"],
            "email": ["recipient"],
            "logging": ["level", "file_path"],
            "archive": ["base_path"]
        }
        
        self.task_config_required_fields = {
            "task_info": ["name", "version"],
            "test_cases": []  # 至少需要是一个列表
        }
    
    def load_main_config(self) -> Dict[str, Any]:
        """
        加载主配置文件
        
        Returns:
            Dict[str, Any]: 主配置文件内容
            
        Raises:
            FileNotFoundError: 配置文件不存在
            json.JSONDecodeError: 配置文件格式错误
            ValueError: 配置文件内容验证失败
        """
        try:
            self.logger.info(f"加载主配置文件: {self.main_config_path}")
            
            if not self.main_config_path.exists():
                raise FileNotFoundError(f"主配置文件不存在: {self.main_config_path}")
            
            with open(self.main_config_path, 'r', encoding='utf-8') as f:
                self.main_config = json.load(f)
            
            # 验证配置文件
            if not self.validate_main_config(self.main_config):
                raise ValueError("主配置文件验证失败")
            
            self.logger.info("主配置文件加载成功")
            return self.main_config
            
        except json.JSONDecodeError as e:
            self.logger.error(f"主配置文件JSON格式错误: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"加载主配置文件失败: {str(e)}")
            raise
    
    def load_task_config(self) -> Dict[str, Any]:
        """
        加载任务配置文件
        
        Returns:
            Dict[str, Any]: 任务配置文件内容
            
        Raises:
            FileNotFoundError: 配置文件不存在
            json.JSONDecodeError: 配置文件格式错误
            ValueError: 配置文件内容验证失败
        """
        try:
            self.logger.info(f"加载任务配置文件: {self.task_config_path}")
            
            if not self.task_config_path.exists():
                raise FileNotFoundError(f"任务配置文件不存在: {self.task_config_path}")
            
            with open(self.task_config_path, 'r', encoding='utf-8') as f:
                self.task_config = json.load(f)
            
            # 验证配置文件
            if not self.validate_task_config(self.task_config):
                raise ValueError("任务配置文件验证失败")
            
            self.logger.info("任务配置文件加载成功")
            return self.task_config
            
        except json.JSONDecodeError as e:
            self.logger.error(f"任务配置文件JSON格式错误: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"加载任务配置文件失败: {str(e)}")
            raise
    
    def validate_main_config(self, config: Dict[str, Any]) -> bool:
        """
        验证主配置文件内容
        
        Args:
            config: 配置文件内容
            
        Returns:
            bool: 验证是否通过
        """
        try:
            self.logger.info("开始验证主配置文件")
            
            # 检查必需的顶级字段
            for section, required_fields in self.main_config_required_fields.items():
                if section not in config:
                    self.logger.error(f"缺少必需的配置节: {section}")
                    return False
                
                # 检查节内的必需字段
                section_config = config[section]
                for field in required_fields:
                    if field not in section_config:
                        self.logger.error(f"配置节 {section} 缺少必需字段: {field}")
                        return False
            
            # 验证特定字段的值
            if not self._validate_main_config_values(config):
                return False
            
            self.logger.info("主配置文件验证通过")
            return True
            
        except Exception as e:
            self.logger.error(f"验证主配置文件时发生错误: {str(e)}")
            return False
    
    def _validate_main_config_values(self, config: Dict[str, Any]) -> bool:
        """验证主配置文件的具体值"""
        # 验证CANoe基础路径
        canoe_path = config["canoe"]["base_path"]
        if not os.path.exists(canoe_path):
            self.logger.error(f"CANoe基础路径不存在: {canoe_path}")
            return False
        
        # 验证邮件配置
        email_config = config["email"]
        if not email_config.get("recipient") or not isinstance(email_config["recipient"], str):
            self.logger.error("邮件收件人地址不能为空且必须是字符串")
            return False
        
        # 验证日志级别
        log_level = config["logging"]["level"]
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level not in valid_levels:
            self.logger.error(f"无效的日志级别: {log_level}")
            return False
        
        return True
    
    def validate_task_config(self, config: Dict[str, Any]) -> bool:
        """
        验证任务配置文件内容
        
        Args:
            config: 配置文件内容
            
        Returns:
            bool: 验证是否通过
        """
        try:
            self.logger.info("开始验证任务配置文件")
            
            # 检查必需的顶级字段
            for section, required_fields in self.task_config_required_fields.items():
                if section not in config:
                    self.logger.error(f"缺少必需的配置节: {section}")
                    return False
                
                # 检查节内的必需字段
                if required_fields:  # 如果有必需字段
                    section_config = config[section]
                    for field in required_fields:
                        if field not in section_config:
                            self.logger.error(f"配置节 {section} 缺少必需字段: {field}")
                            return False
            
            # 验证测试用例配置
            if not self._validate_test_cases(config.get("test_cases", [])):
                return False
            
            self.logger.info("任务配置文件验证通过")
            return True
            
        except Exception as e:
            self.logger.error(f"验证任务配置文件时发生错误: {str(e)}")
            return False
    
    def _validate_test_cases(self, test_cases: list) -> bool:
        """验证测试用例配置"""
        if not isinstance(test_cases, list):
            self.logger.error("test_cases必须是一个列表")
            return False
        
        if not test_cases:
            self.logger.warning("测试用例列表为空")
            return True
        
        required_fields = ["name", "type", "test_file"]
        for i, test_case in enumerate(test_cases):
            for field in required_fields:
                if field not in test_case:
                    self.logger.error(f"测试用例 {i} 缺少必需字段: {field}")
                    return False
            
            # 验证测试类型
            if test_case["type"] not in ["python", "capl"]:
                self.logger.error(f"测试用例 {i} 类型无效: {test_case['type']}")
                return False
        
        return True
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号分隔的嵌套键
        
        Args:
            key: 配置键，支持点号分隔（如 "canoe.application_path"）
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        try:
            # 首先尝试从主配置获取
            if self.main_config:
                value = self._get_nested_value(self.main_config, key)
                if value is not None:
                    return value
            
            # 然后尝试从任务配置获取
            if self.task_config:
                value = self._get_nested_value(self.task_config, key)
                if value is not None:
                    return value
            
            return default
            
        except Exception as e:
            self.logger.warning(f"获取配置值失败 {key}: {str(e)}")
            return default
    
    def _get_nested_value(self, config: Dict[str, Any], key: str) -> Any:
        """从嵌套字典中获取值"""
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        
        return value
    
    def reload_configs(self) -> bool:
        """
        重新加载所有配置文件
        
        Returns:
            bool: 重新加载是否成功
        """
        try:
            self.logger.info("重新加载配置文件")
            self.load_main_config()
            
            # 任务配置文件可能不存在，不强制要求
            if self.task_config_path.exists():
                self.load_task_config()
            
            return True
            
        except Exception as e:
            self.logger.error(f"重新加载配置文件失败: {str(e)}")
            return False
    
    def get_main_config(self) -> Optional[Dict[str, Any]]:
        """获取主配置文件内容"""
        return self.main_config
    
    def get_task_config(self) -> Optional[Dict[str, Any]]:
        """获取任务配置文件内容"""
        return self.task_config