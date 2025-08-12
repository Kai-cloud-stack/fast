# _*_coding:utf-8_*_
"""
@statement: Copyright(c) 2024 FreeTech Automated Testing CO.LTD
@file     : file_ctrl
@date     : 2025/8/5
@author   : <kai.ren@freetech.com>
@describe : 从Windows共享路径拉取所有文件到本地目录的功能实现。
支持文件过滤、进度监控、错误处理和并发传输。
"""

import os
import shutil
import asyncio
import logging
import fnmatch
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Callable, Union
import time


# 自定义异常类层次结构
class WindowsFileSyncError(Exception):
    """基础异常类"""
    pass


class ShareAccessError(WindowsFileSyncError):
    """共享路径访问错误"""
    pass


class AuthenticationError(WindowsFileSyncError):
    """身份验证错误"""
    pass


class FileAccessError(WindowsFileSyncError):
    """文件访问错误"""
    pass


class TransferError(WindowsFileSyncError):
    """传输错误"""
    pass


class ZipProcessingError(WindowsFileSyncError):
    """ZIP文件处理错误"""
    pass


# 核心数据模型
@dataclass
class FileInfo:
    """文件信息数据类"""
    name: str
    path: str
    size: int
    modified_time: datetime
    is_directory: bool
    permissions: Optional[str] = None


@dataclass
class TransferResult:
    """单个文件传输结果"""
    file_info: FileInfo
    success: bool
    local_path: Optional[Path]
    error_message: Optional[str] = None
    bytes_transferred: int = 0
    transfer_time: float = 0.0


@dataclass
class TransferSummary:
    """传输摘要"""
    total_files: int
    successful_files: int
    failed_files: int
    skipped_files: int
    total_bytes: int
    transferred_bytes: int
    total_time: float
    errors: List[str]


@dataclass
class ZipProcessingSummary:
    """ZIP处理摘要"""
    total_zip_files: int
    processed_zip_files: int
    failed_zip_files: int
    extracted_files: int
    merged_directories: List[str]
    processing_time: float
    errors: List[str]


@dataclass
class SyncConfig:
    """同步配置"""
    max_concurrent_transfers: int = 5
    connection_timeout: int = 30
    read_timeout: int = 60
    retry_attempts: int = 3
    retry_delay: float = 1.0
    chunk_size: int = 64 * 1024  # 64KB
    log_level: str = "INFO"
    verify_transfers: bool = True  # 验证传输完整性
    create_backup: bool = False    # 是否创建备份

    def validate(self):
        """验证配置参数"""
        if self.max_concurrent_transfers < 1:
            raise ValueError("max_concurrent_transfers 必须大于 0")
        if self.retry_attempts < 0:
            raise ValueError("retry_attempts 不能为负数")
        if self.chunk_size < 1024:
            raise ValueError("chunk_size 不能小于 1024 字节")
        if self.log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            raise ValueError("无效的日志级别")


# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WindowsShareManager:
    """管理Windows共享路径访问"""

    def __init__(self, share_path: str):
        self.share_path = share_path
        self.normalized_path = self.normalize_path()
        logger.info(f"初始化Windows共享管理器: {self.normalized_path}")

    def validate_path(self) -> bool:
        """验证UNC路径格式和可访问性"""
        try:
            # 检查UNC路径格式
            if not self.share_path.startswith(('\\\\', '//')):
                raise ShareAccessError(f"无效的UNC路径格式: {self.share_path}")

            # 检查路径是否存在和可访问
            if not os.path.exists(self.normalized_path):
                raise ShareAccessError(f"共享路径不存在或无法访问: {self.normalized_path}")

            # 检查是否有读取权限
            if not os.access(self.normalized_path, os.R_OK):
                raise ShareAccessError(f"没有读取权限: {self.normalized_path}")

            logger.info(f"路径验证成功: {self.normalized_path}")
            return True

        except OSError as e:
            error_msg = f"路径访问错误: {e}"
            logger.error(error_msg)
            raise ShareAccessError(error_msg)

    def normalize_path(self) -> str:
        """标准化UNC路径格式"""
        # 将正斜杠转换为反斜杠（Windows标准）
        normalized = self.share_path.replace('/', '\\')

        # 确保以双反斜杠开头
        if not normalized.startswith('\\\\'):
            if normalized.startswith('\\'):
                normalized = '\\' + normalized
            else:
                normalized = '\\\\' + normalized

        # 移除末尾的反斜杠
        normalized = normalized.rstrip('\\')

        logger.debug(f"路径标准化: {self.share_path} -> {normalized}")
        return normalized

    def test_access(self) -> bool:
        """测试路径访问权限"""
        try:
            # 尝试列出目录内容
            os.listdir(self.normalized_path)
            logger.info(f"访问测试成功: {self.normalized_path}")
            return True
        except PermissionError:
            logger.error(f"权限不足: {self.normalized_path}")
            raise AuthenticationError(f"没有访问权限: {self.normalized_path}")
        except OSError as e:
            logger.error(f"访问测试失败: {e}")
            raise ShareAccessError(f"无法访问共享路径: {e}")

    def get_share_info(self) -> dict:
        """获取共享路径信息"""
        try:
            stat_info = os.stat(self.normalized_path)
            return {
                'path': self.normalized_path,
                'exists': True,
                'is_directory': os.path.isdir(self.normalized_path),
                'modified_time': datetime.fromtimestamp(stat_info.st_mtime),
                'accessible': self.test_access()
            }
        except Exception as e:
            logger.error(f"获取共享信息失败: {e}")
            return {
                'path': self.normalized_path,
                'exists': False,
                'error': str(e)
            }


