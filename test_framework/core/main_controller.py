"""
主控制器模块
Main Controller Module

负责协调整个测试流程的执行，包括初始化各个模块、执行配置验证、
环境检查、任务配置读取、刷写操作、测试用例运行、数据归档和通知发送。
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .config_manager import ConfigManager
from .logger_manager import LoggerManager
from ..checkers.environment_checker import EnvironmentChecker
from ..executors.task_executor import TaskExecutor
from ..executors.flash_manager import FlashManager
from ..executors.test_runner import TestRunner
from ..services.data_archiver import DataArchiver
from ..services.notification_service import NotificationService
from ..services.package_manager import PackageManager
from ..interfaces.canoe_interface import CANoeInterface


class MainController:
    """
    主控制器类
    
    协调整个测试框架的执行流程，管理各个模块的生命周期，
    处理流程控制和错误处理。
    """
    
    def __init__(self, config_path: str):
        """
        初始化主控制器
        
        Args:
            config_path: 主配置文件路径
        """
        self.config_path = config_path
        self.config_manager: Optional[ConfigManager] = None
        self.logger_manager: Optional[LoggerManager] = None
        self.logger: Optional[logging.Logger] = None
        
        # 各功能模块
        self.canoe_interface: Optional[CANoeInterface] = None
        self.environment_checker: Optional[EnvironmentChecker] = None
        self.task_executor: Optional[TaskExecutor] = None
        self.flash_manager: Optional[FlashManager] = None
        self.test_runner: Optional[TestRunner] = None
        self.data_archiver: Optional[DataArchiver] = None
        self.notification_service: Optional[NotificationService] = None
        self.package_manager: Optional[PackageManager] = None
        
        # 运行状态
        self.is_running = False
        self.start_time: Optional[datetime] = None
        self.current_phase = "初始化"
        self.test_results: Dict[str, Any] = {}
        
    def initialize(self) -> bool:
        """
        初始化所有模块
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 初始化配置管理器
            self.config_manager = ConfigManager(self.config_path)
            
            # 初始化日志管理器
            self.logger_manager = LoggerManager(self.config_manager)
            self.logger = self.logger_manager.get_logger("MainController")
            
            self.logger.info("开始初始化测试框架")
            
            # 初始化各功能模块
            self._initialize_modules()
            
            self.logger.info("测试框架初始化完成")
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"初始化失败: {str(e)}")
            return False
    
    def _initialize_modules(self) -> None:
        """初始化各功能模块"""
        # 获取配置
        main_config = self.config_manager.load_main_config()
        
        # 初始化服务 (NotificationService needs to be initialized before checkers)
        self.notification_service = NotificationService(
            email_config=main_config.get("email", {}),
            wechat_config=main_config.get("wechat", {})
        )
        self.data_archiver = DataArchiver(main_config.get("archive", {}))
        self.package_manager = PackageManager(main_config.get("package_manager", {}))

        # 初始化CANoe接口
        self.canoe_interface = CANoeInterface(main_config.get("canoe", {}))
        
        # 初始化检查器
        self.environment_checker = EnvironmentChecker(self.canoe_interface, self.notification_service)
        
        # 初始化执行器
        self.task_executor = TaskExecutor(self.config_manager)
        self.flash_manager = FlashManager(main_config.get("flash", {}))
        self.test_runner = TestRunner(self.canoe_interface)
    
    def _execute_phase(self, phase_name: str, func, *args, **kwargs) -> bool:
        """执行一个测试流程阶段"""
        self.current_phase = phase_name
        self.logger.info(f"开始 {phase_name}")
        try:
            if not func(*args, **kwargs):
                self.logger.error(f"{phase_name} 失败")
                self._handle_critical_error(f"{phase_name} 失败")
                return False
            self.logger.info(f"{phase_name} 完成")
            return True
        except Exception as e:
            self.logger.error(f"{phase_name} 期间发生异常: {e}")
            self._handle_critical_error(f"{phase_name} 期间发生异常: {e}")
            return False

    def run(self) -> bool:
        """
        运行完整的测试流程
        
        Returns:
            bool: 测试流程是否成功完成
        """
        if not self.initialize():
            return False
            
        self.is_running = True
        self.start_time = datetime.now()
        
        try:
            self.logger.info("开始执行测试流程")
            
            if not self._execute_phase("配置文件验证", self._execute_config_validation):
                return False
            if not self._execute_phase("测试环境检查", self._execute_environment_check):
                return False
            if not self._execute_phase("读取任务配置", self._load_task_configuration):
                return False
            if not self._execute_phase("软件包管理", self._manage_packages):
                return False
            if not self._execute_phase("执行刷写操作", self._execute_flash_operation):
                return False
            if not self._execute_phase("运行测试用例", self._execute_test_cases):
                return False
            if not self._execute_phase("数据归档和通知", self._finalize_execution):
                return False
                
            self.logger.info("测试流程执行完成")
            return True
            
        except Exception as e:
            self.logger.error(f"测试流程执行失败: {str(e)}")
            self._handle_critical_error(str(e))
            return False
        finally:
            self.is_running = False
    
    def _execute_config_validation(self) -> bool:
        """执行配置文件验证"""
        try:
            self.config_manager.load_main_config()
            self.config_manager.load_task_config()
            self.logger.info("配置文件验证成功")
            return True
        except (FileNotFoundError, ValueError) as e:
            self.logger.error(f"配置文件验证失败: {e}")
            # No need to call _handle_critical_error here as it's handled by _execute_phase
            return False
    
    def _execute_environment_check(self) -> bool:
        """执行测试环境检查"""
        try:
            check_results = self.environment_checker.check_environment()
            
            if check_results.get('result') == 'fail':
                error_msg = f"环境检查失败: {check_results.get('error_message', '未知错误')}"
                self.logger.error(error_msg)
                
                # 发送通知
                self.notification_service.send_email(
                    subject="环境检查失败警告",
                    content=error_msg
                )
                self.notification_service.send_robot_message(
                    message=error_msg,
                    level='error'
                )
                
                return False
            
            self.logger.info("环境检查通过")
            return True
            
        except Exception as e:
            self.logger.error(f"环境检查期间发生异常: {str(e)}")
            return False
    
    def _load_task_configuration(self) -> bool:
        """读取任务配置"""
        try:
            test_cases = self.task_executor.parse_task_config()
            if not test_cases:
                self.logger.error("未找到有效的测试用例")
                return False
            
            self.logger.info(f"成功加载 {len(test_cases)} 个测试用例")
            return True
            
        except Exception as e:
            self.logger.error(f"读取任务配置失败: {str(e)}")
            return False
    
    def _manage_packages(self) -> bool:
        """管理软件包"""
        self.current_phase = "软件包管理"
        self.logger.info("开始软件包管理")
        
        # 实现软件包管理逻辑
        return True
    
    def _execute_flash_operation(self) -> bool:
        """执行刷写操作"""
        self.current_phase = "刷写操作"
        self.logger.info("开始刷写操作")
        
        # 实现刷写操作逻辑
        return True
    
    def _execute_test_cases(self) -> bool:
        """执行测试用例"""
        self.current_phase = "测试执行"
        self.logger.info("开始执行测试用例")
        
        # 实现测试用例执行逻辑
        return True
    
    def _finalize_execution(self) -> bool:
        """完成执行，归档数据和发送通知"""
        self.current_phase = "数据归档和通知"
        self.logger.info("开始数据归档和通知")
        
        # 实现数据归档和通知逻辑
        return True
    
    def _handle_critical_error(self, error_message: str, failed_keywords: set = None) -> None:
        """处理关键错误"""
        self.logger.error(f"发生关键错误: {error_message}")
        
        # 发送错误通知邮件
        if self.notification_service:
            error_info = {
                "错误类型": "系统关键错误",
                "错误信息": error_message,
                "发生阶段": self.current_phase,
                "时间戳": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.notification_service.send_email(
                subject=f"FAST测试框架关键错误: {self.current_phase}",
                results=error_info,
                failed_keywords=failed_keywords if failed_keywords else set()
            )
            self.notification_service.send_robot_message(
                content=f"FAST测试框架发生关键错误！\n阶段: {self.current_phase}\n错误: {error_message}\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
    
    def stop(self) -> None:
        """
        停止测试框架运行
        """
        self.logger.info("正在停止测试框架")
        self.is_running = False
        
        # 清理资源
        if self.canoe_interface:
            self.canoe_interface.cleanup()
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取当前运行状态
        
        Returns:
            Dict[str, Any]: 包含运行状态信息的字典
        """
        return {
            "is_running": self.is_running,
            "current_phase": self.current_phase,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "test_results": self.test_results
        }