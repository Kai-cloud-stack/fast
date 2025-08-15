#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多TSE文件顺序执行示例
Multiple TSE Files Sequential Execution Example

本示例展示如何使用修改后的CANoeInterface类来：
1. 配置多个TSE文件路径
2. 按顺序执行所有TSE文件
3. 汇总所有测试结果
4. 发送汇总邮件
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from test_framework.interfaces.canoe_interface import CANoeInterface
from test_framework.services.notification_service import NotificationService
from test_framework.utils.logging_system import get_logger


def main():
    """主函数 - 多TSE文件顺序执行示例"""
    logger = get_logger(__name__)
    logger.info("开始多TSE文件顺序执行示例")
    
    # 配置多个TSE文件路径
    canoe_config = {
        'canoe': {
            'base_path': '/path/to/canoe/project',
            'configuration_path': '/path/to/canoe/config.cfg',
            # 支持多个TSE文件路径（按执行顺序排列）
            'tse_path': [
                'test_environments/basic_tests.tse',
                'test_environments/advanced_tests.tse',
                'test_environments/regression_tests.tse',
                'test_environments/performance_tests.tse'
            ]
        }
    }
    
    # 邮件通知配置
    notification_config = {
        'email': {
            'enabled': True,
            'smtp_server': 'smtp.company.com',
            'smtp_port': 587,
            'username': 'test@company.com',
            'password': 'your_password',
            'from_email': 'test@company.com',
            'to_emails': ['manager@company.com', 'team@company.com'],
            'use_tls': True
        },
        'wechat_robot': {
            'enabled': False,
            'webhook_url': 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key'
        }
    }
    
    try:
        # 1. 初始化CANoe接口
        logger.info("初始化CANoe接口...")
        canoe_interface = CANoeInterface(canoe_config)
        
        if not canoe_interface.is_connected:
            logger.error("CANoe接口初始化失败")
            return False
        
        # 2. 初始化通知服务
        logger.info("初始化通知服务...")
        notification_service = NotificationService(notification_config)
        
        # 3. 启动CANoe测量
        logger.info("启动CANoe测量...")
        if not canoe_interface.start_measurement():
            logger.error("启动CANoe测量失败")
            return False
        
        # 4. 按顺序运行所有TSE文件
        logger.info("开始按顺序运行所有TSE文件...")
        summary = canoe_interface.run_multiple_tse_files()
        
        if not summary:
            logger.error("运行TSE文件失败")
            return False
        
        # 5. 打印汇总结果
        logger.info("=== 测试执行汇总 ===")
        logger.info(f"总TSE文件数: {summary['total_tse_files']}")
        logger.info(f"成功完成: {summary['completed_tse_files']}")
        logger.info(f"执行失败: {summary['failed_tse_files']}")
        logger.info(f"总体测试结果: {summary['overall_stats']}")
        
        # 6. 获取合并的测试结果数据框
        combined_df = canoe_interface.get_combined_test_results_dataframe()
        if not combined_df.empty:
            logger.info(f"生成合并测试结果，共 {len(combined_df)} 条记录")
            
            # 保存合并结果到文件
            output_file = project_root / 'output' / 'combined_test_results.xlsx'
            output_file.parent.mkdir(parents=True, exist_ok=True)
            combined_df.to_excel(output_file, index=False)
            logger.info(f"合并测试结果已保存到: {output_file}")
        
        # 7. 发送汇总邮件
        logger.info("发送测试结果汇总邮件...")
        email_sent = canoe_interface.send_summary_email(summary, notification_service)
        
        if email_sent:
            logger.info("汇总邮件发送成功")
        else:
            logger.warning("汇总邮件发送失败")
        
        # 8. 停止CANoe测量
        logger.info("停止CANoe测量...")
        canoe_interface.stop_measurement()
        
        logger.info("多TSE文件顺序执行完成")
        return True
        
    except Exception as e:
        logger.error(f"执行过程中发生错误: {e}")
        return False
    
    finally:
        # 清理资源
        if 'canoe_interface' in locals():
            canoe_interface.cleanup()


def run_single_tse_example():
    """单TSE文件执行示例（向后兼容）"""
    logger = get_logger(__name__)
    logger.info("开始单TSE文件执行示例")
    
    # 单个TSE文件配置
    canoe_config = {
        'canoe': {
            'base_path': '/path/to/canoe/project',
            'configuration_path': '/path/to/canoe/config.cfg',
            # 单个TSE文件路径（向后兼容）
            'tse_path': 'test_environments/basic_tests.tse'
        }
    }
    
    try:
        # 初始化CANoe接口（会自动加载单个TSE文件）
        canoe_interface = CANoeInterface(canoe_config)
        
        if not canoe_interface.is_connected:
            logger.error("CANoe接口初始化失败")
            return False
        
        # 启动测量并运行测试
        canoe_interface.start_measurement()
        test_df = canoe_interface.run_test_modules()
        
        # 获取测试摘要
        summary = canoe_interface.get_test_summary()
        logger.info(f"单TSE测试结果: {summary}")
        
        # 停止测量
        canoe_interface.stop_measurement()
        
        return True
        
    except Exception as e:
        logger.error(f"单TSE执行过程中发生错误: {e}")
        return False
    
    finally:
        if 'canoe_interface' in locals():
            canoe_interface.cleanup()


if __name__ == '__main__':
    # 运行多TSE文件示例
    success = main()
    
    if success:
        print("多TSE文件顺序执行示例完成")
    else:
        print("多TSE文件顺序执行示例失败")
        sys.exit(1)
    
    # 可选：运行单TSE文件示例
    # run_single_tse_example()