class FileDiscoveryService:
    """负责遍历和发现共享路径中的文件"""

    def __init__(self, share_manager: WindowsShareManager):
        self.share_manager = share_manager
        logger.info("初始化文件发现服务")

    async def discover_files(self,
                           remote_path: str = "",
                           file_filter: Optional['FileFilter'] = None) -> List[FileInfo]:
        """使用os.walk递归发现所有文件"""
        files = []
        base_path = os.path.join(self.share_manager.normalized_path, remote_path.lstrip('\\'))

        logger.info(f"开始发现文件: {base_path}")

        try:
            for root, dirs, filenames in os.walk(base_path):
                # 处理文件
                for filename in filenames:
                    try:
                        file_path = os.path.join(root, filename)
                        file_info = await self.get_file_info(file_path)

                        # 应用文件过滤器
                        if file_filter is None or file_filter.should_include(file_info):
                            files.append(file_info)
                            logger.debug(f"发现文件: {file_info.name}")
                        else:
                            logger.debug(f"文件被过滤: {file_info.name}")

                    except (PermissionError, OSError) as e:
                        logger.warning(f"无法访问文件 {filename}: {e}")
                        continue

                # 处理目录（如果需要）
                for dirname in dirs:
                    try:
                        dir_path = os.path.join(root, dirname)
                        dir_info = await self.get_file_info(dir_path)

                        # 如果过滤器允许目录，则添加
                        if file_filter is None or file_filter.should_include(dir_info):
                            files.append(dir_info)
                            logger.debug(f"发现目录: {dir_info.name}")

                    except (PermissionError, OSError) as e:
                        logger.warning(f"无法访问目录 {dirname}: {e}")
                        # 移除无法访问的目录，避免进一步遍历
                        dirs.remove(dirname)
                        continue

        except (PermissionError, OSError) as e:
            error_msg = f"遍历目录失败: {e}"
            logger.error(error_msg)
            raise FileAccessError(error_msg)

        logger.info(f"文件发现完成，共找到 {len(files)} 个项目")
        return files

    async def get_file_info(self, file_path: str) -> FileInfo:
        """使用os.stat获取文件详细信息"""
        try:
            stat_info = os.stat(file_path)

            # 处理文件名编码问题
            try:
                # 尝试使用UTF-8编码
                filename = os.path.basename(file_path)
                if isinstance(filename, bytes):
                    filename = filename.decode('utf-8', errors='replace')
            except UnicodeDecodeError:
                # 如果UTF-8失败，使用系统默认编码
                filename = os.path.basename(file_path)
                if isinstance(filename, bytes):
                    filename = filename.decode('gbk', errors='replace')

            file_info = FileInfo(
                name=filename,
                path=file_path,
                size=int(stat_info.st_size),  # 确保大小是整数类型
                modified_time=datetime.fromtimestamp(stat_info.st_mtime),
                is_directory=os.path.isdir(file_path),
                permissions=oct(stat_info.st_mode)[-3:]  # 获取权限的最后3位
            )

            return file_info

        except (OSError, PermissionError) as e:
            error_msg = f"获取文件信息失败 {file_path}: {e}"
            logger.error(error_msg)
            raise FileAccessError(error_msg)

    async def get_directory_size(self, dir_path: str) -> int:
        """计算目录总大小"""
        total_size = 0
        try:
            for root, dirs, files in os.walk(dir_path):
                for filename in files:
                    try:
                        file_path = os.path.join(root, filename)
                        total_size += os.path.getsize(file_path)
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError) as e:
            logger.warning(f"计算目录大小失败 {dir_path}: {e}")

        return total_size


class FileFilter:
    """文件过滤配置"""

    def __init__(self,
                 extensions: Optional[List[str]] = None,
                 max_size: Optional[int] = None,
                 exclude_patterns: Optional[List[str]] = None,
                 include_directories: bool = True,
                 filename_prefixes: Optional[List[str]] = None,
                 filename_suffixes: Optional[List[str]] = None):
        self.extensions = [ext.lower().lstrip('.') for ext in (extensions or [])]
        # 确保 max_size 是整数类型或 None
        if max_size is not None:
            try:
                self.max_size = int(max_size)
            except (ValueError, TypeError):
                logger.warning(f"无效的 max_size 值: {max_size}, 将忽略大小限制")
                self.max_size = None
        else:
            self.max_size = None
        self.exclude_patterns = exclude_patterns or []
        self.include_directories = include_directories
        self.filename_prefixes = [prefix.lower() for prefix in (filename_prefixes or [])]
        self.filename_suffixes = [suffix.lower() for suffix in (filename_suffixes or [])]

        logger.info(f"初始化文件过滤器 - 扩展名: {self.extensions}, "
                   f"最大大小: {self.max_size}, 排除模式: {self.exclude_patterns}, "
                   f"文件名前缀: {self.filename_prefixes}, 文件名后缀: {self.filename_suffixes}")

    def should_include(self, file_info: FileInfo) -> bool:
        """判断文件是否应该被包含"""

        # 目录处理
        if file_info.is_directory:
            if not self.include_directories:
                return False
            # 检查目录是否匹配排除模式
            return not self._matches_exclude_patterns(file_info.name, file_info.path)

        # 文件大小过滤
        if self.max_size is not None:
            try:
                # 确保文件大小和最大大小都是整数类型
                file_size = int(file_info.size) if isinstance(file_info.size, str) else file_info.size
                max_size = int(self.max_size) if isinstance(self.max_size, str) else self.max_size
                if file_size > max_size:
                    logger.debug(f"文件 {file_info.name} 超过大小限制: {file_size} > {max_size}")
                    return False
            except (ValueError, TypeError) as e:
                logger.warning(f"文件大小比较失败 {file_info.name}: {e}, 跳过大小检查")
                # 如果类型转换失败，跳过大小检查，继续其他过滤条件

        # 扩展名过滤
        if self.extensions:
            file_ext = self._get_file_extension(file_info.name)
            if file_ext not in self.extensions:
                logger.debug(f"文件 {file_info.name} 扩展名不匹配: {file_ext} not in {self.extensions}")
                return False

        # 文件名前缀过滤
        if self.filename_prefixes:
            filename_lower = file_info.name.lower()
            if not any(filename_lower.startswith(prefix) for prefix in self.filename_prefixes):
                logger.debug(f"文件 {file_info.name} 前缀不匹配: 不以 {self.filename_prefixes} 中任何一个开头")
                return False

        # 文件名后缀过滤（不包括扩展名）
        if self.filename_suffixes:
            # 获取不含扩展名的文件名
            filename_without_ext = file_info.name
            if '.' in filename_without_ext:
                filename_without_ext = '.'.join(filename_without_ext.split('.')[:-1])
            filename_lower = filename_without_ext.lower()

            if not any(filename_lower.endswith(suffix) for suffix in self.filename_suffixes):
                logger.debug(f"文件 {file_info.name} 后缀不匹配: 不以 {self.filename_suffixes} 中任何一个结尾")
                return False

        # 排除模式过滤
        if self._matches_exclude_patterns(file_info.name, file_info.path):
            logger.debug(f"文件 {file_info.name} 匹配排除模式")
            return False

        return True

    def _get_file_extension(self, filename: str) -> str:
        """获取文件扩展名（小写，不含点）"""
        if '.' in filename:
            return filename.split('.')[-1].lower()
        return ''

    def _matches_exclude_patterns(self, filename: str, filepath: str) -> bool:
        """检查文件是否匹配排除模式"""
        for pattern in self.exclude_patterns:
            # 支持通配符模式
            if fnmatch.fnmatch(filename.lower(), pattern.lower()):
                return True

            # 支持正则表达式模式（以regex:开头）
            if pattern.startswith('regex:'):
                regex_pattern = pattern[6:]  # 移除'regex:'前缀
                try:
                    if re.search(regex_pattern, filename, re.IGNORECASE):
                        return True
                except re.error:
                    logger.warning(f"无效的正则表达式模式: {regex_pattern}")

            # 支持路径模式匹配
            if fnmatch.fnmatch(filepath.lower(), pattern.lower()):
                return True

        return False

    def get_filter_summary(self) -> dict:
        """获取过滤器配置摘要"""
        return {
            'extensions': self.extensions,
            'max_size': self.max_size,
            'exclude_patterns': self.exclude_patterns,
            'include_directories': self.include_directories,
            'filename_prefixes': self.filename_prefixes,
            'filename_suffixes': self.filename_suffixes
        }


