# CANoe多TSE文件顺序执行功能

## 概述

本功能扩展了原有的CANoe测试框架，支持按顺序执行多个TSE（Test Setup Environment）文件，并在所有测试完成后汇总结果并发送邮件通知。

## 主要特性

- ✅ **多TSE文件支持**: 支持配置和执行多个TSE文件
- ✅ **顺序执行**: 按配置顺序依次执行每个TSE文件
- ✅ **智能测试用例匹配**: 根据TSE文件名自动匹配对应的测试用例组
- ✅ **结果汇总**: 自动汇总所有TSE文件的测试结果
- ✅ **多格式输出**: 支持Excel、CSV、JSON、HTML等多种格式的结果输出
- ✅ **邮件通知**: 执行完成后自动发送详细的测试结果邮件
- ✅ **向后兼容**: 完全兼容原有的单TSE文件执行方式
- ✅ **详细报告**: 生成包含统计信息和详细结果的HTML报告
- ✅ **错误处理**: 完善的错误处理和日志记录

## 文件结构

```
CANoe_py/
├── test_framework/
│   ├── executors/
│   │   └── multi_tse_executor.py       # 多TSE执行器
│   ├── interfaces/
│   │   └── canoe_interface.py          # 修改后的CANoe接口，支持多TSE
│   └── utils/
│       └── test_execution_utils.py     # 包含多TSE执行工具函数
├── config/
│   └── main_config.json                # 主配置文件（包含TSE路径配置）
├── temp_main.py                        # 主程序入口（集成多TSE功能）
└── README_MULTI_TSE.md                # 本说明文档
```

## TSE名称与测试用例匹配

### 匹配规则

系统会根据TSE文件名自动匹配对应的测试用例组：

- TSE文件名包含 `Diag` → 匹配 `testcases_Diag` 测试用例组
- TSE文件名包含 `Can` → 匹配 `testcases_Can` 测试用例组
- 其他情况 → 使用默认的 `test_cases` 测试用例组

### 示例

```
TSE文件: "Test_Diag_Module1.tse" → 使用 testcases_Diag 中启用的测试用例
TSE文件: "Test_Can_Module2.tse" → 使用 testcases_Can 中启用的测试用例
TSE文件: "General_Test.tse" → 使用 test_cases 中启用的测试用例
```

## 快速开始

### 1. 配置文件准备

创建或修改配置文件，将`tse_path`改为`tse_paths`列表格式：

```json
{
  "canoe": {
    "project_path": "C:/CANoe_Projects/MyProject.cfg",
    "tse_paths": [
      "C:/CANoe_Projects/TestEnvironments/Test_Diag_Module1.tse",
      "C:/CANoe_Projects/TestEnvironments/Test_Can_Module2.tse",
      "C:/CANoe_Projects/TestEnvironments/Test_Diag_Module3.tse"
    ],
    "canoe_exe_path": "C:/Program Files/Vector CANoe 16.0/Exec64/CANoe64.exe"
  },
  "task_config_path": "test_framework/config/task_config.json"
}
```

### 2. 使用主程序执行多TSE测试

```bash
# 使用多TSE模式（默认配置文件）
python3 temp_main.py --mode multi

# 使用多TSE模式并指定配置文件
python3 temp_main.py --mode multi --config test_framework/config/main_config.json

# 启用详细日志
python3 temp_main.py --mode multi --verbose
```

### 3. 使用单TSE模式（原有功能）

```bash
# 使用单TSE模式（默认）
python3 temp_main.py

# 或明确指定单TSE模式
python3 temp_main.py --mode single

# 指定任务配置文件
python3 temp_main.py --mode single --task-config test_framework/config/task_config.json
```

## 详细使用说明

### 配置文件格式

完整的配置文件示例请参考 `test_framework/config/main_config.json`，主要包含以下部分：

#### CANoe配置
```json
"canoe": {
  "project_path": "CANoe项目文件路径",
  "tse_paths": ["TSE文件路径列表"],
  "canoe_exe_path": "CANoe可执行文件路径",
  "timeout": 300,
  "auto_start_measurement": true
}
```

#### 邮件通知配置
```json
"notification": {
  "email": {
    "enabled": true,
    "smtp_server": "smtp.example.com",
    "smtp_port": 587,
    "username": "your_email@example.com",
    "password": "your_password",
    "sender": "CANoe测试系统 <canoe@example.com>",
    "recipients": ["recipient@example.com"],
    "subject_template": "CANoe多TSE测试结果 - {project_name}"
  }
}
```

