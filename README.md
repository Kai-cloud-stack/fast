# 测试框架 (Test Framework)

一个模块化的自动化测试系统，支持配置验证、环境检查、测试用例执行、刷写操作和结果通知等功能。

## 项目结构

```
test_framework/
├── core/                    # 核心模块
│   ├── main_controller.py   # 主控制器
│   ├── config_manager.py    # 配置管理器
│   └── logger_manager.py    # 日志管理器
├── checkers/                # 检查器模块
│   ├── environment_checker.py  # 环境检查器
│   └── config_validator.py     # 配置验证器
├── executors/               # 执行器模块
│   ├── task_executor.py     # 任务执行器
│   ├── test_runner.py       # 测试运行器
│   └── flash_manager.py     # 刷写管理器
├── interfaces/              # 接口模块
│   ├── canoe_interface.py   # CANoe接口
│   └── python_test_executor.py  # Python测试执行器
├── services/                # 服务模块
│   ├── notification_service.py  # 通知服务
│   ├── data_archiver.py         # 数据归档器
│   └── package_manager.py       # 软件包管理器
├── utils/                   # 工具模块
│   ├── file_utils.py        # 文件工具
│   └── email_utils.py       # 邮件工具
└── config/                  # 配置文件目录
    ├── main_config.json     # 主配置文件
    └── task_config.json     # 任务配置文件
```

## 功能特性

- **模块化架构**: 采用模块化设计，便于扩展和维护
- **配置管理**: 支持JSON格式的配置文件，灵活配置系统参数
- **日志管理**: 完善的日志记录系统，支持文件轮转和多级别日志
- **CANoe集成**: 与CANoe/CAPL无缝集成，支持现有测试用例
- **错误处理**: 完善的错误处理和恢复机制
- **邮件通知**: 自动发送测试结果和错误通知邮件
- **数据归档**: 自动归档测试数据和报告

## 快速开始

1. 配置主配置文件 `test_framework/config/main_config.json`
2. 配置任务配置文件 `test_framework/config/task_config.json`
3. 运行测试框架：

```bash
python main.py
```

## 配置说明

### 主配置文件 (main_config.json)

包含系统级配置，如CANoe路径、邮件服务器、日志配置等。

### 任务配置文件 (task_config.json)

包含具体的测试任务配置，如测试用例列表、刷写配置等。

## 开发状态

当前实现了基础的项目结构和核心模块框架，包括：

- ✅ 项目目录结构
- ✅ 主控制器类框架
- ✅ 配置管理器类框架
- ✅ 日志管理器类框架
- ✅ 各模块基础接口

## CANoe功能集成

### 已完成的CANoe集成功能

`test_framework/interfaces/canoe_interface.py` 现已集成完整的CANoe自动化控制功能：

#### 核心功能
- **CANoe应用程序控制**: 启动、停止、版本检测
- **配置管理**: 加载CANoe配置文件(.cfg)
- **测试环境管理**: 加载和管理测试环境(.tse)
- **测量控制**: 启动/停止CANoe测量
- **测试模块执行**: 自动运行测试模块并收集结果

#### 测试结果处理
- **结果收集**: 自动收集测试用例执行结果
- **数据统计**: 生成测试通过率、失败率等统计信息
- **报告生成**: 支持XML格式测试报告
- **日志记录**: 完整的测试过程日志
- **邮件通知**: 支持测试结果和错误信息的邮件通知

#### 事件处理
- **测试事件**: 监听测试开始、停止、报告生成事件
- **测量事件**: 监听CANoe测量状态变化
- **异步处理**: 支持Windows消息队列处理

#### 使用方式

```python
from test_framework.interfaces.canoe_interface import CANoeInterface

# 配置参数
canoe_config = {
    'project_path': 'P20_basic',
    'tse_path': 'TestEnvironments/P181_ADC25_J_v15.tse'
}

# 创建接口实例
canoe = CANoeInterface(canoe_config)

# 分步骤操作
canoe.start_canoe_application()
canoe.load_configuration("config.cfg")
canoe.load_test_setup()
canoe.select_test_cases(["TestCase_001", "TestCase_002"])
canoe.start_measurement()
results = canoe.run_test_modules()
summary = canoe.get_test_summary()
```

### 邮件通知服务

`test_framework/services/notification_service.py` 提供了完整的邮件通知功能，支持发送测试结果和错误信息。

#### 核心功能
- **HTML邮件**: 支持富文本格式的邮件内容
- **表格展示**: 自动生成测试结果表格
- **失败标记**: 自动标红失败的测试用例
- **统计信息**: 显示异常项数量
- **错误通知**: 支持系统错误和异常的邮件通知

#### 使用示例