class ProgressMonitor:
    """监控和报告传输进度"""

    def __init__(self):
        self.total_files = 0
        self.completed_files = 0
        self.failed_files = 0
        self.skipped_files = 0
        self.total_bytes = 0
        self.transferred_bytes = 0
        self.start_time = None
        self.current_file = None
        self.current_file_bytes = 0
        self.errors = []

        logger.info("初始化进度监控器")

    def start_transfer(self, total_files: int, total_bytes: int):
        """开始传输监控"""
        self.total_files = total_files
        self.total_bytes = total_bytes
        self.start_time = time.time()
        self.completed_files = 0
        self.failed_files = 0
        self.skipped_files = 0
        self.transferred_bytes = 0
        self.errors = []

        logger.info(f"开始传输监控 - 总文件数: {total_files}, 总大小: {self._format_bytes(total_bytes)}")

    def start_file_transfer(self, file_info: FileInfo):
        """开始单个文件传输"""
        self.current_file = file_info
        self.current_file_bytes = 0
        logger.debug(f"开始传输文件: {file_info.name}")

    def update_progress(self, bytes_transferred: int):
        """更新传输进度"""
        self.current_file_bytes += bytes_transferred
        self.transferred_bytes += bytes_transferred

    def file_completed(self, success: bool, error_message: Optional[str] = None):
        """标记文件传输完成"""
        if success:
            self.completed_files += 1
            logger.debug(f"文件传输成功: {self.current_file.name if self.current_file else 'Unknown'}")
        else:
            self.failed_files += 1
            if error_message:
                self.errors.append(error_message)
            logger.warning(f"文件传输失败: {self.current_file.name if self.current_file else 'Unknown'} - {error_message}")

        self.current_file = None
        self.current_file_bytes = 0

    def file_skipped(self, reason: str):
        """标记文件被跳过"""
        self.skipped_files += 1
        logger.debug(f"文件被跳过: {self.current_file.name if self.current_file else 'Unknown'} - {reason}")

    def get_progress_info(self) -> dict:
        """获取当前进度信息"""
        elapsed_time = time.time() - self.start_time if self.start_time else 0

        # 计算传输速度
        transfer_speed = self.transferred_bytes / elapsed_time if elapsed_time > 0 else 0

        # 计算完成百分比
        try:
            total_files = int(self.total_files) if not isinstance(self.total_files, int) else self.total_files
            total_bytes = int(self.total_bytes) if not isinstance(self.total_bytes, int) else self.total_bytes
        except (ValueError, TypeError):
            total_files = 0
            total_bytes = 0
            
        file_progress = (self.completed_files + self.failed_files + self.skipped_files) / total_files * 100 if total_files > 0 else 0
        byte_progress = self.transferred_bytes / total_bytes * 100 if total_bytes > 0 else 0

        # 估算剩余时间
        remaining_bytes = total_bytes - self.transferred_bytes
        estimated_time = remaining_bytes / transfer_speed if transfer_speed > 0 else 0

        return {
            'total_files': self.total_files,
            'completed_files': self.completed_files,
            'failed_files': self.failed_files,
            'skipped_files': self.skipped_files,
            'file_progress_percent': round(file_progress, 2),
            'total_bytes': self.total_bytes,
            'transferred_bytes': self.transferred_bytes,
            'byte_progress_percent': round(byte_progress, 2),
            'transfer_speed_bps': transfer_speed,
            'transfer_speed_formatted': self._format_speed(transfer_speed),
            'elapsed_time': elapsed_time,
            'estimated_remaining_time': estimated_time,
            'current_file': self.current_file.name if self.current_file else None,
            'current_file_progress': self.current_file_bytes
        }

    def get_summary(self) -> TransferSummary:
        """获取传输摘要"""
        total_time = time.time() - self.start_time if self.start_time else 0

        return TransferSummary(
            total_files=self.total_files,
            successful_files=self.completed_files,
            failed_files=self.failed_files,
            skipped_files=self.skipped_files,
            total_bytes=self.total_bytes,
            transferred_bytes=self.transferred_bytes,
            total_time=total_time,
            errors=self.errors.copy()
        )

    def print_progress(self):
        """打印当前进度"""
        info = self.get_progress_info()

        print(f"\r进度: {info['completed_files']}/{info['total_files']} 文件 "
              f"({info['file_progress_percent']:.1f}%) | "
              f"{self._format_bytes(info['transferred_bytes'])}/{self._format_bytes(info['total_bytes'])} "
              f"({info['byte_progress_percent']:.1f}%) | "
              f"速度: {info['transfer_speed_formatted']}", end='', flush=True)

    def _format_bytes(self, bytes_count: int) -> str:
        """格式化字节数显示"""
        try:
            # 确保 bytes_count 是数值类型
            bytes_count = float(bytes_count) if not isinstance(bytes_count, (int, float)) else float(bytes_count)
        except (ValueError, TypeError):
            return "0 B"
            
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"

    def _format_speed(self, bytes_per_second: float) -> str:
        """格式化传输速度显示"""
        return f"{self._format_bytes(bytes_per_second)}/s"

    def _format_time(self, seconds: float) -> str:
        """格式化时间显示"""
        if seconds < 60:
            return f"{seconds:.0f}秒"
        elif seconds < 3600:
            return f"{seconds/60:.0f}分{seconds%60:.0f}秒"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours:.0f}时{minutes:.0f}分"


