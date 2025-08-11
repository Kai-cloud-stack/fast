"""
日志管理器模块
Logger Manager Module

负责管理系统日志的配置、创建和管理，提供统一的日志记录接口。
"""

import logging
import logging.handlers
import os
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime


class LoggerManager:
    """
    日志管理器类
    
    负责配置和管理系统日志，支持文件日志、控制台日志，
    提供日志轮转、格式化和多级别日志记录功能。
    """
    
    def __init__(self, config_manager):
        """
        初始化日志管理器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self.loggers: Dict[str, logging.Logger] = {}
        self.log_config = None
        self.initialized = False
        
        # 初始化日志配置
        self._initialize_logging()
    
    def _initialize_logging(self) -> None:
        """初始化日志配置"""
        try:
            # 获取日志配置
            main_config = self.config_manager.get_main_config()
            if main_config:
                self.log_config = main_config.get("logging", {})
            else:
                # 使用默认配置
                self.log_config = self._get_default_log_config()
            
            # 创建日志目录
            self._create_log_directory()
            
            # 配置根日志记录器
            self._configure_root_logger()
            
            self.initialized = True
            
        except Exception as e:
            # 如果日志初始化失败，使用基本配置
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            logging.error(f"日志管理器初始化失败，使用默认配置: {str(e)}")
    
    def _get_default_log_config(self) -> Dict:
        """获取默认日志配置"""
        return {
            "level": "INFO",
            "file_path": "./logs/test_framework.log",
            "max_size": "10MB",
            "backup_count": 5,
            "console_output": True,
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "date_format": "%Y-%m-%d %H:%M:%S"
        }
    
    def _create_log_directory(self) -> None:
        """创建日志目录"""
        log_file_path = Path(self.log_config.get("file_path", "./logs/test_framework.log"))
        log_dir = log_file_path.parent
        
        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)
    
    def _configure_root_logger(self) -> None:
        """配置根日志记录器"""
        # 获取日志级别
        log_level = getattr(logging, self.log_config.get("level", "INFO").upper())
        
        # 创建格式化器
        formatter = logging.Formatter(
            fmt=self.log_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            datefmt=self.log_config.get("date_format", "%Y-%m-%d %H:%M:%S")
        )
        
        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # 清除现有处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 添加文件处理器
        self._add_file_handler(root_logger, formatter)
        
        # 添加控制台处理器（如果启用）
        if self.log_config.get("console_output", True):
            self._add_console_handler(root_logger, formatter)
    
    def _add_file_handler(self, logger: logging.Logger, formatter: logging.Formatter) -> None:
        """添加文件处理器"""
        log_file_path = self.log_config.get("file_path", "./logs/test_framework.log")
        max_size = self._parse_size(self.log_config.get("max_size", "10MB"))
        backup_count = self.log_config.get("backup_count", 5)
        
        # 创建轮转文件处理器
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file_path,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    def _add_console_handler(self, logger: logging.Logger, formatter: logging.Formatter) -> None:
        """添加控制台处理器"""
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    def _parse_size(self, size_str: str) -> int:
        """解析大小字符串为字节数"""
        size_str = size_str.upper()
        
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            # 默认为字节
            return int(size_str)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        获取指定名称的日志记录器
        
        Args:
            name: 日志记录器名称
            
        Returns:
            logging.Logger: 日志记录器实例
        """
        if name not in self.loggers:
            logger = logging.getLogger(name)
            
            # 如果日志管理器未初始化，使用基本配置
            if not self.initialized:
                logger.setLevel(logging.INFO)
            
            self.loggers[name] = logger
        
        return self.loggers[name]
    
    def create_module_logger(self, module_name: str, log_file: Optional[str] = None) -> logging.Logger:
        """
        为特定模块创建专用日志记录器
        
        Args:
            module_name: 模块名称
            log_file: 专用日志文件路径（可选）
            
        Returns:
            logging.Logger: 模块专用日志记录器
        """
        logger = logging.getLogger(f"TestFramework.{module_name}")
        
        if log_file:
            # 创建专用文件处理器
            formatter = logging.Formatter(
                fmt=self.log_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
                datefmt=self.log_config.get("date_format", "%Y-%m-%d %H:%M:%S")
            )
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        self.loggers[module_name] = logger
        return logger
    
    def set_log_level(self, level: str) -> None:
        """
        设置日志级别
        
        Args:
            level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        """
        try:
            log_level = getattr(logging, level.upper())
            
            # 更新根日志记录器级别
            logging.getLogger().setLevel(log_level)
            
            # 更新所有已创建的日志记录器级别
            for logger in self.loggers.values():
                logger.setLevel(log_level)
            
            # 更新配置
            self.log_config["level"] = level.upper()
            
        except AttributeError:
            logging.error(f"无效的日志级别: {level}")
    
    def log_system_info(self) -> None:
        """记录系统信息"""
        logger = self.get_logger("SystemInfo")
        
        logger.info("=" * 50)
        logger.info("测试框架启动")
        logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"日志级别: {self.log_config.get('level', 'INFO')}")
        logger.info(f"日志文件: {self.log_config.get('file_path', 'N/A')}")
        logger.info("=" * 50)
    
    def log_execution_summary(self, start_time: datetime, end_time: datetime, 
                            success: bool, phase: str = "") -> None:
        """
        记录执行摘要
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            success: 是否成功
            phase: 执行阶段
        """
        logger = self.get_logger("ExecutionSummary")
        
        duration = end_time - start_time
        status = "成功" if success else "失败"
        
        logger.info("=" * 50)
        logger.info("执行摘要")
        if phase:
            logger.info(f"执行阶段: {phase}")
        logger.info(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"执行时长: {duration}")
        logger.info(f"执行状态: {status}")
        logger.info("=" * 50)
    
    def cleanup_old_logs(self, days: int = 30) -> None:
        """
        清理旧日志文件
        
        Args:
            days: 保留天数
        """
        try:
            log_file_path = Path(self.log_config.get("file_path", "./logs/test_framework.log"))
            log_dir = log_file_path.parent
            
            if not log_dir.exists():
                return
            
            cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
            
            for log_file in log_dir.glob("*.log*"):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    logging.info(f"删除旧日志文件: {log_file}")
            
        except Exception as e:
            logging.error(f"清理旧日志文件失败: {str(e)}")
    
    def get_log_stats(self) -> Dict:
        """
        获取日志统计信息
        
        Returns:
            Dict: 日志统计信息
        """
        try:
            log_file_path = Path(self.log_config.get("file_path", "./logs/test_framework.log"))
            
            if not log_file_path.exists():
                return {"error": "日志文件不存在"}
            
            stat = log_file_path.stat()
            
            return {
                "log_file": str(log_file_path),
                "file_size": stat.st_size,
                "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "log_level": self.log_config.get("level", "INFO"),
                "active_loggers": len(self.loggers)
            }
            
        except Exception as e:
            return {"error": f"获取日志统计失败: {str(e)}"}
    
    def shutdown(self) -> None:
        """关闭日志管理器"""
        try:
            # 刷新所有处理器
            for logger in self.loggers.values():
                for handler in logger.handlers:
                    handler.flush()
            
            # 关闭根日志记录器的处理器
            root_logger = logging.getLogger()
            for handler in root_logger.handlers:
                handler.close()
            
            logging.info("日志管理器已关闭")
            
        except Exception as e:
            logging.error(f"关闭日志管理器失败: {str(e)}")