#### 输出配置
```json
"output": {
  "base_directory": "output",
  "timestamp_folders": true,
  "formats": {
    "excel": true,
    "csv": true,
    "json": true,
    "html_report": true
  }
}
```

### 编程接口使用

#### 使用MultiTSEExecutor

```python
from test_framework.executors.multi_tse_executor import MultiTSEExecutor
from test_framework.utils.test_execution_utils import execute_multi_tse_workflow

# 方法1: 使用便捷函数
success = execute_multi_tse_workflow('test_framework/config/main_config.json')
if success:
    print("多TSE测试执行成功")
else:
    print("多TSE测试执行失败")

# 方法2: 直接使用MultiTSEExecutor
executor = MultiTSEExecutor('test_framework/config/main_config.json')
summary = executor.execute_all_tse_files()
print(f"执行完成，通过率: {summary['overall_stats']['pass_rate']:.2f}%")
```

#### 使用CANoeInterface（底层接口）

```python
from test_framework.interfaces.canoe_interface import CANoeInterface
from test_framework.services.notification_service import NotificationService

# 加载配置
config = {
    "canoe": {
        "project_path": "C:/CANoe_Projects/MyProject.cfg",
        "tse_paths": [
            "C:/CANoe_Projects/Test1.tse",
            "C:/CANoe_Projects/Test2.tse"
        ]
    },
    "notification": {
        "email": {
            "enabled": True,
            # ... 邮件配置
        }
    }
}

# 创建CANoe接口
canoe_interface = CANoeInterface(config)

# 启动测量
canoe_interface.start_measurement()

# 执行多TSE文件
summary = canoe_interface.run_multiple_tse_files()

# 获取合并的测试结果
combined_df = canoe_interface.get_combined_test_results_dataframe()

# 发送邮件通知
notification_service = NotificationService(config['notification'])
canoe_interface.send_summary_email(summary, notification_service)

# 停止测量和清理
canoe_interface.stop_measurement()
canoe_interface.cleanup()
```

#### 高级用法

```python
# 单独加载和执行特定TSE文件
canoe_interface.load_test_setup("C:/CANoe_Projects/SpecificTest.tse")
results = canoe_interface.run_tests()

# 获取特定TSE的结果
for i, tse_path in enumerate(canoe_interface.tse_paths):
    if i < len(canoe_interface.all_test_results):
        tse_results = canoe_interface.all_test_results[i]
        print(f"TSE {i+1} ({tse_path}): {len(tse_results)} 个测试结果")
```

## 输出结果

### 文件输出

执行完成后，会在输出目录生成以下文件：

```
output/
└── multi_tse_execution_20231201_143022/
    ├── combined_test_results.xlsx      # Excel格式的合并结果
    ├── combined_test_results.csv       # CSV格式的合并结果
    ├── test_execution_summary.json     # JSON格式的执行摘要
    └── test_execution_report.html      # HTML格式的详细报告
```

### 邮件通知

邮件包含以下内容：
- 执行概况（TSE文件数量、测试用例统计）
- 各TSE文件的详细结果
- 总体通过率和统计信息
- 附件（Excel结果文件）

### 控制台输出

```
多TSE文件执行摘要
============================================================
执行时间: 2023-12-01 14:30:22 - 2023-12-01 14:45:18
总耗时: 896.45 秒

TSE文件执行情况:
  总数: 3
  成功: 3
  失败: 0

总体测试结果:
  总测试用例: 45
  通过: 42
  失败: 2
  跳过: 1
  通过率: 93.33%

各TSE文件详细结果:
  1. C:/CANoe_Projects/Test1.tse
     测试用例: 15 | 通过: 14 | 失败: 1 | 跳过: 0 | 通过率: 93.33%
  2. C:/CANoe_Projects/Test2.tse
     测试用例: 20 | 通过: 19 | 失败: 1 | 跳过: 0 | 通过率: 95.00%
  3. C:/CANoe_Projects/Test3.tse
     测试用例: 10 | 通过: 9 | 失败: 0 | 跳过: 1 | 通过率: 90.00%
============================================================
```

## API参考

### CANoeInterface 新增方法

#### `run_multiple_tse_files() -> Dict[str, Any]`
按顺序执行所有配置的TSE文件并返回汇总结果。