class ZipProcessingService:
    """处理ZIP文件解压和目录合并"""

    def __init__(self, config: Optional[SyncConfig] = None):
        self.config = config or SyncConfig()
        logger.info("初始化ZIP处理服务")

    async def process_mcu_soc_structure(self,
                                      base_path: Path,
                                      output_path: Path,
                                      keep_original: bool = False,
                                      copy_soc_to_mcu: bool = True) -> ZipProcessingSummary:
        """
        处理MCU和SOC目录结构，解压ZIP文件并合并到同一目录

        Args:
            base_path: 包含MCU和SOC目录的基础路径
            output_path: 输出合并后文件的目录
            keep_original: 是否保留原始ZIP文件
            copy_soc_to_mcu: 是否将SOC文件复制到每个MCU目录中

        Returns:
            ZipProcessingSummary: 处理摘要
        """
        start_time = time.time()

        logger.info(f"开始处理MCU和SOC目录结构: {base_path}")

        # 验证基础路径存在（在创建输出目录之前）
        if not base_path.exists():
            raise ZipProcessingError(f"基础路径不存在: {base_path}")

        mcu_path = base_path / "MCU"
        soc_path = base_path / "SOC"

        # 确保输出目录存在
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"输出目录: {output_path}")

        total_zip_files = 0
        processed_zip_files = 0
        failed_zip_files = 0
        extracted_files = 0
        merged_directories = []
        errors = []

        try:
            # 处理MCU目录
            if mcu_path.exists():
                logger.info(f"处理MCU目录: {mcu_path}")
                mcu_result = await self._process_directory_zips(
                    mcu_path, output_path, "MCU", keep_original
                )
                total_zip_files += mcu_result['total_zips']
                processed_zip_files += mcu_result['processed_zips']
                failed_zip_files += mcu_result['failed_zips']
                extracted_files += mcu_result['extracted_files']
                merged_directories.extend(mcu_result['directories'])
                errors.extend(mcu_result['errors'])
            else:
                logger.warning(f"MCU目录不存在: {mcu_path}")

            # 处理SOC目录
            if soc_path.exists():
                logger.info(f"处理SOC目录: {soc_path}")
                soc_result = await self._process_directory_zips(
                    soc_path, output_path, "SOC", keep_original
                )
                total_zip_files += soc_result['total_zips']
                processed_zip_files += soc_result['processed_zips']
                failed_zip_files += soc_result['failed_zips']
                extracted_files += soc_result['extracted_files']
                merged_directories.extend(soc_result['directories'])
                errors.extend(soc_result['errors'])
            else:
                logger.warning(f"SOC目录不存在: {soc_path}")

            # 如果需要将SOC文件复制到每个MCU目录中
            if copy_soc_to_mcu and mcu_path.exists() and soc_path.exists():
                logger.info("开始将SOC文件复制到每个MCU目录中...")
                soc_copy_result = await self._copy_soc_to_mcu_directories(
                    output_path, merged_directories
                )
                extracted_files += soc_copy_result['copied_files']
                errors.extend(soc_copy_result['errors'])

            # 自动删除原始的MCU和SOC文件夹
            logger.info("清理原始MCU和SOC文件夹...")
            cleanup_result = await self.cleanup_original_folders(base_path)

            if cleanup_result['deleted_folders']:
                logger.info(f"已删除原始文件夹: {cleanup_result['deleted_folders']}")

            if cleanup_result['errors']:
                logger.warning(f"清理过程中的错误: {cleanup_result['errors']}")
                errors.extend(cleanup_result['errors'])

            processing_time = time.time() - start_time

            logger.info(f"ZIP处理完成! 处理了 {processed_zip_files}/{total_zip_files} 个ZIP文件")
            logger.info(f"解压了 {extracted_files} 个文件到 {len(merged_directories)} 个目录")
            logger.info(f"处理时间: {processing_time:.2f} 秒")

            return ZipProcessingSummary(
                total_zip_files=total_zip_files,
                processed_zip_files=processed_zip_files,
                failed_zip_files=failed_zip_files,
                extracted_files=extracted_files,
                merged_directories=merged_directories,
                processing_time=processing_time,
                errors=errors
            )

        except Exception as e:
            error_msg = f"ZIP处理过程中出错: {e}"
            logger.error(error_msg)
            raise ZipProcessingError(error_msg)

    async def cleanup_original_folders(self, base_path: Path) -> dict:
        """删除原始的MCU和SOC文件夹"""
        result = {
            'deleted_folders': [],
            'errors': []
        }

        mcu_path = base_path / "MCU"
        soc_path = base_path / "SOC"

        # 删除MCU文件夹
        if mcu_path.exists():
            try:
                shutil.rmtree(mcu_path)
                result['deleted_folders'].append(str(mcu_path))
                logger.info(f"已删除原始MCU文件夹: {mcu_path}")
            except Exception as e:
                error_msg = f"删除MCU文件夹失败: {e}"
                logger.error(error_msg)
                result['errors'].append(error_msg)

        # 删除SOC文件夹
        if soc_path.exists():
            try:
                shutil.rmtree(soc_path)
                result['deleted_folders'].append(str(soc_path))
                logger.info(f"已删除原始SOC文件夹: {soc_path}")
            except Exception as e:
                error_msg = f"删除SOC文件夹失败: {e}"
                logger.error(error_msg)
                result['errors'].append(error_msg)

        return result

    async def _process_directory_zips(self,
                                    source_dir: Path,
                                    output_dir: Path,
                                    category: str,
                                    keep_original: bool) -> dict:
        """处理目录中的所有ZIP文件"""
        result = {
            'total_zips': 0,
            'processed_zips': 0,
            'failed_zips': 0,
            'extracted_files': 0,
            'directories': [],
            'errors': []
        }

        # 递归查找所有ZIP文件
        zip_files = list(source_dir.rglob("*.zip"))
        result['total_zips'] = len(zip_files)

        logger.info(f"在 {category} 目录中找到 {len(zip_files)} 个ZIP文件")

        for zip_file in zip_files:
            try:
                # 为每个ZIP文件创建一个子目录
                relative_path = zip_file.relative_to(source_dir)

                # 使用新的命名逻辑提取车型信息
                dir_name = self._extract_vehicle_model(zip_file.name, category)
                output_subdir = output_dir / dir_name

                # 如果目录已存在且不为空，添加序号后缀避免覆盖
                counter = 1
                original_subdir = output_subdir
                while output_subdir.exists() and any(output_subdir.iterdir()):
                    output_subdir = original_subdir.parent / f"{original_subdir.name}_{counter}"
                    counter += 1

                output_subdir.mkdir(parents=True, exist_ok=True)

                logger.info(f"解压 {zip_file.name} 到 {output_subdir}")

                # 解压ZIP文件
                extracted_count = await self._extract_zip_file(zip_file, output_subdir)

                result['processed_zips'] += 1
                result['extracted_files'] += extracted_count
                result['directories'].append(str(output_subdir))

                # 删除原始ZIP文件（如果不保留）
                if not keep_original:
                    zip_file.unlink()
                    logger.debug(f"删除原始ZIP文件: {zip_file}")

            except Exception as e:
                error_msg = f"处理ZIP文件失败 {zip_file}: {e}"
                logger.error(error_msg)
                result['failed_zips'] += 1
                result['errors'].append(error_msg)

        return result

    def _extract_vehicle_model(self, zip_filename: str, category: str) -> str:
        """从ZIP文件名中提取车型信息"""
        # 移除扩展名
        name = Path(zip_filename).stem

        if category == "MCU":
            # 对于MCU文件，尝试提取车型
            # 支持多种文件名格式：
            # 1. VBF_ReleasePackage_FX12-A2-M1_MCU_R3.3.7B1 -> FX12-A2-M1
            # 2. VBF_ReleasePackage_FS11-A5_MCU_R3.3.7B10_2025-08-01-22-14-51 -> FS11-A5
            # 3. VBF_ReleasePackage_E245_MCU_R3.3.7B1 -> E245

            # 主要模式：VBF_ReleasePackage_{车型}_MCU
            if "VBF_ReleasePackage_" in name and "_MCU" in name:
                # 提取VBF_ReleasePackage_和_MCU之间的部分
                start_idx = name.find("VBF_ReleasePackage_") + len("VBF_ReleasePackage_")
                end_idx = name.find("_MCU", start_idx)

                if end_idx > start_idx:
                    vehicle_part = name[start_idx:end_idx]

                    # 保留完整的车型名称，包括所有后缀
                    # 特别处理FX12-A2-M1, FX12-A2-M2这样的复杂车型名
                    # 确保完整保留所有标识符，包括M1/M2等后缀
                    logger.info(f"提取车型名称: '{zip_filename}' -> '{vehicle_part}'")
                    return vehicle_part  # 返回完整车型名称

            # 备用模式：如果不是标准格式，尝试其他模式
            # 例如: FX12-A2-M1_MCU_xxx -> FX12-A2-M1
            if "_MCU" in name:
                parts = name.split("_MCU")
                if len(parts) > 0:
                    potential_vehicle = parts[0]
                    # 移除可能的前缀，但保留完整的车型标识
                    if potential_vehicle.startswith("VBF_ReleasePackage_"):
                        potential_vehicle = potential_vehicle[len("VBF_ReleasePackage_"):]
                    elif potential_vehicle.startswith("VBF_"):
                        potential_vehicle = potential_vehicle[4:]

                    logger.info(f"备用提取车型名称: '{zip_filename}' -> '{potential_vehicle}'")
                    return potential_vehicle

            # 如果无法解析，使用原始逻辑
            logger.warning(f"无法解析车型名称，使用原始文件名: {zip_filename}")
            return name

        elif category == "SOC":
            # 对于SOC文件，保持原有逻辑或简化
            # 例如: VBF_P181_SOC_J3.3.7B10_2025-08-02-00-12 -> SOC_P181
            if "VBF_" in name and "_SOC" in name:
                # 提取VBF_和_SOC之间的部分
                start_idx = name.find("VBF_") + len("VBF_")
                end_idx = name.find("_SOC", start_idx)

                if end_idx > start_idx:
                    soc_model = name[start_idx:end_idx]
                    return f"SOC_{soc_model}"

            # 如果无法解析，使用原始逻辑
            return f"SOC_{name}"

        # 默认情况
        return f"{category}_{name}"

    async def _copy_soc_to_mcu_directories(self,
                                         output_path: Path,
                                         all_directories: List[str]) -> dict:
        """将SOC文件复制到每个MCU目录中"""
        result = {
            'copied_files': 0,
            'errors': []
        }

        # 找到所有MCU和SOC目录
        # MCU目录现在不再有MCU_前缀，需要通过排除SOC目录来识别
        soc_directories = [d for d in all_directories if Path(d).name.startswith('SOC_')]
        mcu_directories = [d for d in all_directories if not Path(d).name.startswith('SOC_')]

        if not mcu_directories:
            logger.warning("没有找到MCU目录，跳过SOC文件复制")
            return result

        if not soc_directories:
            logger.warning("没有找到SOC目录，跳过SOC文件复制")
            return result

        logger.info(f"找到 {len(mcu_directories)} 个MCU目录和 {len(soc_directories)} 个SOC目录")

        # 为每个MCU目录复制所有SOC文件
        for mcu_dir_path in mcu_directories:
            mcu_dir = Path(mcu_dir_path)
            logger.info(f"处理MCU目录: {mcu_dir.name}")

            for soc_dir_path in soc_directories:
                soc_dir = Path(soc_dir_path)

                try:
                    # 直接将SOC文件复制到MCU目录中，不创建子文件夹
                    if soc_dir.exists():
                        logger.info(f"复制 {soc_dir.name} 文件到 {mcu_dir.name}")

                        # 直接复制所有SOC文件到MCU目录
                        copied_count = await self._copy_directory_contents(soc_dir, mcu_dir)
                        result['copied_files'] += copied_count

                        logger.debug(f"复制了 {copied_count} 个SOC文件到 {mcu_dir}")

                except Exception as e:
                    error_msg = f"复制SOC文件到MCU目录失败 {mcu_dir.name}: {e}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)

        logger.info(f"SOC文件复制完成，共复制了 {result['copied_files']} 个文件")
        return result

    async def _copy_directory_contents(self, source_dir: Path, target_dir: Path) -> int:
        """复制目录中的所有内容"""
        copied_count = 0

        try:
            for item in source_dir.rglob("*"):
                if item.is_file():
                    # 计算相对路径
                    relative_path = item.relative_to(source_dir)
                    target_file = target_dir / relative_path

                    # 确保目标目录存在
                    target_file.parent.mkdir(parents=True, exist_ok=True)

                    # 复制文件
                    shutil.copy2(item, target_file)
                    copied_count += 1

        except Exception as e:
            logger.error(f"复制目录内容失败: {e}")
            raise

        return copied_count

    async def _extract_zip_file(self, zip_path: Path, extract_to: Path) -> int:
        """解压单个ZIP文件"""
        extracted_count = 0

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # 获取ZIP文件中的所有文件列表
                file_list = zip_ref.namelist()

                for file_name in file_list:
                    try:
                        # 解压单个文件
                        zip_ref.extract(file_name, extract_to)
                        extracted_count += 1

                        # 处理文件权限（如果需要）
                        extracted_file = extract_to / file_name
                        if extracted_file.exists() and not extracted_file.is_dir():
                            # 设置文件为可读写
                            extracted_file.chmod(0o644)

                    except Exception as e:
                        logger.warning(f"解压文件失败 {file_name}: {e}")
                        continue

                logger.debug(f"成功解压 {extracted_count} 个文件从 {zip_path.name}")

        except zipfile.BadZipFile:
            error_msg = f"无效的ZIP文件: {zip_path}"
            logger.error(error_msg)
            raise ZipProcessingError(error_msg)
        except Exception as e:
            error_msg = f"解压ZIP文件时出错 {zip_path}: {e}"
            logger.error(error_msg)
            raise ZipProcessingError(error_msg)

        return extracted_count

    async def extract_all_zips(self,
                             directory: Path,
                             output_directory: Optional[Path] = None,
                             keep_original: bool = False,
                             create_subdirs: bool = True) -> ZipProcessingSummary:
        """
        解压目录中的所有ZIP文件

        Args:
            directory: 包含ZIP文件的目录
            output_directory: 输出目录，如果为None则在原地解压
            keep_original: 是否保留原始ZIP文件
            create_subdirs: 是否为每个ZIP文件创建子目录

        Returns:
            ZipProcessingSummary: 处理摘要
        """
        start_time = time.time()

        if output_directory is None:
            output_directory = directory

        output_directory.mkdir(parents=True, exist_ok=True)

        # 查找所有ZIP文件
        zip_files = list(directory.rglob("*.zip"))

        logger.info(f"在 {directory} 中找到 {len(zip_files)} 个ZIP文件")

        processed_zips = 0
        failed_zips = 0
        extracted_files = 0
        directories = []
        errors = []

        for zip_file in zip_files:
            try:
                if create_subdirs:
                    # 为每个ZIP创建子目录
                    extract_dir = output_directory / zip_file.stem
                    extract_dir.mkdir(parents=True, exist_ok=True)
                else:
                    extract_dir = output_directory

                # 解压文件
                count = await self._extract_zip_file(zip_file, extract_dir)

                processed_zips += 1
                extracted_files += count
                if create_subdirs:
                    directories.append(str(extract_dir))

                # 删除原始文件（如果不保留）
                if not keep_original:
                    zip_file.unlink()

            except Exception as e:
                error_msg = f"处理ZIP文件失败 {zip_file}: {e}"
                logger.error(error_msg)
                failed_zips += 1
                errors.append(error_msg)

        processing_time = time.time() - start_time

        return ZipProcessingSummary(
            total_zip_files=len(zip_files),
            processed_zip_files=processed_zips,
            failed_zip_files=failed_zips,
            extracted_files=extracted_files,
            merged_directories=directories,
            processing_time=processing_time,
            errors=errors
        )


