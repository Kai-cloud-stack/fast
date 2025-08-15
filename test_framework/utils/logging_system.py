#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志系统工具模块
提供统一的日志记录功能
"""

import logging
import os
from datetime import datetime
from typing import Optional

# 全局变量存储项目日志文件路径
_project_log_file = None
_project_log_level = 'INFO'


def get_logger(name: str, log_level: str = 'INFO', log_file: Optional[str] = None) -> logging.Logger:
    """
    获取配置好的日志记录器
    
    Args:
        name: 日志记录器名称，通常使用 __name__
        log_level: 日志级别 ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        log_file: 可选的日志文件路径，如果不提供则尝试使用项目级别的日志文件
    
    Returns:
        配置好的日志记录器实例
    """
    global _project_log_file, _project_log_level
    
    logger = logging.getLogger(name)
    
    # 如果logger已经有处理器，直接返回
    if logger.handlers:
        return logger
    
    # 设置日志级别，优先使用传入的级别，否则使用项目级别
    if log_level == 'INFO' and _project_log_level != 'INFO':
        level = getattr(logging, _project_log_level.upper(), logging.INFO)
    else:
        level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 确定要使用的日志文件
    target_log_file = log_file or _project_log_file
    
    # 如果有日志文件，创建文件处理器
    if target_log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(target_log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(target_log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # 防止日志向上传播到根日志记录器
    logger.propagate = False
    
    return logger


def setup_project_logging(project_name: str = 'CANoe_Test_Framework', 
                         log_dir: str = 'logs',
                         log_level: str = 'INFO') -> logging.Logger:
    """
    为整个项目设置日志系统
    
    Args:
        project_name: 项目名称
        log_dir: 日志目录
        log_level: 日志级别
    
    Returns:
        项目主日志记录器
    """
    global _project_log_file, _project_log_level
    
    # 创建日志目录
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # 生成日志文件名（包含时间戳）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'{project_name}_{timestamp}.log')
    
    # 设置全局日志配置
    _project_log_file = log_file
    _project_log_level = log_level
    
    # 获取项目主日志记录器
    main_logger = get_logger(project_name, log_level, log_file)
    
    main_logger.info(f"日志系统初始化完成 - 日志文件: {log_file}")
    main_logger.info(f"日志级别: {log_level}")
    main_logger.info("所有模块的日志将自动保存到此文件")
    
    return main_logger


def get_module_logger(module_name: str, parent_logger: Optional[logging.Logger] = None) -> logging.Logger:
    """
    为模块获取日志记录器
    
    Args:
        module_name: 模块名称
        parent_logger: 父日志记录器，如果提供则继承其配置
    
    Returns:
        模块日志记录器
    """
    if parent_logger:
        logger_name = f"{parent_logger.name}.{module_name}"
    else:
        logger_name = module_name
    
    logger = logging.getLogger(logger_name)
    
    # 如果没有父日志记录器，使用默认配置
    if not parent_logger and not logger.handlers:
        return get_logger(logger_name)
    
    return logger


def get_project_log_file() -> Optional[str]:
    """
    获取当前项目日志文件路径
    
    Returns:
        项目日志文件路径，如果未设置则返回None
    """
    global _project_log_file
    return _project_log_file


def get_project_log_level() -> str:
    """
    获取当前项目日志级别
    
    Returns:
        项目日志级别
    """
    global _project_log_level
    return _project_log_level


if __name__ == '__main__':
    # 演示日志系统使用
    print("=" * 50)
    print("日志系统演示")
    print("=" * 50)
    
    # 1. 基本使用
    logger = get_logger(__name__)
    logger.info("这是一条信息日志")
    logger.warning("这是一条警告日志")
    logger.error("这是一条错误日志")
    
    # 2. 项目日志设置
    project_logger = setup_project_logging()
    project_logger.info("项目日志系统测试")
    
    # 3. 模块日志
    module_logger = get_module_logger("test_module", project_logger)
    module_logger.info("模块日志测试")
    
    print("\n日志系统演示完成！")