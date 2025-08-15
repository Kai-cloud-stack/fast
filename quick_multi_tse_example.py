#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速多TSE文件执行示例
Quick Multiple TSE Files Execution Example

这是一个简化的示例，展示如何快速配置和执行多个TSE文件。
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from test_framework.interfaces.canoe_interface import CANoeInterface
from test_framework.services.notification_service import NotificationService


def quick_multi_tse_execution():
    """快速多TSE文件执行示例"""
    
    # 配置信息（实际使用时请根据您的环境修改）
    config = {
        "project": {
            "name": "多TSE测试项目",
            "version": "1.0.0",
            "description": "CANoe多TSE文件顺序执行测试"
        },
        "canoe": {
            "project_path": "C:/CANoe_Projects/MyProject.cfg",
            "tse_path": [
                "C:/CANoe_Projects/TestEnvironments/Test1.tse",
                "C:/CANoe_Projects/TestEnvironments/Test2.tse",
                "C:/CANoe_Projects/TestEnvironments/Test3.tse"
            ],
            "canoe_exe_path": "C:/Program Files/Vector CANoe 16.0/Exec64/CANoe64.exe",
            "timeout": 300,
            "auto_start_measurement": True
        },
        "logging": {
            "level": "INFO",
            "log_directory": "logs",
            "max_log_files": 10
        },
        "notification": {
            "email": {
                "enabled": True,
                "smtp_server": "smtp.example.com",
                "smtp_port": 587,
                "username": "your_email@example.com",
                "password": "your_password",
                "sender": "CANoe测试系统 <canoe@example.com>",
                "recipients": [
                    "test_team@example.com",
                    "manager@example.com"
                ],
                "subject_template": "CANoe多TSE测试结果 - {project_name}",
                "include_attachments": True
            },
            "wechat_robot": {
                "enabled": False,
                "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key"
            }
        },
        "output": {
            "base_directory": "output",
            "timestamp_folders": True,
            "formats": {
                "excel": True,
                "csv": True,
                "json": True,
                "html_report": True
            },
            "file_naming": {
                "combined_results": "combined_test_results",
                "summary_report": "test_execution_summary"
            }
        },
        "test_execution": {
            "stop_on_first_failure": False,
            "parallel_execution": False,
            "retry_failed_tests": False,
            "max_retries": 1
        }
    }
    
    canoe_interface = None
    
    try:
        print("开始多TSE文件顺序执行示例...")
        
        # 1. 创建CANoe接口实例
        print("初始化CANoe接口...")
        canoe_interface = CANoeInterface(config)
        
        if not canoe_interface.is_connected:
            print("❌ CANoe接口初始化失败")
            return False
        
        print(f"✅ CANoe接口初始化成功，发现 {len(canoe_interface.tse_paths)} 个TSE文件")
        
        # 2. 启动CANoe测量
        print("启动CANoe测量...")
        if not canoe_interface.start_measurement():
            print("❌ 启动CANoe测量失败")
            return False
        
        print("✅ CANoe测量启动成功")
        
        # 3. 执行多TSE文件
        print("\n开始执行多TSE文件...")
        print("="*50)
        
        summary = canoe_interface.run_multiple_tse_files()
        
        if not summary:
            print("❌ 多TSE文件执行失败")
            return False
        
        # 4. 显示执行结果
        print("\n" + "="*50)
        print("执行结果摘要")
        print("="*50)
        
        print(f"TSE文件执行情况:")
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
            print(f"  {tse_result['tse_index']}. {Path(tse_result['tse_path']).name}")
            print(f"     测试用例: {tse_result['total']} | 通过: {tse_result['passed']} | 失败: {tse_result['failed']} | 跳过: {tse_result['skipped']} | 通过率: {tse_result['pass_rate']:.2f}%")
        
        # 5. 获取合并的测试结果
        print("\n获取详细测试结果...")
        combined_df = canoe_interface.get_combined_test_results_dataframe()
        
        if not combined_df.empty:
            print(f"✅ 获取到 {len(combined_df)} 条测试结果记录")
            
            # 保存结果到文件
            output_dir = Path("output/quick_example")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            excel_file = output_dir / "combined_results.xlsx"
            combined_df.to_excel(excel_file, index=False)
            print(f"✅ 结果已保存到: {excel_file}")
        else:
            print("⚠️ 未获取到测试结果数据")
        
        # 6. 发送邮件通知（如果配置了的话）
        if config['notification']['email']['enabled']:
            print("\n发送邮件通知...")
            notification_service = NotificationService(config['notification'])
            
            email_sent = canoe_interface.send_summary_email(summary, notification_service)
            
            if email_sent:
                print("✅ 邮件通知发送成功")
            else:
                print("⚠️ 邮件通知发送失败")
        
        # 7. 停止CANoe测量
        print("\n停止CANoe测量...")
        canoe_interface.stop_measurement()
        print("✅ CANoe测量已停止")
        
        print("\n🎉 多TSE文件顺序执行完成！")
        return True
        
    except Exception as e:
        print(f"❌ 执行过程中发生错误: {e}")
        return False
        
    finally:
        # 清理资源
        if canoe_interface:
            canoe_interface.cleanup()
            print("✅ 资源清理完成")


def main():
    """主函数"""
    print("CANoe多TSE文件顺序执行快速示例")
    print("="*40)
    
    # 提示用户修改配置
    print("\n⚠️ 注意: 请在运行前修改脚本中的配置信息:")
    print("  - CANoe项目路径 (project_path)")
    print("  - TSE文件路径列表 (tse_path)")
    print("  - CANoe可执行文件路径 (canoe_exe_path)")
    print("  - 邮件服务器配置 (notification.email)")
    print("\n按回车键继续，或按Ctrl+C退出...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n用户取消执行")
        return
    
    # 执行示例
    success = quick_multi_tse_execution()
    
    if success:
        print("\n✅ 示例执行成功")
    else:
        print("\n❌ 示例执行失败")


if __name__ == '__main__':
    main()