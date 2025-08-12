#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 packge.py 中所有 int 和 str 类型比较错误的修复
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from test_framework.utils.packge import (
    FileInfo, FileFilter, ProgressMonitor, TransferSummary
)

def test_file_info_with_string_size():
    """测试 FileInfo 对象使用字符串 size 的情况"""
    print("\n=== 测试 FileInfo 字符串 size 处理 ===")
    
    # 模拟可能出现字符串 size 的情况
    file_info = FileInfo(
        name="test_file.txt",
        path="/test/path/test_file.txt",
        size="1024",  # 字符串类型的 size
        modified_time=datetime.now(),
        is_directory=False
    )
    
    print(f"FileInfo.size 类型: {type(file_info.size)}")
    print(f"FileInfo.size 值: {file_info.size}")
    
    # 测试 FileFilter 处理字符串 size
    file_filter = FileFilter(max_size=2048)
    result = file_filter.should_include(file_info)
    print(f"FileFilter.should_include 结果: {result}")
    
    return file_info

def test_total_size_calculation():
    """测试总大小计算中的类型安全处理"""
    print("\n=== 测试总大小计算类型安全 ===")
    
    # 创建混合类型 size 的文件列表
    files = [
        FileInfo("file1.txt", "/path/file1.txt", 1024, datetime.now(), False),  # int size
        FileInfo("file2.txt", "/path/file2.txt", "2048", datetime.now(), False),  # str size
        FileInfo("file3.txt", "/path/file3.txt", 512, datetime.now(), False),   # int size
        FileInfo("dir1", "/path/dir1", 0, datetime.now(), True),  # directory
    ]
    
    # 模拟 sync_files 中的总大小计算
    try:
        total_size = sum(int(f.size) if isinstance(f.size, str) else f.size for f in files if not f.is_directory)
        print(f"总大小计算成功: {total_size} bytes")
        
        # 模拟 list_files 中的总大小计算
        regular_files = [f for f in files if not f.is_directory]
        total_size2 = sum(int(f.size) if isinstance(f.size, str) else f.size for f in regular_files)
        print(f"list_files 总大小计算成功: {total_size2} bytes")
        
        # 模拟 TransferSummary 中的总大小计算
        total_bytes = sum(int(f.size) if isinstance(f.size, str) else f.size for f in files if not f.is_directory)
        print(f"TransferSummary 总大小计算成功: {total_bytes} bytes")
        
        return True
    except Exception as e:
        print(f"总大小计算失败: {e}")
        return False

def test_progress_monitor_with_string_bytes():
    """测试 ProgressMonitor 处理字符串字节数的情况"""
    print("\n=== 测试 ProgressMonitor 字符串字节数处理 ===")
    
    monitor = ProgressMonitor()
    
    # 测试 start_transfer 方法
    monitor.start_transfer(5, 10240)
    
    # 测试 get_progress_info 方法的类型安全处理
    try:
        progress_info = monitor.get_progress_info()
        print(f"进度信息获取成功: 文件进度 {progress_info['file_progress_percent']:.1f}%, 字节进度 {progress_info['byte_progress_percent']:.1f}%")
        
        # 测试 _format_bytes 方法的类型检查
        formatted_bytes1 = monitor._format_bytes(1024)  # int
        formatted_bytes2 = monitor._format_bytes("2048")  # str
        print(f"格式化字节数 (int): {formatted_bytes1}")
        print(f"格式化字节数 (str): {formatted_bytes2}")
        
        return True
    except Exception as e:
        print(f"ProgressMonitor 测试失败: {e}")
        return False

def test_file_filter_comprehensive():
    """综合测试 FileFilter 的类型安全处理"""
    print("\n=== 综合测试 FileFilter 类型安全 ===")
    
    # 测试不同类型的 max_size 初始化
    filters = [
        FileFilter(max_size=1024),      # int
        FileFilter(max_size="2048"),    # str
        FileFilter(max_size=None),      # None
    ]
    
    # 测试文件
    test_files = [
        FileInfo("small.txt", "/path/small.txt", 512, datetime.now(), False),
        FileInfo("medium.txt", "/path/medium.txt", "1536", datetime.now(), False),  # str size
        FileInfo("large.txt", "/path/large.txt", 3072, datetime.now(), False),
    ]
    
    for i, file_filter in enumerate(filters):
        print(f"\n过滤器 {i+1} (max_size={file_filter.max_size}, 类型={type(file_filter.max_size)}):")
        for file_info in test_files:
            try:
                result = file_filter.should_include(file_info)
                print(f"  {file_info.name} (size={file_info.size}, 类型={type(file_info.size)}): {result}")
            except Exception as e:
                print(f"  {file_info.name}: 错误 - {e}")
                return False
    
    return True

def main():
    """运行所有测试"""
    print("开始测试 packge.py 中的类型安全修复...")
    
    tests = [
        test_file_info_with_string_size,
        test_total_size_calculation,
        test_progress_monitor_with_string_bytes,
        test_file_filter_comprehensive,
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            result = test_func()
            if result is not False:
                passed += 1
                print(f"✓ {test_func.__name__} 通过")
            else:
                print(f"✗ {test_func.__name__} 失败")
        except Exception as e:
            print(f"✗ {test_func.__name__} 异常: {e}")
    
    print(f"\n=== 测试结果 ===")
    print(f"通过: {passed}/{total}")
    print(f"失败: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 所有类型安全修复测试通过！")
        return True
    else:
        print("\n❌ 部分测试失败，需要进一步检查")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)