**返回值:**
```python
{
    'total_tse_files': int,           # TSE文件总数
    'completed_tse_files': int,       # 成功完成的TSE文件数
    'failed_tse_files': int,          # 失败的TSE文件数
    'overall_stats': {               # 总体统计
        'total': int,
        'passed': int,
        'failed': int,
        'skipped': int,
        'pass_rate': float
    },
    'tse_results': [                 # 各TSE文件详细结果
        {
            'tse_index': int,
            'tse_path': str,
            'total': int,
            'passed': int,
            'failed': int,
            'skipped': int,
            'pass_rate': float
        }
    ]
}
```

#### `get_combined_test_results_dataframe() -> pd.DataFrame`
获取所有TSE文件的合并测试结果数据框。

**返回值:** 包含以下列的DataFrame:
- `TSE_File`: TSE文件路径
- `TestModule`: 测试模块名
- `TestGroup`: 测试组名
- `TestCase`: 测试用例名
- `TestResult`: 测试结果 (PASS/FAIL/SKIP)

#### `send_summary_email(summary: Dict[str, Any], notification_service: NotificationService) -> bool`
发送测试结果汇总邮件。

**参数:**
- `summary`: 测试结果汇总信息
- `notification_service`: 通知服务实例

**返回值:** 邮件发送是否成功

## 向后兼容性

新版本完全兼容原有的单TSE文件配置：

```json
// 原有格式（仍然支持）
"canoe": {
  "tse_path": "C:/CANoe_Projects/SingleTest.tse"
}

// 新格式（推荐）
"canoe": {
  "tse_paths": ["C:/CANoe_Projects/SingleTest.tse"]
}

// 多TSE文件格式
"canoe": {
  "tse_paths": [
    "C:/CANoe_Projects/Test1.tse",
    "C:/CANoe_Projects/Test2.tse",
    "C:/CANoe_Projects/Test3.tse"
  ]
}
```

## 注意事项

1. **TSE文件路径**: 确保所有TSE文件路径都是绝对路径且文件存在
2. **执行顺序**: TSE文件将按照配置文件中的顺序依次执行
3. **资源管理**: 每个TSE文件执行完成后会自动清理资源
4. **错误处理**: 单个TSE文件执行失败不会影响后续文件的执行
5. **邮件配置**: 确保SMTP服务器配置正确，否则邮件发送会失败
6. **输出目录**: 输出目录会自动创建，建议定期清理旧的结果文件

## 故障排除

### 常见问题

1. **TSE文件加载失败**
   - 检查文件路径是否正确
   - 确认文件是否存在且可读
   - 验证TSE文件格式是否正确

2. **邮件发送失败**
   - 检查SMTP服务器配置
   - 验证用户名和密码
   - 确认网络连接正常

3. **CANoe连接失败**
   - 确认CANoe软件已安装
   - 检查CANoe可执行文件路径
   - 验证CANoe项目文件是否存在

### 日志查看

日志文件位于 `logs/` 目录下，包含详细的执行信息和错误信息。

## 更新日志

### v2.2.0 (2024-12-19)
- ✅ 新增TSE名称与测试用例智能匹配功能
- ✅ 支持根据TSE文件名自动选择对应的测试用例组
- ✅ 更新 `get_enabled_test_cases` 函数支持TSE名称参数
- ✅ 新增 `get_testcase_group_from_tse_name` 函数
- ✅ 修改 `run_multiple_tse_files` 方法支持任务配置
- ✅ 更新多TSE执行器支持任务配置文件路径
- ✅ 完善文档说明匹配规则和使用方法

### v2.1.0 (2023-12-01)
- ✅ 多TSE功能集成到主程序入口
- ✅ 新增命令行参数支持（--mode, --config, --task-config, --verbose）
- ✅ 统一单TSE和多TSE执行入口
- ✅ 创建MultiTSEExecutor执行器类
- ✅ 添加便捷函数到test_execution_utils
- ✅ 移除独立的多TSE主程序文件

### v2.0.0 (2023-12-01)
- ✅ 新增多TSE文件顺序执行功能
- ✅ 新增结果汇总和合并功能
- ✅ 新增HTML报告生成
- ✅ 改进邮件通知功能
- ✅ 保持向后兼容性

## 技术支持

如有问题或建议，请联系开发团队或查看项目文档。