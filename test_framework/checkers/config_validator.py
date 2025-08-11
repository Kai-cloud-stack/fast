"""
配置验证器模块
Config Validator Module

通过CAPL用例验证配置文件的存在性和正确性。
"""

import logging
from typing import Dict, Any, Optional


class ConfigValidator:
    """
    配置验证器类
    
    负责通过CANoe/CAPL用例验证配置文件的存在性和正确性。
    """
    
    def __init__(self, canoe_interface):
        """
        初始化配置验证器
        
        Args:
            canoe_interface: CANoe接口实例
        """
        self.canoe_interface = canoe_interface
        self.logger = logging.getLogger(__name__)
        self.validation_results: Dict[str, Any] = {}
    
    def validate_config(self) -> bool:
        """
        验证配置文件
        
        Returns:
            bool: 配置验证是否通过
        """
        self.logger.info("开始配置文件验证")
        
        try:
            # 检查json文件是否存在
            if not os.path.exists(self.config_path):
                self.logger.error(f"配置文件不存在: {self.config_path}")
                self.validation_results['file_exists'] = False
                return False
            
            # 验证json格式
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                self.validation_results['json_format'] = True
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON格式错误: {str(e)}")
                self.validation_results['json_format'] = False
                return False
            
            # 验证配置内容
            validation_passed = True
            self.validation_results['content_check'] = {}
            
            # 检查开关配置的布尔值
            for key, value in config_data.get('task_config', {}).get('testcases', {}).get('enabled', {}).items():
                if not isinstance(value, bool):
                    self.logger.error(f"开关配置 '{key}' 的值必须是布尔类型")
                    # 检查flash_config中的配置项
                    if key.startswith('flash_config'):
                        if 'enabled' in key:
                            self.validation_results['content_check'][key] = False
                            self.logger.error(f"flash_config中的enabled必须为布尔值")
                        elif 'retry' in key or 'timeout' in key:
                            self.validation_results['content_check'][key] = False
                            self.logger.error(f"flash_config中的{key}必须为数字")
                    else:
                        self.validation_results['content_check'][key] = False
                    validation_passed = False
                else:
                    self.validation_results['content_check'][key] = True
            

            return True
            
        except Exception as e:
            self.logger.error(f"配置验证失败: {str(e)}")
            return False
    
    def get_validation_results(self) -> Dict[str, Any]:
        """获取验证结果"""
        return self.validation_results