"""
CANoe接口模块
CANoe Interface Module

封装Python与CANoe的交互接口，集成现有的CANoe控制代码。
该模块提供了CANoe应用程序的自动化控制功能，包括：
- CANoe应用程序的启动和停止
- 测试模块的加载和执行
- 测试结果的统计和报告
- 日志记录和报告生成
"""

import logging
import os
import time
import sys
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.utils.logging_system import get_logger

import pandas as pd

# 尝试导入win32com模块，如果失败则设置为None
try:
    from win32com.client import Dispatch, DispatchEx, WithEvents, DispatchWithEvents, CastTo
    from win32com.client.connect import *
    import pythoncom
    WIN32COM_AVAILABLE = True
except ImportError:
    # 在非Windows环境下，win32com不可用
    Dispatch = DispatchEx = WithEvents = DispatchWithEvents = CastTo = None
    pythoncom = None
    WIN32COM_AVAILABLE = False


class TestResult(Enum):
    """测试结果枚举"""
    SKIP = '0'
    PASS = '1'
    FAIL = '2'


@dataclass
class TestCaseResult:
    """测试用例结果数据类"""
    test_module: str
    test_group: str
    test_case: str
    result: TestResult


class CANoeError(Exception):
    """CANoe相关异常基类"""
    pass


class CANoeConnectionError(CANoeError):
    """CANoe连接异常"""
    pass


class CANoeConfigurationError(CANoeError):
    """CANoe配置异常"""
    pass


def do_events() -> None:
    """处理Windows消息队列"""
    pythoncom.PumpWaitingMessages()
    time.sleep(0.1)


def do_events_until(condition: Callable[[], bool], timeout: float = 30.0) -> bool:
    """等待条件满足或超时
    
    Args:
        condition: 条件函数
        timeout: 超时时间（秒）
        
    Returns:
        bool: 条件是否在超时前满足
    """
    start_time = time.time()
    while not condition():
        if time.time() - start_time > timeout:
            get_logger(__name__).warning(f"等待条件超时: {timeout}秒")
            return False
        do_events()
    return True


class CANoeTestModule:
    """CANoe测试模块包装类"""
    
    def __init__(self, tm):
        self.tm = tm
        self.events = DispatchWithEvents(tm, CANoeTestEvents)
        self.events.name = tm.Name
        self.name = tm.Name
        self.full_name = tm.FullName
        self.path = tm.Path
        self.enabled = tm.Enabled
        self.sequence = tm.Sequence
    
    def is_done(self) -> bool:
        """检查测试是否完成"""
        return self.events.stopped
    
    def start(self) -> bool:
        """启动测试模块"""
        logger = get_logger(__name__)
        if not self.enabled:
            logger.warning(f"测试模块未启用: {self.name}")
            return False
            
        try:
            self.tm.Start()
            self.events.wait_for_start()
            return True
        except Exception as e:
            logger.error(f"启动测试模块失败: {e}")
            return False
    
    def wait_report_generate(self) -> None:
        """等待报告生成"""
        if self.enabled:
            self.events.wait_for_report_generated()


class CANoeTestEvents:
    """CANoe测试事件处理类"""
    
    def __init__(self):
        self.started = False
        self.stopped = False
        self.report_generated = False
        self.name = ""
    
    def wait_for_start(self, timeout: float = 30.0) -> bool:
        """等待测试开始"""
        return do_events_until(lambda: self.started, timeout)
    
    def wait_for_stop(self, timeout: float = 30.0) -> bool:
        """等待测试停止"""
        return do_events_until(lambda: self.stopped, timeout)
    
    def wait_for_report_generated(self, timeout: float = 30.0) -> bool:
        """等待报告生成"""
        return do_events_until(lambda: self.report_generated, timeout)
    
    def OnStart(self):
        """测试开始事件"""
        self.started = True
        self.stopped = False
        self.report_generated = False
        get_logger(__name__).info(f"测试模块已开始: {self.name}")
    
    def OnStop(self, reason):
        """测试停止事件"""
        self.started = False
        self.stopped = True
        get_logger(__name__).info(f"测试模块已停止: {self.name}")
    
    def OnReportGenerated(self, success, source_full_name, generated_full_name):
        """报告生成事件"""
        self.report_generated = True
        get_logger(__name__).info(f"测试报告已生成: {source_full_name}")


