"""
测试运行器模块
Test Runner Module

执行Python和CAPL测试用例，生成测试报告。
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any, List

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.utils.logging_system import get_logger


class TestRunner:
    """
    测试运行器类
    
    负责执行Python和CAPL测试用例，收集测试结果并生成报告。
    """
    
    def __init__(self, canoe_interface):
        """
        初始化测试运行器
        
        Args:
            canoe_interface: CANoe接口实例
        """
        self.canoe_interface = canoe_interface
        self.logger = get_logger(__name__)
        self.test_results: List[Dict[str, Any]] = []
    
    def run_test_suite(self, task_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行测试套件
        
        Args:
            task_config: 任务配置，包含测试用例配置
            
        Returns:
            Dict[str, Any]: 测试结果摘要
        """
        self.logger.info("开始运行测试套件")
        
        try:
            # 检查CANoe接口是否已连接
            if not self.canoe_interface.is_connected:
                self.logger.error("CANoe接口未连接")
                return {"status": "failed", "error": "CANoe接口未连接"}
            
            # 从task_config中获取测试用例配置
            test_cases = task_config.get("test_cases", [])
            if not test_cases:
                self.logger.warning("未找到测试用例配置")
                return {"status": "success", "total": 0, "passed": 0, "failed": 0, "skipped": 0, "pass_rate": 0, "results": []}
            
            # 过滤出启用的测试用例
            enabled_test_cases = [case for case in test_cases if case.get('enabled', False)]
            
            if not enabled_test_cases:
                self.logger.warning("没有启用的测试用例")
                return {"status": "success", "total": 0, "passed": 0, "failed": 0, "skipped": 0, "pass_rate": 0, "results": []}
            
            self.logger.info(f"共找到 {len(test_cases)} 个测试用例，其中 {len(enabled_test_cases)} 个已启用")
            
            # 获取启用的测试用例名称列表
            enabled_case_names = [case.get('name', '') for case in enabled_test_cases if case.get('name')]
            
            if not enabled_case_names:
                self.logger.error("启用的测试用例中没有有效的名称")
                return {"status": "failed", "error": "启用的测试用例中没有有效的名称"}
            
            # 使用select_test_cases方法选择要运行的测试用例
            self.logger.info(f"选择测试用例: {enabled_case_names}")
            self.canoe_interface.select_test_cases(enabled_case_names)
            
            # 启动测量
            if not self.canoe_interface.start_measurement():
                self.logger.error("启动CANoe测量失败")
                return {"status": "failed", "error": "启动CANoe测量失败"}
            
            # 运行测试模块
            self.logger.info("开始运行CANoe测试模块")
            test_results_df = self.canoe_interface.run_test_modules()
            
            # 停止测量
            self.canoe_interface.stop_measurement()
            
            # 获取测试摘要
            test_summary = self.canoe_interface.get_test_summary()
            
            # 保存测试结果
            self.test_results = test_results_df.to_dict('records') if not test_results_df.empty else []
            
            self.logger.info(f"测试套件运行完成，总计: {test_summary.get('total', 0)} 个测试")
            
            return {
                "status": "success",
                "total": test_summary.get('total', 0),
                "passed": test_summary.get('passed', 0),
                "failed": test_summary.get('failed', 0),
                "skipped": test_summary.get('skipped', 0),
                "pass_rate": test_summary.get('pass_rate', 0),
                "results": self.test_results
            }
            
        except Exception as e:
            self.logger.error(f"测试套件运行失败: {str(e)}")
            # 确保停止测量
            try:
                self.canoe_interface.stop_measurement()
            except:
                pass
            return {"status": "failed", "error": str(e)}
    
    def get_test_results(self) -> List[Dict[str, Any]]:
        """获取测试结果"""
        return self.test_results