```python
from test_framework.services.notification_service import NotificationService

# 邮件配置
email_config = {
    'recipient': 'kai.ren@freetech.com'
}

# 初始化通知服务
notification_service = NotificationService(email_config)

# 发送测试结果通知
test_results = {
    'Test_SWDL': 'v1.2.3',
    'Test_InnerReleaseVersion': 'ERROR: 无法读取版本',
    'Test_ExternalReleaseVersion': 'v1.5.2'
}
failed_cases = ['Test_InnerReleaseVersion']

notification_service.send_test_result_notification(test_results, failed_cases)

# 发送错误通知
error_info = {
    '错误类型': 'CANoe连接失败',
    '错误时间': '2024-01-15 14:30:25',
    '错误描述': 'CANoe应用程序无法启动'
}
notification_service.send_error_notification(error_info)
 ```

### 微信通知服务

框架集成了企业微信机器人通知功能，支持发送测试结果、错误信息和自定义消息到微信群。

#### 配置说明

微信通知配置位于 `test_framework/config/main_config.json` 文件中：

```json
"wechat": {
    "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your-key",
    "timeout": 10,
    "retry_count": 3,
    "default_mentioned_users": [],
    "enable_notification": true
}
```

#### 核心功能
- **文本消息发送**: 支持发送格式化的文本消息
- **@用户功能**: 支持@指定用户或@所有人
- **测试结果通知**: 自动统计测试结果并发送格式化报告
- **错误通知**: 发送系统异常和错误信息
- **表情符号**: 支持emoji表情增强消息可读性
- **配置化管理**: webhook地址等配置从配置文件读取
- **开关控制**: 可通过配置文件启用/禁用微信通知
- **默认@用户**: 通过default_mentioned_users配置默认@的用户
- **异常处理**: 网络异常时自动记录日志

#### default_mentioned_users配置说明

`default_mentioned_users` 字段控制在发送测试结果和错误通知时默认@哪些用户：

- **空数组 `[]`**: 不@任何人（推荐设置）
- **@所有人 `["@all"]`**: @群内所有成员
- **指定用户 `["13800138000", "13900139000"]`**: @指定手机号的用户

> 💡 **注意**: 当调用 `send_wechat_test_result()` 或 `send_wechat_error_notification()` 方法时，如果不传入 `mentioned_mobile_list` 参数，系统会自动使用 `default_mentioned_users` 的配置。

#### 使用示例

```python
import json
from test_framework.services.notification_service import NotificationService

# 加载配置文件
with open('test_framework/config/main_config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
wechat_config = config.get('wechat', {})

# 初始化通知服务
notification_service = NotificationService(wechat_config=wechat_config)

# 发送基础微信通知
content = "🤖 FAST自动化测试平台\n\n✅ 系统启动成功！"
notification_service.send_wechat_notification(content)

# @指定用户发送通知
mentioned_users = ["13800138000", "13900139000"]
notification_service.send_wechat_notification(content, mentioned_users)

# @所有人发送通知
notification_service.send_wechat_notification(content, ["@all"])

# 发送测试结果通知
test_results = [
    {"name": "Test_SWDL", "result": "✅ 通过"},
    {"name": "Test_UDS_Service", "result": "❌ 失败"},
    {"name": "Test_CAN_Communication", "result": "✅ 通过"}
]
notification_service.send_wechat_test_result(test_results)

# 发送错误通知
error_info = {
    "error_type": "CANoe连接异常",
    "error_message": "无法连接到CANoe应用程序",
    "component": "CANoeInterface",
    "timestamp": "2024-01-15 14:25:30"
}
notification_service.send_wechat_error_notification(error_info)
```

#### CANoe操作完整示例

```python
# CANoe操作完整流程
canoe.stop_measurement()
canoe.cleanup()
```

### 依赖包

项目已创建 `requirements.txt` 文件，包含所有必需的依赖包：
- `pandas`: 数据处理和结果分析
- `pywin32`: Windows COM接口支持
- `pyyaml`: 配置文件处理
- 其他支持包

### 使用示例

参考 `example_usage.py` 文件了解详细的使用方法和最佳实践。

## 下一步开发计划

1. ✅ ~~CANoe接口的具体实现~~ (已完成)
2. 配置验证器的具体实现
3. 测试用例执行逻辑优化
4. 刷写管理功能
5. 邮件通知和数据归档功能
6. 集成测试和错误处理优化

## 技术栈

- **Python 3.8+**: 主要开发语言
- **CANoe/CAPL**: 测试环境和用例执行
- **pywin32**: Windows COM接口
- **pandas**: 数据处理和分析
- **JSON/YAML**: 配置文件格式
- **Logging**: Python标准日志库