class CanoeMeasurementEvents:
    """CANoe测量事件处理类"""
    
    def OnStart(self):
        """测量开始事件"""
        CANoeInterface._started = True
        CANoeInterface._stopped = False
        get_logger(__name__).info("CANoe测量已开始")
    
    def OnStop(self):
        """测量停止事件"""
        CANoeInterface._started = False
        CANoeInterface._stopped = True
        get_logger(__name__).info("CANoe测量已停止")


class CANoeInterface:
    """
    CANoe接口类
    
    封装Python与CANoe的交互，提供CANoe应用程序控制、
    配置加载、测量控制等功能。
    """
    
    # 类变量
    _started = False
    _stopped = False
    
    def __init__(self, canoe_config: Dict[str, Any]):
        """
        初始化CANoe接口
        
        Args:
            canoe_config: CANoe配置参数，包含project_path和tse_path等
        """
        self.canoe_config = canoe_config
        self.logger = get_logger(__name__)
        self.is_connected = False
        self.canoe_app = None
        
        # 检查win32com是否可用
        if not WIN32COM_AVAILABLE:
            raise ImportError("win32com模块不可用，无法在非Windows环境下运行CANoe接口")
        
        # 从配置中获取参数
        # 从main_config的canoe配置中获取CANoe配置文件路径
        self.project_path = canoe_config['canoe'].get('base_path', '')
        # 从main_config的canoe配置中获取测试环境文件路径（支持单个或多个）
        tse_config = canoe_config['canoe'].get('tse_paths', canoe_config['canoe'].get('tse_path', ''))
        if isinstance(tse_config, list):
            self.tse_paths = tse_config
        else:
            self.tse_paths = [tse_config] if tse_config else []
        self.config_path = canoe_config['canoe'].get('configuration_path', '')
        self.test_results: List[TestCaseResult] = []
        self.test_modules: List[CANoeTestModule] = []
        self.all_test_results: List[List[TestCaseResult]] = []  # 存储所有tse的测试结果
        
        # CANoe对象
        self.app = None
        self.measurement = None
        self.configuration = None
        self.test_setup = None
        self.logging = None
        self.temp_log_name = ""
        
        # 自动初始化CANoe接口
        self.initialize()
    
    def initialize(self) -> bool:
        """
        初始化CANoe接口
        
        执行完整的CANoe接口初始化流程，包括：
        - 验证配置参数
        - 检查CANoe环境可用性
        - 初始化CANoe应用程序连接
        - 加载配置文件
        
        Returns:
            bool: 初始化是否成功
        """
        self.logger.info("开始初始化CANoe接口")
        
        try:
            # 1. 验证配置参数
            if not self._validate_configuration():
                self.logger.error("CANoe配置验证失败")
                return False
            
            # 2. 检查CANoe环境
            if not self._check_canoe_environment():
                self.logger.error("CANoe环境检查失败")
                return False
            
            # 3. 初始化CANoe应用程序
            if not self._initialize_canoe_connection():
                self.logger.error("CANoe应用程序初始化失败")
                return False
            
            # 4. 加载配置文件
            if self.config_path and not self._load_configuration():
                self.logger.warning("CANoe配置文件加载失败，将使用默认配置")
            
            # 5. 自动加载测试设置（如果只有一个tse文件）
            if len(self.tse_paths) == 1:
                if self.load_test_setup(self.tse_paths[0]):
                    self.logger.info("测试设置自动加载成功")
                else:
                    self.logger.warning("测试设置自动加载失败")
            elif len(self.tse_paths) > 1:
                self.logger.info(f"检测到{len(self.tse_paths)}个tse文件，将在运行时按顺序加载")
            
            self.is_connected = True
            self.logger.info("CANoe接口初始化成功")
            return True
            
        except Exception as e:
            self.logger.error(f"CANoe接口初始化失败: {str(e)}")
            self.is_connected = False
            return False
    

    
    def _validate_configuration(self) -> bool:
        """
        验证CANoe配置参数
        
        Returns:
            bool: 配置是否有效
        """
        if not self.canoe_config:
            self.logger.error("CANoe配置为空")
            return False
        
        if 'canoe' not in self.canoe_config:
            self.logger.error("配置中缺少CANoe配置节")
            return False
        
        canoe_config = self.canoe_config['canoe']
        
        # 检查必要的配置项
        required_configs = ['base_path']
        for config_key in required_configs:
            if not canoe_config.get(config_key):
                self.logger.error(f"缺少必要的配置项: {config_key}")
                return False
        
        # 验证路径存在性
        if self.project_path and not os.path.exists(self.project_path):
            self.logger.error(f"CANoe项目路径不存在: {self.project_path}")
            return False
        
        if self.config_path and not os.path.exists(self.config_path):
            self.logger.warning(f"CANoe配置文件不存在: {self.config_path}")
        
        # 验证所有tse路径
        for tse_path in self.tse_paths:
            if tse_path and not os.path.exists(tse_path):
                self.logger.warning(f"测试环境文件不存在: {tse_path}")
        
        return True
    
    def _check_canoe_environment(self) -> bool:
        """
        检查CANoe环境可用性
        
        Returns:
            bool: CANoe环境是否可用
        """
        try:
            # 尝试创建CANoe应用程序对象来检查环境
            test_app = Dispatch('CANoe.Application')
            if test_app:
                version = test_app.Version
                self.logger.info(f"检测到CANoe版本: {version.major}.{version.minor}.{version.Build}")
                return True
            else:
                self.logger.error("无法创建CANoe应用程序对象")
                return False
        except Exception as e:
            self.logger.error(f"CANoe环境检查失败: {str(e)}")
            return False
    
    def _initialize_canoe_connection(self) -> bool:
        """
        初始化CANoe应用程序连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            self._initialize_canoe()
            return True
        except Exception as e:
            self.logger.error(f"CANoe连接初始化失败: {str(e)}")
            return False
    
    def _load_configuration(self) -> bool:
        """
        加载CANoe配置文件
        
        Returns:
            bool: 配置加载是否成功
        """
        try:
            if not self.app or not self.config_path:
                return False
            
            self.logger.info(f"加载CANoe配置文件: {self.config_path}")
            self.app.Open(self.config_path)
            self.configuration = self.app.Configuration
            
            if self.configuration:
                self.logger.info("CANoe配置文件加载成功")
                return True
            else:
                self.logger.error("CANoe配置对象获取失败")
                return False
                
        except Exception as e:
            self.logger.error(f"加载CANoe配置文件失败: {str(e)}")
            return False

    def start_canoe_application(self) -> bool:
        """
        启动CANoe应用程序
        
        Returns:
            bool: 启动是否成功
        """
        self.logger.info("启动CANoe应用程序")
        
        try:
            self._initialize_canoe()
            self.is_connected = True
            return True
            
        except Exception as e:
            self.logger.error(f"启动CANoe应用程序失败: {str(e)}")
            return False
    
    def _initialize_canoe(self) -> None:
        """初始化CANoe应用程序"""
        self.app = DispatchEx('CANoe.Application')
        self.app.Configuration.Modified = False
        
        version = self.app.Version
        self.logger.info(f"已加载CANoe版本: {version.major}.{version.minor}.{version.Build}")
        
        self.measurement = self.app.Measurement
        self.running = lambda: self.measurement.Running
        
        # 设置事件处理
        WithEvents(self.app.Measurement, CanoeMeasurementEvents)
    
    def stop_canoe_application(self) -> bool:
        """
        停止CANoe应用程序
        
        Returns:
            bool: 停止是否成功
        """
        self.logger.info("停止CANoe应用程序")
        
        try:
            if self.is_connected and self.measurement:
                self.stop_measurement()
            self.is_connected = False
            return True
            
        except Exception as e:
            self.logger.error(f"停止CANoe应用程序失败: {str(e)}")
            return False
    
    def start_measurement(self, timeout: float = 30.0) -> bool:
        """启动测量
        
        Args:
            timeout: 启动超时时间
            
        Returns:
            bool: 启动是否成功
        """
        if not self.measurement:
            self.logger.error("CANoe未初始化")
            return False
            
        if self.running():
            self.logger.warning("测量已在运行中")
            return True
            
        try:
            self.measurement.Start()
            success = do_events_until(lambda: CANoeInterface._started, timeout)
            if success:
                self.logger.info("CANoe测量已启动")
            else:
                self.logger.error("CANoe测量启动超时")
            return success
        except Exception as e:
            self.logger.error(f"启动CANoe测量失败: {e}")
            return False
    
    def stop_measurement(self, timeout: float = 30.0) -> bool:
        """停止测量
        
        Args:
            timeout: 停止超时时间
            
        Returns:
            bool: 停止是否成功
        """
        if not self.measurement:
            self.logger.error("CANoe未初始化")
            return False
            
        if not self.running():
            self.logger.warning("测量未在运行")
            return True
            
        try:
            self.measurement.Stop()
            success = do_events_until(lambda: CANoeInterface._stopped, timeout)
            if success:
                self.logger.info("CANoe测量已停止")
            else:
                self.logger.error("CANoe测量停止超时")
            return success
        except Exception as e:
            self.logger.error(f"停止CANoe测量失败: {e}")
            return False
    
    def load_configuration(self, config_path: str) -> bool:
        """加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            bool: 加载是否成功
        """
        if not self.app:
            self.logger.error("CANoe应用程序未启动")
            return False
            
        try:
            config_path = Path(config_path)
            if not config_path.exists():
                raise CANoeConfigurationError(f"配置文件不存在: {config_path}")
                
            self.logger.info(f"正在加载配置: {config_path}")
            self.config_path = str(config_path.parent)
            self.configuration = self.app.Configuration
            self.app.Open(str(config_path))
            self.logger.info("配置文件加载成功")
            return True
            
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            return False
    
    def load_test_setup(self, tse_path: str = None) -> bool:
        """
        加载测试设置
        
        Args:
            tse_path: 测试环境文件路径，如果为None则使用第一个配置的路径
        
        Returns:
            bool: 加载是否成功
        """
        
        if not self.app or not self.configuration:
            self.logger.error("CANoe配置未加载")
            return False
            
        if tse_path is None:
            if not self.tse_paths:
                self.logger.error("未配置测试环境文件路径")
                return False
            tse_path = self.tse_paths[0]
            
        try:
            self.test_setup = self.app.Configuration.TestSetup
            full_tse_path = os.path.join(self.config_path, tse_path) if self.config_path else tse_path
            
            # 检查测试环境是否已存在
            test_env = self._find_or_add_test_environment(full_tse_path)
            if test_env is None:
                return False
                
            test_env = CastTo(test_env, "ITestEnvironment2")
            
            # 加载测试模块
            self.test_modules = []
            self._traverse_test_items(test_env, lambda tm: self.test_modules.append(CANoeTestModule(tm)))
            
            self.logger.info(f"已加载 {len(self.test_modules)} 个测试模块 (来自 {tse_path})")
            return True
            
        except Exception as e:
            self.logger.error(f"加载测试设置失败: {e}")
            return False
    
    def _find_or_add_test_environment(self, tse_path: str):
        """查找或添加测试环境"""
        test_environments = self.test_setup.TestEnvironments
        
        # 查找已存在的测试环境
        for i in range(1, test_environments.Count + 1):
            if test_environments.Item(i).FullName == tse_path:
                self.logger.info(f"找到已存在的测试环境: {tse_path}")
                return test_environments.Item(i)
        
        # 添加新的测试环境
        try:
            self.logger.info(f"添加新的测试环境: {tse_path}")
            return test_environments.Add(tse_path)
        except Exception as e:
            self.logger.error(f"添加测试环境失败: {e}")
            return None
    
    def _traverse_test_items(self, parent, test_func: Callable) -> None:
        """遍历测试项目"""
        for test in parent.TestModules:
            test_func(test)
        for folder in parent.Folders:
            self._traverse_test_items(folder, test_func)
    
    def run_test_modules(self) -> pd.DataFrame:
        """运行所有测试模块
        
        Returns:
            pd.DataFrame: 测试结果数据框
        """
        self.logger.info("开始运行测试模块")
        self.test_results.clear()
        
        for test_module in self.test_modules:
            if not test_module.enabled:
                continue
                
            self.logger.info(f"运行测试模块: {test_module.name}")
            test_module.start()
            
            # 等待测试完成
            while not test_module.is_done():
                do_events()
            
            # 收集测试结果
            self._collect_test_results(test_module)
        
        return self._generate_results_dataframe()
    
    def _collect_test_results(self, test_module: CANoeTestModule) -> None:
        """收集测试结果"""
        for i in range(1, test_module.tm.Sequence.Count + 1):
            self._process_test_item(test_module, test_module.tm.Sequence.Item(i))
    
    def _process_test_item(self, test_module: CANoeTestModule, test_item) -> None:
        """处理测试项目（递归处理测试组和测试用例）"""
        test_group = CastTo(test_item, "ITestGroup")
        
        try:
            # 尝试获取测试组的序列数量
            count = test_group.Sequence.Count
            # 如果成功，说明这是一个测试组，递归处理
            for j in range(1, count + 1):
                self._process_test_item(test_module, test_group.Sequence.Item(j))
        except Exception:
            # 如果失败，说明这是一个测试用例
            test_case = CastTo(test_item, "ITestCase")
            result = TestCaseResult(
                test_module=test_module.name,
                test_group=test_group.Name,
                test_case=test_case.Name,
                result=TestResult(str(test_case.Verdict))
            )
            self.test_results.append(result)
    
    def _generate_results_dataframe(self) -> pd.DataFrame:
        """生成测试结果数据框"""
        if not self.test_results:
            return pd.DataFrame()
            
        data = [
            [r.test_module, r.test_group, r.test_case, r.result.name]
            for r in self.test_results
        ]
        
        df = pd.DataFrame(data, columns=['TestModule', 'TestGroup', 'TestCase', 'TestResult'])
        self.logger.info(f"生成测试结果报告，共 {len(df)} 条记录")
        return df
    
    def set_test_modules_path(self, log_path: str) -> None:
        """设置测试模块报告路径"""
        log_path = Path(log_path)
        log_path.mkdir(parents=True, exist_ok=True)
        
        for test_module in self.test_modules:
            report_name = f"{test_module.tm.Report.Name}.xml"
            full_path = log_path / report_name
            test_module.tm.Report.FullName = str(full_path)
            self.logger.info(f"设置报告路径: {full_path}")
    
    def set_logging(self, log_name: str = "temp.blf") -> None:
        """设置日志记录
        
        Args:
            log_name: 日志文件名
        """
        if not self.app or not self.configuration:
            self.logger.error("CANoe配置未加载")
            return
            
        logging_collection = self.app.Configuration.OnlineSetup.LoggingCollection
        
        for i in range(1, logging_collection.Count + 1):
            logging_item = logging_collection(i)
            current_path = Path(logging_item.FullName)
            new_log_path = current_path.parent / log_name
            
            # 删除已存在的日志文件
            if new_log_path.exists():
                try:
                    new_log_path.unlink()
                except Exception as e:
                    self.logger.warning(f"删除旧日志文件失败: {e}")
            
            try:
                logging_item.FullName = str(new_log_path)
                self.logging = logging_item
                self.temp_log_name = str(new_log_path)
                self.logger.info(f"设置日志文件: {new_log_path}")
            except Exception as e:
                self.logger.error(f"设置日志文件失败: {e}")
    
    def select_test_cases(self, case_names: List[str]) -> None:
        """选择要运行的测试用例
        
        Args:
            case_names: 测试用例名称列表
        """
        if not case_names:
            self.logger.warning("未指定测试用例")
            return
            
        if not self.app or not self.test_setup:
            self.logger.error("CANoe测试设置未加载")
            return
            
        test_env = self.app.Configuration.TestSetup.TestEnvironments.Item(1)
        test_modules = [CastTo(item, 'ITSTestModule2') for item in test_env.Items]
        test_env.Enabled = True
        
        for tm in test_modules:
            module_enabled = False
            module = CANoeTestModule(tm)
            
            for index in range(1, module.sequence.Count + 1):
                test_item = module.sequence.Item(index)
                test_item.Enabled = 0  # 默认禁用
                
                # 检查是否匹配指定的测试用例
                for case_name in case_names:
                    if case_name == test_item.Name:
                        test_item.Enabled = 1
                        module_enabled = True
                        self.logger.info(f"启用测试用例: {test_item.Name}")
                        break
            
            tm.Enabled = 1 if module_enabled else 0
            
            # 同步更新CANoeTestModule对象的enabled属性
            for test_module in self.test_modules:
                if test_module.tm == tm:
                    test_module.enabled = tm.Enabled
                    break
        
        self.logger.info(f"已选择 {len(case_names)} 个测试用例")
    
    def get_test_summary(self) -> Dict[str, Any]:
        """
        获取测试摘要
        
        Returns:
            Dict: 包含测试统计信息的字典
        """
        if not self.test_results:
            return {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0,
                'pass_rate': 0.0
            }
            
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r.result == TestResult.PASS)
        failed = sum(1 for r in self.test_results if r.result == TestResult.FAIL)
        skipped = sum(1 for r in self.test_results if r.result == TestResult.SKIP)
        
        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'pass_rate': (passed / total * 100) if total > 0 else 0
        }
    

    def run_multiple_tse_files(self, task_config_path: str = None, measurement_started: bool = False) -> Dict[str, Any]:
        """
        按顺序运行多个tse文件并汇总结果
        
        Args:
            task_config_path: 任务配置文件路径，用于根据TSE名称匹配测试用例
            measurement_started: 测量是否已经启动，如果为False则在每个TSE执行前启动测量
        
        Returns:
            Dict: 包含所有测试结果的汇总信息
        """
        if not self.tse_paths:
            self.logger.error("未配置测试环境文件路径")
            return {}
            
        self.logger.info(f"开始按顺序运行 {len(self.tse_paths)} 个tse文件")
        self.all_test_results.clear()
        
        overall_summary = {
            'total_tse_files': len(self.tse_paths),
            'completed_tse_files': 0,
            'failed_tse_files': 0,
            'tse_results': [],
            'overall_stats': {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0,
                'pass_rate': 0.0
            }
        }
        
        for i, tse_path in enumerate(self.tse_paths, 1):
            self.logger.info(f"运行第 {i}/{len(self.tse_paths)} 个tse文件: {tse_path}")
            
            try:
                # 清理之前的测试结果和模块
                self.test_results.clear()
                self.test_modules.clear()
                
                # 如果测量已启动，先停止测量以便重新配置
                if measurement_started and self.running():
                    self.logger.info("停止当前测量以重新配置TSE")
                    self.stop_measurement()
                
                # 加载当前tse文件
                if not self.load_test_setup(tse_path):
                    self.logger.error(f"加载tse文件失败: {tse_path}")
                    overall_summary['failed_tse_files'] += 1
                    continue
                
                # 根据TSE名称选择对应的测试用例（在启动测量之前）
                if task_config_path:
                    from test_framework.utils.common_utils import load_task_config, get_enabled_test_cases
                    import os
                    
                    try:
                        # 获取TSE文件名（不含路径和扩展名）
                        tse_name = os.path.splitext(os.path.basename(tse_path))[0]
                        
                        # 加载任务配置
                        task_config = load_task_config(task_config_path)
                        
                        # 根据TSE名称获取对应的测试用例
                        enabled_case_names = get_enabled_test_cases(task_config, tse_name)
                        
                        if enabled_case_names:
                            self.logger.info(f"为TSE文件 {tse_name} 选择了 {len(enabled_case_names)} 个测试用例")
                            self.select_test_cases(enabled_case_names)
                        else:
                            self.logger.warning(f"TSE文件 {tse_name} 没有找到匹配的测试用例")
                    except Exception as e:
                        self.logger.error(f"选择测试用例时发生错误: {e}，将运行所有启用的测试模块")
                
                # 启动测量（在选择测试用例之后）
                if not measurement_started or not self.running():
                    self.logger.info(f"为TSE文件 {tse_path} 启动测量")
                    if not self.start_measurement():
                        self.logger.error(f"启动测量失败，跳过TSE文件: {tse_path}")
                        overall_summary['failed_tse_files'] += 1
                        continue
                
                # 运行测试
                test_df = self.run_test_modules()
                
                # 停止测量（为下一个TSE做准备）
                if not measurement_started:
                    self.logger.info(f"TSE文件 {tse_path} 测试完成，停止测量")
                    self.stop_measurement()
                
                # 获取当前tse的测试摘要
                tse_summary = self.get_test_summary()
                tse_summary['tse_path'] = tse_path
                tse_summary['tse_index'] = i
                
                # 保存当前tse的测试结果
                current_results = self.test_results.copy()
                self.all_test_results.append(current_results)
                
                # 更新总体统计
                overall_summary['overall_stats']['total'] += tse_summary['total']
                overall_summary['overall_stats']['passed'] += tse_summary['passed']
                overall_summary['overall_stats']['failed'] += tse_summary['failed']
                overall_summary['overall_stats']['skipped'] += tse_summary['skipped']
                
                overall_summary['tse_results'].append(tse_summary)
                overall_summary['completed_tse_files'] += 1
                
                self.logger.info(f"tse文件 {tse_path} 运行完成: {tse_summary}")
                
            except Exception as e:
                self.logger.error(f"运行tse文件失败 {tse_path}: {e}")
                overall_summary['failed_tse_files'] += 1
        
        # 计算总体通过率
        total_tests = overall_summary['overall_stats']['total']
        if total_tests > 0:
            overall_summary['overall_stats']['pass_rate'] = (
                overall_summary['overall_stats']['passed'] / total_tests * 100
            )
        
        self.logger.info(f"所有tse文件运行完成，总体结果: {overall_summary['overall_stats']}")
        return overall_summary
    
    def get_combined_test_results_dataframe(self) -> pd.DataFrame:
        """
        获取所有tse文件的合并测试结果数据框
        
        Returns:
            pd.DataFrame: 合并的测试结果数据框
        """
        if not self.all_test_results:
            return pd.DataFrame()
        
        all_data = []
        for tse_index, results in enumerate(self.all_test_results, 1):
            tse_path = self.tse_paths[tse_index - 1] if tse_index <= len(self.tse_paths) else f"TSE_{tse_index}"
            
            for result in results:
                all_data.append([
                    tse_path,
                    result.test_module,
                    result.test_group,
                    result.test_case,
                    result.result.name
                ])
        
        df = pd.DataFrame(all_data, columns=['TSE_File', 'TestModule', 'TestGroup', 'TestCase', 'TestResult'])
        self.logger.info(f"生成合并测试结果报告，共 {len(df)} 条记录")
        return df
    
    def send_summary_email(self, summary: Dict[str, Any], notification_service=None, html_report_path: str = None) -> bool:
        """
        发送测试结果汇总邮件
        
        Args:
            summary: 测试结果汇总信息
            notification_service: 通知服务实例
            html_report_path: HTML报告文件路径（可选）
            
        Returns:
            bool: 发送是否成功
        """
        if not notification_service:
            self.logger.warning("未提供通知服务，跳过邮件发送")
            return False
        
        try:
            # 构建邮件内容
            subject = f"CANoe多TSE测试结果汇总 - {summary['completed_tse_files']}/{summary['total_tse_files']}个文件完成"
            
            body = f"""
            CANoe多TSE文件测试执行完成
            
            执行概况:
            - 总TSE文件数: {summary['total_tse_files']}
            - 成功完成: {summary['completed_tse_files']}
            - 执行失败: {summary['failed_tse_files']}
            
            总体测试结果:
            - 总测试用例: {summary['overall_stats']['total']}
            - 通过: {summary['overall_stats']['passed']}
            - 失败: {summary['overall_stats']['failed']}
            - 跳过: {summary['overall_stats']['skipped']}
            - 通过率: {summary['overall_stats']['pass_rate']:.2f}%
            
            各TSE文件详细结果:
            """
            
            for tse_result in summary['tse_results']:
                body += f"""
            
            TSE文件 {tse_result['tse_index']}: {tse_result['tse_path']}
            - 测试用例: {tse_result['total']}
            - 通过: {tse_result['passed']}
            - 失败: {tse_result['failed']}
            - 跳过: {tse_result['skipped']}
            - 通过率: {tse_result['pass_rate']:.2f}%
                """
            
            # 构建结果字典用于邮件发送
            email_results = {
                "总TSE文件数": summary['total_tse_files'],
                "成功完成": summary['completed_tse_files'],
                "执行失败": summary['failed_tse_files'],
                "总测试用例": summary['overall_stats']['total'],
                "通过": summary['overall_stats']['passed'],
                "失败": summary['overall_stats']['failed'],
                "跳过": summary['overall_stats']['skipped'],
                "通过率": f"{summary['overall_stats']['pass_rate']:.2f}%"
            }
            
            # 添加各TSE文件的详细结果
            for i, tse_result in enumerate(summary['tse_results'], 1):
                tse_name = f"TSE文件{i}"
                email_results[f"{tse_name}_路径"] = tse_result['tse_path']
                email_results[f"{tse_name}_测试用例"] = tse_result['total']
                email_results[f"{tse_name}_通过"] = tse_result['passed']
                email_results[f"{tse_name}_失败"] = tse_result['failed']
                email_results[f"{tse_name}_跳过"] = tse_result['skipped']
                email_results[f"{tse_name}_通过率"] = f"{tse_result['pass_rate']:.2f}%"
            
            # 识别失败的关键字
            failed_keywords = set()
            if summary['overall_stats']['failed'] > 0:
                failed_keywords.add('失败')
            if summary['failed_tse_files'] > 0:
                failed_keywords.add('执行失败')
            
            # 发送邮件（包含HTML附件）
            return notification_service.send_email(
                subject=subject,
                results=email_results,
                failed_keywords=failed_keywords,
                attachment_path=html_report_path
            )
            
        except Exception as e:
            self.logger.error(f"发送汇总邮件失败: {e}")
            return False
    
    def cleanup(self) -> None:
        """清理资源"""
        if self.is_connected:
            self.stop_canoe_application()