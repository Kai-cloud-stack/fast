"""
配置管理器模块
Config Manager Module

负责管理系统配置文件的读取、验证和访问，支持主配置文件和任务配置文件的管理。
"""

import json
import os
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.utils.logging_system import get_logger


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
        self.logger = get_logger(__name__)
        
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
            "test_cases": []
        }

    def _load_config(self, config_path: Path, config_name: str) -> Optional[Dict[str, Any]]:
        """通用配置加载方法"""
        try:
            self.logger.info(f"加载{config_name}配置文件: {config_path}")
            if not config_path.exists():
                raise FileNotFoundError(f"{config_name}配置文件不存在: {config_path}")
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.logger.info(f"{config_name}配置文件加载成功")
            return config
            
        except json.JSONDecodeError as e:
            self.logger.error(f"{config_name}配置文件JSON格式错误: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"加载{config_name}配置文件失败: {str(e)}")
            raise

    def load_main_config(self) -> Dict[str, Any]:
        """加载并验证主配置文件"""
        config = self._load_config(self.main_config_path, "主")
        if not self.validate_main_config(config):
            raise ValueError("主配置文件验证失败")
        self.main_config = config
        self.logger.info("主配置文件加载和验证成功")
        return self.main_config

    def load_task_config(self) -> Dict[str, Any]:
        """加载并验证任务配置文件"""
        config = self._load_config(self.task_config_path, "任务")
        if not self.validate_task_config(config):
            raise ValueError("任务配置文件验证失败")
        self.task_config = config
        self.logger.info("任务配置文件加载和验证成功")
        return self.task_config

    def _validate_config(self, config: Dict[str, Any], required_fields: Dict[str, list], config_name: str) -> bool:
        """通用配置验证方法"""
        self.logger.info(f"开始验证{config_name}配置文件")
        for section, fields in required_fields.items():
            if section not in config:
                self.logger.error(f"缺少必需的配置节: {section}")
                return False
            
            section_config = config[section]
            for field in fields:
                if field not in section_config:
                    self.logger.error(f"配置节 {section} 缺少必需字段: {field}")
                    return False
        return True

    def validate_main_config(self, config: Dict[str, Any]) -> bool:
        """验证主配置文件内容"""
        if not self._validate_config(config, self.main_config_required_fields, "主"):
            return False
        
        if not self._validate_main_config_values(config):
            return False
        
        self.logger.info("主配置文件验证通过")
        return True

    def _validate_main_config_values(self, config: Dict[str, Any]) -> bool:
        """验证主配置文件的具体值"""
        canoe_path = config["canoe"]["base_path"]
        if not os.path.exists(canoe_path):
            self.logger.error(f"CANoe基础路径不存在: {canoe_path}")
            return False
        
        email_config = config["email"]
        if not email_config.get("recipient") or not isinstance(email_config["recipient"], str):
            self.logger.error("邮件收件人地址不能为空且必须是字符串")
            return False
        
        log_level = config["logging"]["level"]
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level not in valid_levels:
            self.logger.error(f"无效的日志级别: {log_level}")
            return False
        
        return True

    def validate_task_config(self, config: Dict[str, Any]) -> bool:
        """验证任务配置文件内容"""
        if not self._validate_config(config, self.task_config_required_fields, "任务"):
            return False
        
        if not self._validate_task_config_values(config):
            return False
        
        self.logger.info("任务配置文件验证通过")
        return True

    def _validate_task_config_values(self, config: Dict[str, Any]) -> bool:
        """验证任务配置文件的具体值"""
        testcases = config.get("test_cases", {})
        if isinstance(testcases, dict):
            enabled_settings = testcases.get("enabled", {})
            if isinstance(enabled_settings, dict):
                for key, value in enabled_settings.items():
                    if not isinstance(value, bool):
                        self.logger.error(f"任务配置中 'enabled' 下的 '{key}' 的值必须是布尔类型")
                        return False

        flash_config = config.get("flash_config", {})
        if flash_config:
            if 'enabled' in flash_config and not isinstance(flash_config['enabled'], bool):
                self.logger.error("flash_config中的enabled必须为布尔值")
                return False
            if 'retry' in flash_config and not isinstance(flash_config['retry'], int):
                self.logger.error("flash_config中的retry必须为整数")
                return False
            if 'timeout' in flash_config and not isinstance(flash_config['timeout'], int):
                self.logger.error("flash_config中的timeout必须为整数")
                return False
        
        return True

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取指定配置项的值
        
        Args:
            key: 配置项名称 (e.g., "canoe.base_path")
            default: 默认值
            
        Returns:
            Any: 配置项的值
        """
        if self.main_config is None:
            self.load_main_config()

        keys = key.split('.')
        value = self.main_config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def get_task_config(self, key: str, default: Any = None) -> Any:
        """
        获取任务配置项的值
        
        Args:
            key: 配置项名称
            default: 默认值
            
        Returns:
            Any: 配置项的值
        """
        if self.task_config is None:
            self.load_task_config()

        keys = key.split('.')
        value = self.task_config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default