class FileTransferService:
    """处理文件复制和传输"""

    def __init__(self,
                 share_manager: WindowsShareManager,
                 progress_callback: Optional[Callable] = None,
                 config: Optional[SyncConfig] = None):
        self.share_manager = share_manager
        self.progress_callback = progress_callback
        self.config = config or SyncConfig()

        logger.info("初始化文件传输服务")

    async def copy_file(self,
                       remote_path: str,
                       local_path: Path,
                       overwrite: bool = False) -> TransferResult:
        """使用shutil.copy2复制单个文件"""
        start_time = time.time()

        try:
            # 确保本地目录存在
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # 检查文件是否已存在
            if local_path.exists() and not overwrite:
                return TransferResult(
                    file_info=await self._get_file_info_from_path(remote_path),
                    success=False,
                    local_path=local_path,
                    error_message="文件已存在且未设置覆盖"
                )

            # 获取文件信息
            file_info = await self._get_file_info_from_path(remote_path)

            # 如果是目录，创建目录
            if file_info.is_directory:
                local_path.mkdir(parents=True, exist_ok=True)
                return TransferResult(
                    file_info=file_info,
                    success=True,
                    local_path=local_path,
                    bytes_transferred=0,
                    transfer_time=time.time() - start_time
                )

            # 复制文件
            bytes_transferred = await self._copy_file_with_progress(
                remote_path, str(local_path), file_info.size
            )

            transfer_time = time.time() - start_time

            logger.debug(f"文件复制成功: {remote_path} -> {local_path}")

            return TransferResult(
                file_info=file_info,
                success=True,
                local_path=local_path,
                bytes_transferred=bytes_transferred,
                transfer_time=transfer_time
            )

        except Exception as e:
            error_msg = f"复制文件失败 {remote_path}: {e}"
            logger.error(error_msg)

            return TransferResult(
                file_info=await self._get_file_info_from_path(remote_path),
                success=False,
                local_path=local_path,
                error_message=error_msg,
                transfer_time=time.time() - start_time
            )

    async def copy_files(self,
                        file_list: List[FileInfo],
                        local_base_path: Path,
                        overwrite: bool = False,
                        clear_destination: bool = False) -> TransferSummary:
        """批量复制文件"""

        # 如果需要清空目标目录
        if clear_destination and local_base_path.exists():
            logger.info(f"清空目标目录: {local_base_path}")
            try:
                shutil.rmtree(local_base_path)
                local_base_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"清空目录失败: {e}")
                raise TransferError(f"无法清空目标目录: {e}")

        # 确保目标目录存在
        local_base_path.mkdir(parents=True, exist_ok=True)

        results = []
        semaphore = asyncio.Semaphore(self.config.max_concurrent_transfers)

        async def copy_single_file(file_info: FileInfo):
            async with semaphore:
                # 计算相对路径
                relative_path = os.path.relpath(file_info.path, self.share_manager.normalized_path)
                local_file_path = local_base_path / relative_path

                # 重试机制
                for attempt in range(self.config.retry_attempts):
                    try:
                        result = await self.copy_file(
                            file_info.path,
                            local_file_path,
                            overwrite
                        )
                        results.append(result)

                        # 调用进度回调
                        if self.progress_callback:
                            self.progress_callback(result)

                        break

                    except Exception as e:
                        if attempt < self.config.retry_attempts - 1:
                            logger.warning(f"重试复制文件 {file_info.name} (尝试 {attempt + 1}/{self.config.retry_attempts})")
                            await asyncio.sleep(self.config.retry_delay)
                        else:
                            error_result = TransferResult(
                                file_info=file_info,
                                success=False,
                                local_path=local_file_path,
                                error_message=f"重试失败: {e}"
                            )
                            results.append(error_result)

        # 并发复制文件
        tasks = [copy_single_file(file_info) for file_info in file_list if not file_info.is_directory]

        # 先创建目录结构
        for file_info in file_list:
            if file_info.is_directory:
                relative_path = os.path.relpath(file_info.path, self.share_manager.normalized_path)
                local_dir_path = local_base_path / relative_path
                local_dir_path.mkdir(parents=True, exist_ok=True)

        # 执行文件复制任务
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # 生成摘要
        successful = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        total_bytes = sum(r.bytes_transferred for r in results)
        errors = [r.error_message for r in results if r.error_message]

        return TransferSummary(
            total_files=len(file_list),
            successful_files=successful,
            failed_files=failed,
            skipped_files=0,
            total_bytes=sum(int(f.size) if isinstance(f.size, str) else f.size for f in file_list if not f.is_directory),
            transferred_bytes=total_bytes,
            total_time=0,  # 将在调用方计算
            errors=errors
        )

    async def _copy_file_with_progress(self, source: str, destination: str, file_size: int) -> int:
        """带进度的文件复制"""
        bytes_transferred = 0

        try:
            with open(source, 'rb') as src, open(destination, 'wb') as dst:
                while True:
                    chunk = src.read(self.config.chunk_size)
                    if not chunk:
                        break

                    dst.write(chunk)
                    bytes_transferred += len(chunk)

                    # 更新进度
                    if self.progress_callback:
                        # 这里可以添加更细粒度的进度回调
                        pass

            # 复制文件元数据（修改时间等）
            shutil.copystat(source, destination)

        except Exception as e:
            logger.error(f"文件复制过程中出错: {e}")
            raise

        return bytes_transferred

    async def _get_file_info_from_path(self, file_path: str) -> FileInfo:
        """从路径获取文件信息"""
        try:
            stat_info = os.stat(file_path)
            filename = os.path.basename(file_path)

            return FileInfo(
                name=filename,
                path=file_path,
                size=int(stat_info.st_size),  # 确保大小是整数类型
                modified_time=datetime.fromtimestamp(stat_info.st_mtime),
                is_directory=os.path.isdir(file_path)
            )
        except Exception as e:
            logger.error(f"获取文件信息失败: {e}")
            raise FileAccessError(f"无法获取文件信息: {e}")


