#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多TSE文件顺序执行器
Multiple TSE Files Sequential Executor

本模块实现了多个TSE文件的顺序执行功能，包括：
1. 从配置文件加载多个TSE路径
2. 按顺序执行所有TSE文件
3. 汇总所有测试结果
4. 生成详细报告
5. 发送邮件通知
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from ..interfaces.canoe_interface import CANoeInterface
from ..services.notification_service import NotificationService
from ..utils.logging_system import get_logger


class MultiTSEExecutor:
    """多TSE文件执行器"""
    
    def __init__(self, config_file: str = None, config: Dict[str, Any] = None):
        """
        初始化多TSE执行器
        
        Args:
            config_file: 配置文件路径（已弃用，保留向后兼容性）
            config: 已加载的配置字典（推荐使用）
        """
        self.logger = get_logger(__name__)
        
        # 优先使用传入的配置字典，避免重复加载
        if config is not None:
            self.config = config
            self.config_file = None  # 不需要配置文件路径
            self.logger.info("使用传入的配置字典")
        else:
            # 向后兼容：如果没有传入配置字典，则从文件加载
            self.config_file = config_file or 'test_framework/config/main_config.json'
            self.config = self._load_config()
            self.logger.info(f"从文件加载配置: {self.config_file}")
            
        self.canoe_interface = None
        self.notification_service = None
        self.execution_start_time = None
        self.execution_end_time = None
        
    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            Dict: 配置信息
        """
        config_path = Path(self.config_file)
        
        if not config_path.exists():
            self.logger.error(f"配置文件不存在: {config_path}")
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.logger.info(f"成功加载配置文件: {config_path}")
            return config
            
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            raise
    
    def _validate_config(self) -> bool:
        """
        验证配置文件
        
        Returns:
            bool: 配置是否有效
        """
        required_sections = ['canoe', 'notification']
        
        for section in required_sections:
            if section not in self.config:
                self.logger.error(f"配置文件缺少必要节: {section}")
                return False
        
        # 验证CANoe配置
        canoe_config = self.config['canoe']
        if 'tse_paths' not in canoe_config and 'tse_path' not in canoe_config:
            self.logger.error("配置文件缺少tse_paths配置")
            return False
        
        # 支持新旧配置格式
        tse_paths = canoe_config.get('tse_paths', canoe_config.get('tse_path', []))
        if not isinstance(tse_paths, list) or len(tse_paths) == 0:
            self.logger.error("tse_path必须是非空列表")
            return False
        
        self.logger.info(f"配置验证通过，发现 {len(tse_paths)} 个TSE文件")
        return True
    
    def _initialize_services(self) -> bool:
        """
        初始化服务
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 初始化CANoe接口
            self.logger.info("初始化CANoe接口...")
            self.canoe_interface = CANoeInterface(self.config)
            
            if not self.canoe_interface.is_connected:
                self.logger.error("CANoe接口初始化失败")
                return False
            
            # 初始化通知服务
            self.logger.info("初始化通知服务...")
            self.notification_service = NotificationService(self.config.get('notification', {}))
            
            return True
            
        except Exception as e:
            self.logger.error(f"服务初始化失败: {e}")
            return False
    
    def _create_output_directory(self) -> Path:
        """
        创建输出目录
        
        Returns:
            Path: 输出目录路径
        """
        output_config = self.config.get('output', {})
        base_dir = Path(output_config.get('base_directory', 'output'))
        
        if output_config.get('timestamp_folders', True):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = base_dir / f"multi_tse_execution_{timestamp}"
        else:
            output_dir = base_dir / "multi_tse_execution"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"创建输出目录: {output_dir}")
        
        return output_dir
    
    def _save_results(self, summary: Dict[str, Any], output_dir: Path) -> None:
        """
        保存测试结果（仅保留HTML格式）
        
        Args:
            summary: 测试结果汇总
            output_dir: 输出目录
        """
        # 获取合并的测试结果数据框
        combined_df = self.canoe_interface.get_combined_test_results_dataframe()
        
        # 仅生成HTML报告
        self.logger.info("生成HTML测试报告...")
        self._generate_html_report(summary, combined_df, output_dir)
    
    def _generate_html_report(self, summary: Dict[str, Any], df, output_dir: Path) -> None:
        """
        生成HTML报告
        
        Args:
            summary: 测试结果汇总
            df: 测试结果数据框
            output_dir: 输出目录
        """
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>CANoe多TSE测试执行报告</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .summary {{ margin: 20px 0; }}
                .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
                .stat-box {{ background-color: #e8f4fd; padding: 15px; border-radius: 5px; flex: 1; }}
                .tse-results {{ margin: 20px 0; }}
                .tse-item {{ background-color: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .pass {{ color: green; font-weight: bold; }}
                .fail {{ color: red; font-weight: bold; }}
                .skip {{ color: orange; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>CANoe多TSE测试执行报告</h1>
                <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="summary">
                <h2>执行概况</h2>
                <div class="stats">
                    <div class="stat-box">
                        <h3>TSE文件</h3>
                        <p>总数: {summary['total_tse_files']}</p>
                        <p>完成: {summary['completed_tse_files']}</p>
                        <p>失败: {summary['failed_tse_files']}</p>
                    </div>
                    <div class="stat-box">
                        <h3>测试用例</h3>
                        <p>总数: {summary['overall_stats']['total']}</p>
                        <p class="pass">通过: {summary['overall_stats']['passed']}</p>
                        <p class="fail">失败: {summary['overall_stats']['failed']}</p>
                        <p class="skip">跳过: {summary['overall_stats']['skipped']}</p>
                    </div>
                    <div class="stat-box">
                        <h3>通过率</h3>
                        <p style="font-size: 24px; font-weight: bold;">{summary['overall_stats']['pass_rate']:.2f}%</p>
                    </div>
                </div>
            </div>
            
            <div class="tse-results">
                <h2>各TSE文件详细结果</h2>
        """
        
        # 添加每个TSE文件的结果
        for tse_result in summary['tse_results']:
            html_content += f"""
                <div class="tse-item">
                    <h3>TSE文件 {tse_result['tse_index']}: {tse_result['tse_path']}</h3>
                    <p>测试用例: {tse_result['total']} | 
                       <span class="pass">通过: {tse_result['passed']}</span> | 
                       <span class="fail">失败: {tse_result['failed']}</span> | 
                       <span class="skip">跳过: {tse_result['skipped']}</span> | 
                       通过率: {tse_result['pass_rate']:.2f}%</p>
                </div>
            """
        
        # 添加详细测试结果表格
        if not df.empty:
            html_content += """
            </div>
            
            <div class="detailed-results">
                <h2>详细测试结果</h2>
                <table>
                    <thead>
                        <tr>
                            <th>TSE文件</th>
                            <th>测试模块</th>
                            <th>测试组</th>
                            <th>测试用例</th>
                            <th>结果</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for _, row in df.iterrows():
                result_class = 'pass' if row['TestResult'] == 'PASS' else ('fail' if row['TestResult'] == 'FAIL' else 'skip')
                html_content += f"""
                        <tr>
                            <td>{row['TSE_File']}</td>
                            <td>{row['TestModule']}</td>
                            <td>{row['TestGroup']}</td>
                            <td>{row['TestCase']}</td>
                            <td class="{result_class}">{row['TestResult']}</td>
                        </tr>
                """
            
            html_content += """
                    </tbody>
                </table>
            </div>
            """
        
        html_content += """
        </body>
        </html>
        """
        
        # 保存HTML文件
        html_file = output_dir / "test_execution_report.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"HTML报告已生成: {html_file}")
    
    def execute(self) -> bool:
        """
        执行多TSE文件测试
        
        Returns:
            bool: 执行是否成功
        """
        try:
            self.logger.info("开始多TSE文件顺序执行")
            self.execution_start_time = datetime.now()
            
            # 1. 验证配置
            if not self._validate_config():
                return False
            
            # 2. 初始化服务
            if not self._initialize_services():
                return False
            
            # 3. 创建输出目录
            output_dir = self._create_output_directory()
            
            # 4. 执行多TSE文件（内部管理测量生命周期）
            self.logger.info("开始执行多TSE文件...")
            
            # 获取任务配置文件路径（如果配置中有的话）
            task_config_path = self.config.get('task_config_path')
            if task_config_path:
                self.logger.info(f"使用任务配置文件: {task_config_path}")
            
            # 使用measurement_started=False，让run_multiple_tse_files内部管理测量
            summary = self.canoe_interface.run_multiple_tse_files(task_config_path, measurement_started=False)
            
            if not summary:
                self.logger.error("多TSE文件执行失败")
                return False
            
            self.execution_end_time = datetime.now()
            
            # 5. 保存结果
            self.logger.info("保存测试结果...")
            self._save_results(summary, output_dir)
            
            # 6. 发送通知
            self.logger.info("发送测试结果通知...")
            email_sent = self.canoe_interface.send_summary_email(summary, self.notification_service)
            
            if email_sent:
                self.logger.info("通知邮件发送成功")
            else:
                self.logger.warning("通知邮件发送失败")
            
            # 9. 打印执行摘要
            self._print_execution_summary(summary)
            
            self.logger.info("多TSE文件顺序执行完成")
            return True
            
        except Exception as e:
            self.logger.error(f"执行过程中发生错误: {e}")
            return False
        
        finally:
            # 清理资源
            if self.canoe_interface:
                self.canoe_interface.cleanup()
    
    def _print_execution_summary(self, summary: Dict[str, Any]) -> None:
        """
        打印执行摘要
        
        Args:
            summary: 测试结果汇总
        """
        print("\n" + "="*60)
        print("多TSE文件执行摘要")
        print("="*60)
        print(f"执行时间: {self.execution_start_time.strftime('%Y-%m-%d %H:%M:%S')} - {self.execution_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if self.execution_start_time and self.execution_end_time:
            duration = self.execution_end_time - self.execution_start_time
            print(f"总耗时: {duration.total_seconds():.2f} 秒")
        
        print(f"\nTSE文件执行情况:")
        print(f"  总数: {summary['total_tse_files']}")
        print(f"  成功: {summary['completed_tse_files']}")
        print(f"  失败: {summary['failed_tse_files']}")
        
        print(f"\n总体测试结果:")
        stats = summary['overall_stats']
        print(f"  总测试用例: {stats['total']}")
        print(f"  通过: {stats['passed']}")
        print(f"  失败: {stats['failed']}")
        print(f"  跳过: {stats['skipped']}")
        print(f"  通过率: {stats['pass_rate']:.2f}%")
        
        print(f"\n各TSE文件详细结果:")
        for tse_result in summary['tse_results']:
            print(f"  {tse_result['tse_index']}. {tse_result['tse_path']}")
            print(f"     测试用例: {tse_result['total']} | 通过: {tse_result['passed']} | 失败: {tse_result['failed']} | 跳过: {tse_result['skipped']} | 通过率: {tse_result['pass_rate']:.2f}%")
        
        print("="*60)