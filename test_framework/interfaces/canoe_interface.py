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
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

import pandas as pd
from win32com.client import DispatchEx, WithEvents, DispatchWithEvents, CastTo
from win32com.client.connect import *
import pythoncom


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
            logging.getLogger(__name__).warning(f"等待条件超时: {timeout}秒")
            return False
        do_events()
    return True


class CANoeTestModule:
    """CANoe测试模块包装类"""
    
    def __init__(self, tm):
        self.tm = tm
        self.events = DispatchWithEvents(tm, CANoeTestEvents)
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
        logger = logging.getLogger(__name__)
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
        self.name = "Unknown"
    
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
        logging.getLogger(__name__).info(f"测试模块已开始: {self.name}")
    
    def OnStop(self, reason):
        """测试停止事件"""
        self.started = False
        self.stopped = True
        logging.getLogger(__name__).info(f"测试模块已停止: {self.name}")
    
    def OnReportGenerated(self, success, source_full_name, generated_full_name):
        """报告生成事件"""
        self.report_generated = True
        logging.getLogger(__name__).info(f"测试报告已生成: {source_full_name}")


class CanoeMeasurementEvents:
    """CANoe测量事件处理类"""
    
    def OnStart(self):
        """测量开始事件"""
        CANoeInterface._started = True
        CANoeInterface._stopped = False
        logging.getLogger(__name__).info("CANoe测量已开始")
    
    def OnStop(self):
        """测量停止事件"""
        CANoeInterface._started = False
        CANoeInterface._stopped = True
        logging.getLogger(__name__).info("CANoe测量已停止")


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
        self.logger = logging.getLogger(__name__)
        self.is_connected = False
        self.canoe_app = None
        
        # 从配置中获取参数
        # 从main_config的canoe配置中获取CANoe配置文件路径
        self.project_path = canoe_config['canoe'].get('base_path', '')
        # 从main_config的canoe配置中获取测试环境文件路径
        self.tse_path = canoe_config['canoe'].get('tse_path', '')
        self.config_path = canoe_config['canoe'].get('configuration_path', '')
        self.test_results: List[TestCaseResult] = []
        self.test_modules: List[CANoeTestModule] = []
        
        # CANoe对象
        self.app = None
        self.measurement = None
        self.configuration = None
        self.test_setup = None
        self.logging = None
        self.temp_log_name = ""
    
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
    
    def load_test_setup(self) -> bool:
        """加载测试设置
        
        Returns:
            bool: 加载是否成功
        """
        if not self.app or not self.configuration:
            self.logger.error("CANoe配置未加载")
            return False
            
        try:
            self.test_setup = self.app.Configuration.TestSetup
            tse_path = os.path.join(self.config_path, self.tse_path)
            
            # 检查测试环境是否已存在
            test_env = self._find_or_add_test_environment(tse_path)
            if test_env is None:
                return False
                
            test_env = CastTo(test_env, "ITestEnvironment2")
            
            # 加载测试模块
            self.test_modules = []
            self._traverse_test_items(test_env, lambda tm: self.test_modules.append(CANoeTestModule(tm)))
            
            self.logger.info(f"已加载 {len(self.test_modules)} 个测试模块")
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
        
        for tm in test_modules:
            module_enabled = False
            module = CANoeTestModule(tm)
            
            for index in range(1, module.sequence.Count + 1):
                test_item = module.sequence.Item(index)
                test_item.Enabled = 0  # 默认禁用
                
                # 检查是否匹配指定的测试用例
                for case_name in case_names:
                    if case_name in test_item.Name:
                        test_item.Enabled = 1
                        module_enabled = True
                        self.logger.info(f"启用测试用例: {test_item.Name}")
                        break
            
            tm.Enabled = 1 if module_enabled else 0
        
        self.logger.info(f"已选择 {len(case_names)} 个测试用例")
    
    def get_test_summary(self) -> Dict[str, Any]:
        """获取测试摘要
        
        Returns:
            Dict: 包含测试统计信息的字典
        """
        if not self.test_results:
            return {}
            
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
    

    def cleanup(self) -> None:
        """清理资源"""
        if self.is_connected:
            self.stop_canoe_application()