# 错误处理装饰器
def handle_sync_errors(func):
    """同步操作错误处理装饰器"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except KeyboardInterrupt:
            logger.info("用户中断操作")
            raise
        except (ShareAccessError, AuthenticationError) as e:
            logger.error(f"访问错误: {e}")
            raise
        except FileAccessError as e:
            logger.error(f"文件访问错误: {e}")
            raise
        except TransferError as e:
            logger.error(f"传输错误: {e}")
            raise
        except Exception as e:
            logger.error(f"未知错误: {e}")
            raise WindowsFileSyncError(f"操作失败: {e}")

    return wrapper


class WindowsFileSync:
    """主要的文件同步接口"""

    def __init__(self, share_path: str, config: Optional[SyncConfig] = None):
        self.share_path = share_path
        self.config = config or SyncConfig()

        # 验证配置
        try:
            self.config.validate()
        except ValueError as e:
            raise WindowsFileSyncError(f"配置错误: {e}")

        # 初始化组件
        try:
            self.share_manager = WindowsShareManager(share_path)
            self.discovery_service = FileDiscoveryService(self.share_manager)
            self.progress_monitor = ProgressMonitor()
            self.transfer_service = FileTransferService(
                self.share_manager,
                self._progress_callback,
                self.config
            )
            self.zip_service = ZipProcessingService(self.config)
        except Exception as e:
            raise WindowsFileSyncError(f"初始化失败: {e}")

        # 设置日志级别
        logging.getLogger().setLevel(getattr(logging, self.config.log_level))

        # 内部状态
        self._external_progress_callback = None
        self._show_progress = True

        logger.info(f"初始化Windows文件同步器: {share_path}")

    @handle_sync_errors
    async def sync_files(self,
                        local_path: Union[str, Path],
                        file_filter: Optional[FileFilter] = None,
                        overwrite: bool = False,
                        clear_destination: bool = True,
                        progress_callback: Optional[Callable] = None,
                        show_progress: bool = True) -> TransferSummary:
        """同步所有文件到本地路径"""

        local_path = Path(local_path)
        start_time = time.time()

        # 验证本地路径
        self.validate_local_path(local_path)

        # 验证共享路径
        logger.info("验证共享路径访问权限...")
        await self._retry_operation(self.share_manager.validate_path)
        await self._retry_operation(self.share_manager.test_access)

        # 发现文件
        logger.info("开始发现文件...")
        files = await self._retry_operation(
            self.discovery_service.discover_files,
            file_filter=file_filter
        )

        if not files:
            logger.warning("未发现任何文件")
            return TransferSummary(0, 0, 0, 0, 0, 0, 0, [])

        # 计算总大小
        total_size = sum(int(f.size) if isinstance(f.size, str) else f.size for f in files if not f.is_directory)
        file_count = len([f for f in files if not f.is_directory])

        logger.info(f"发现 {len(files)} 个项目 ({file_count} 个文件, 总大小: {self.progress_monitor._format_bytes(total_size)})")

        # 检查磁盘空间
        if total_size > 0:
            self.check_disk_space(local_path, total_size)

        # 开始进度监控
        self.progress_monitor.start_transfer(file_count, total_size)

        # 设置外部进度回调
        self._external_progress_callback = progress_callback
        self._show_progress = show_progress

        # 复制文件
        logger.info("开始文件传输...")
        summary = await self.transfer_service.copy_files(
            files,
            local_path,
            overwrite,
            clear_destination
        )

        # 更新摘要时间
        summary.total_time = time.time() - start_time

        # 打印最终结果
        if show_progress:
            print()  # 换行

        logger.info(f"同步完成! 成功: {summary.successful_files}, "
                   f"失败: {summary.failed_files}, "
                   f"用时: {self.progress_monitor._format_time(summary.total_time)}")

        if summary.errors:
            logger.warning(f"遇到 {len(summary.errors)} 个错误")
            for error in summary.errors[:5]:  # 只显示前5个错误
                logger.warning(f"  - {error}")
            if len(summary.errors) > 5:
                logger.warning(f"  ... 还有 {len(summary.errors) - 5} 个错误")

        return summary

    async def list_files(self,
                        remote_path: str = "",
                        file_filter: Optional[FileFilter] = None,
                        show_details: bool = False) -> List[FileInfo]:
        """列出共享路径中的文件"""

        # 验证共享路径
        await self._retry_operation(self.share_manager.validate_path)
        await self._retry_operation(self.share_manager.test_access)

        # 发现文件
        files = await self._retry_operation(
            self.discovery_service.discover_files,
            remote_path=remote_path,
            file_filter=file_filter
        )

        if show_details:
            logger.info(f"共享路径 {self.share_path} 中找到 {len(files)} 个项目")

            # 统计信息
            directories = [f for f in files if f.is_directory]
            regular_files = [f for f in files if not f.is_directory]
            total_size = sum(int(f.size) if isinstance(f.size, str) else f.size for f in regular_files)

            logger.info(f"目录: {len(directories)} 个")
            logger.info(f"文件: {len(regular_files)} 个")
            logger.info(f"总大小: {self.progress_monitor._format_bytes(total_size)}")

        return files

    async def _retry_operation(self, operation, *args, **kwargs):
        """重试操作的通用方法"""
        last_exception = None

        for attempt in range(self.config.retry_attempts + 1):
            try:
                return await operation(*args, **kwargs) if asyncio.iscoroutinefunction(operation) else operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.config.retry_attempts:
                    logger.warning(f"操作失败，重试中 (尝试 {attempt + 1}/{self.config.retry_attempts}): {e}")
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    logger.error(f"操作最终失败: {e}")

        raise last_exception

    def validate_local_path(self, local_path: Path) -> bool:
        """验证本地路径"""
        try:
            # 检查父目录是否存在或可创建
            if not local_path.parent.exists():
                local_path.parent.mkdir(parents=True, exist_ok=True)

            # 检查写入权限
            test_file = local_path.parent / '.sync_test'
            try:
                test_file.touch()
                test_file.unlink()
            except PermissionError:
                raise TransferError(f"没有写入权限: {local_path.parent}")

            return True

        except Exception as e:
            raise TransferError(f"本地路径验证失败: {e}")

    def check_disk_space(self, local_path: Path, required_bytes: int) -> bool:
        """检查磁盘空间是否足够"""
        try:
            stat = shutil.disk_usage(local_path.parent)
            available_bytes = stat.free

            if available_bytes < required_bytes:
                required_gb = required_bytes / (1024**3)
                available_gb = available_bytes / (1024**3)
                raise TransferError(
                    f"磁盘空间不足: 需要 {required_gb:.2f} GB, 可用 {available_gb:.2f} GB"
                )

            logger.info(f"磁盘空间检查通过: 需要 {self.progress_monitor._format_bytes(required_bytes)}, "
                       f"可用 {self.progress_monitor._format_bytes(available_bytes)}")
            return True

        except TransferError:
            raise
        except Exception as e:
            logger.warning(f"磁盘空间检查失败: {e}")
            return True  # 如果无法检查，假设空间足够

    def _progress_callback(self, transfer_result: TransferResult):
        """内部进度回调"""
        # 更新进度监控器
        self.progress_monitor.file_completed(
            transfer_result.success,
            transfer_result.error_message
        )

        # 显示进度
        if self._show_progress:
            self.progress_monitor.print_progress()

        # 调用外部回调
        if self._external_progress_callback:
            progress_info = self.progress_monitor.get_progress_info()
            self._external_progress_callback(progress_info, transfer_result)

    async def process_mcu_soc_zips(self,
                                 local_path: Union[str, Path],
                                 output_path: Optional[Union[str, Path]] = None,
                                 keep_original: bool = False,
                                 copy_soc_to_mcu: bool = True) -> ZipProcessingSummary:
        """
        处理下载后的MCU和SOC目录中的ZIP文件

        Args:
            local_path: 包含MCU和SOC目录的本地路径
            output_path: 输出合并后文件的目录，如果为None则使用local_path/extracted
            keep_original: 是否保留原始ZIP文件
            copy_soc_to_mcu: 是否将SOC文件复制到每个MCU目录中

        Returns:
            ZipProcessingSummary: ZIP处理摘要
        """
        local_path = Path(local_path)

        if output_path is None:
            output_path = local_path / "extracted"
        else:
            output_path = Path(output_path)

        logger.info(f"开始处理MCU和SOC ZIP文件: {local_path}")

        # 验证本地路径
        if not local_path.exists():
            raise ZipProcessingError(f"本地路径不存在: {local_path}")

        # 处理MCU和SOC结构
        return await self.zip_service.process_mcu_soc_structure(
            local_path, output_path, keep_original, copy_soc_to_mcu
        )

    async def extract_all_zips(self,
                             directory: Union[str, Path],
                             output_directory: Optional[Union[str, Path]] = None,
                             keep_original: bool = False,
                             create_subdirs: bool = True) -> ZipProcessingSummary:
        """
        解压目录中的所有ZIP文件

        Args:
            directory: 包含ZIP文件的目录
            output_directory: 输出目录，如果为None则在原地解压
            keep_original: 是否保留原始ZIP文件
            create_subdirs: 是否为每个ZIP文件创建子目录

        Returns:
            ZipProcessingSummary: ZIP处理摘要
        """
        directory = Path(directory)

        if output_directory is not None:
            output_directory = Path(output_directory)

        logger.info(f"开始解压目录中的所有ZIP文件: {directory}")

        return await self.zip_service.extract_all_zips(
            directory, output_directory, keep_original, create_subdirs
        )

    async def sync_and_process_zips(self,
                                  local_path: Union[str, Path],
                                  file_filter: Optional[FileFilter] = None,
                                  overwrite: bool = False,
                                  clear_destination: bool = True,
                                  process_zips: bool = True,
                                  keep_original_zips: bool = False,
                                  copy_soc_to_mcu: bool = True,
                                  progress_callback: Optional[Callable] = None,
                                  show_progress: bool = True) -> tuple[TransferSummary, Optional[ZipProcessingSummary]]:
        """
        同步文件并自动处理ZIP文件（一站式解决方案）

        Args:
            local_path: 本地目标路径
            file_filter: 文件过滤器
            overwrite: 是否覆盖已存在的文件
            clear_destination: 是否清空目标目录
            process_zips: 是否自动处理ZIP文件
            keep_original_zips: 是否保留原始ZIP文件
            copy_soc_to_mcu: 是否将SOC文件复制到每个MCU目录中
            progress_callback: 进度回调函数
            show_progress: 是否显示进度

        Returns:
            tuple: (传输摘要, ZIP处理摘要)
        """
        # 首先同步文件
        logger.info("开始文件同步...")
        transfer_summary = await self.sync_files(
            local_path=local_path,
            file_filter=file_filter,
            overwrite=overwrite,
            clear_destination=clear_destination,
            progress_callback=progress_callback,
            show_progress=show_progress
        )

        zip_summary = None

        # 如果需要处理ZIP文件
        if process_zips:
            logger.info("开始处理ZIP文件...")
            try:
                zip_summary = await self.process_mcu_soc_zips(
                    local_path=local_path,
                    keep_original=keep_original_zips,
                    copy_soc_to_mcu=copy_soc_to_mcu
                )

                logger.info(f"ZIP处理完成! 处理了 {zip_summary.processed_zip_files} 个ZIP文件")

            except Exception as e:
                logger.error(f"ZIP处理失败: {e}")
                # 即使ZIP处理失败，也返回文件同步的结果

        return transfer_summary, zip_summary


# 便捷函数
async def sync_windows_share(share_path: str,
                           local_path: Union[str, Path],
                           extensions: Optional[List[str]] = None,
                           max_size: Optional[int] = None,
                           exclude_patterns: Optional[List[str]] = None,
                           filename_prefixes: Optional[List[str]] = None,
                           filename_suffixes: Optional[List[str]] = None,
                           overwrite: bool = False,
                           clear_destination: bool = True,
                           show_progress: bool = True) -> TransferSummary:
    """
    便捷的文件同步函数

    Args:
        share_path: Windows共享路径 (如: r"\\server\share")
        local_path: 本地目标路径
        extensions: 允许的文件扩展名列表 (如: ['.txt', '.pdf'])
        max_size: 最大文件大小限制 (字节)
        exclude_patterns: 排除模式列表 (支持通配符)
        filename_prefixes: 文件名前缀列表 (如: ['report_', 'data_'])
        filename_suffixes: 文件名后缀列表 (如: ['_backup', '_final'])
        overwrite: 是否覆盖已存在的文件
        clear_destination: 是否清空目标目录
        show_progress: 是否显示进度

    Returns:
        TransferSummary: 传输摘要
    """

    # 创建文件过滤器
    file_filter = None
    if extensions or max_size or exclude_patterns or filename_prefixes or filename_suffixes:
        file_filter = FileFilter(
            extensions=extensions,
            max_size=max_size,
            exclude_patterns=exclude_patterns,
            filename_prefixes=filename_prefixes,
            filename_suffixes=filename_suffixes
        )

    # 创建同步器并执行同步
    sync = WindowsFileSync(share_path)
    return await sync.sync_files(
        local_path=local_path,
        file_filter=file_filter,
        overwrite=overwrite,
        clear_destination=clear_destination,
        show_progress=show_progress
    )


async def sync_and_process_mcu_soc(share_path: str,
                                 local_path: Union[str, Path],
                                 extensions: Optional[List[str]] = None,
                                 max_size: Optional[int] = None,
                                 exclude_patterns: Optional[List[str]] = None,
                                 filename_prefixes: Optional[List[str]] = None,
                                 filename_suffixes: Optional[List[str]] = None,
                                 overwrite: bool = False,
                                 clear_destination: bool = True,
                                 keep_original_zips: bool = False,
                                 copy_soc_to_mcu: bool = True,
                                 show_progress: bool = True) -> tuple[TransferSummary, Optional[ZipProcessingSummary]]:
    """
    便捷函数：同步文件并自动处理MCU和SOC目录中的ZIP文件

    Args:
        share_path: Windows共享路径 (如: r"\\server\share")
        local_path: 本地目标路径
        extensions: 允许的文件扩展名列表 (如: ['.zip'])
        max_size: 最大文件大小限制 (字节)
        exclude_patterns: 排除模式列表 (支持通配符)
        filename_prefixes: 文件名前缀列表 (如: ['VBF_'])
        filename_suffixes: 文件名后缀列表 (如: ['_MCU', '_SOC'])
        overwrite: 是否覆盖已存在的文件
        clear_destination: 是否清空目标目录
        keep_original_zips: 是否保留原始ZIP文件
        copy_soc_to_mcu: 是否将SOC文件复制到每个MCU目录中
        show_progress: 是否显示进度

    Returns:
        tuple: (传输摘要, ZIP处理摘要)
    """

    # 创建文件过滤器
    file_filter = None
    if extensions or max_size or exclude_patterns or filename_prefixes or filename_suffixes:
        file_filter = FileFilter(
            extensions=extensions,
            max_size=max_size,
            exclude_patterns=exclude_patterns,
            filename_prefixes=filename_prefixes,
            filename_suffixes=filename_suffixes
        )

    # 创建同步器并执行同步和ZIP处理
    sync = WindowsFileSync(share_path)
    return await sync.sync_and_process_zips(
        local_path=local_path,
        file_filter=file_filter,
        overwrite=overwrite,
        clear_destination=clear_destination,
        process_zips=True,
        keep_original_zips=keep_original_zips,
        copy_soc_to_mcu=copy_soc_to_mcu,
        show_progress=show_progress
    )


async def process_local_mcu_soc_zips(local_path: Union[str, Path],
                                   output_path: Optional[Union[str, Path]] = None,
                                   keep_original: bool = False,
                                   copy_soc_to_mcu: bool = True) -> ZipProcessingSummary:
    """
    便捷函数：处理本地MCU和SOC目录中的ZIP文件

    Args:
        local_path: 包含MCU和SOC目录的本地路径
        output_path: 输出合并后文件的目录，如果为None则使用local_path/extracted
        keep_original: 是否保留原始ZIP文件
        copy_soc_to_mcu: 是否将SOC文件复制到每个MCU目录中

    Returns:
        ZipProcessingSummary: ZIP处理摘要
    """

    # 创建ZIP处理服务
    zip_service = ZipProcessingService()

    local_path = Path(local_path)
    if output_path is None:
        output_path = local_path / "extracted"
    else:
        output_path = Path(output_path)

    return await zip_service.process_mcu_soc_structure(
        local_path, output_path, keep_original, copy_soc_to_mcu
    )

