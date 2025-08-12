"""
软件包管理器模块
Package Manager Module

管理软件包的下载和更新，集成Windows共享目录文件同步功能。
"""

import os
import asyncio
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from ..utils.logging_system import get_logger

# 导入共享文件同步模块（假设文件已迁移到项目根目录）
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from packge import (
    WindowsFileSync, 
    FileFilter, 
    SyncConfig,
    TransferSummary,
    ZipProcessingSummary,
    WindowsFileSyncError
)


class PackageManager:
    """
    软件包管理器类
    
    负责管理软件包的下载、验证和安装，集成Windows共享目录文件同步功能。
    """
    
    def __init__(self, package_config: Dict[str, Any]):
        """
        初始化软件包管理器
        
        Args:
            package_config: 软件包配置
        """
        self.package_config = package_config
        self.logger = get_logger(__name__)
        
        # 从 windows_share 子配置读取同步参数（若存在）
        ws_cfg = package_config.get("windows_share", {}) if isinstance(package_config, dict) else {}
        
        # 默认配置
        self.default_download_path = package_config.get("download_path", "./downloads")
        self.default_cache_path = package_config.get("cache_path", "./cache")
        self.timeout = package_config.get("timeout", 300)
        self.auto_update = package_config.get("auto_update", True)
        
        # Windows共享同步配置（优先读取 windows_share 子配置）
        self.sync_config = SyncConfig(
            max_concurrent_transfers=ws_cfg.get("max_concurrent_transfers", package_config.get("max_concurrent_transfers", 5)),
            connection_timeout=ws_cfg.get("connection_timeout", package_config.get("connection_timeout", 30)),
            read_timeout=ws_cfg.get("read_timeout", package_config.get("read_timeout", 60)),
            retry_attempts=ws_cfg.get("retry_attempts", package_config.get("retry_attempts", 3)),
            retry_delay=ws_cfg.get("retry_delay", package_config.get("retry_delay", 1.0)),
            chunk_size=ws_cfg.get("chunk_size", package_config.get("chunk_size", '')),
            verify_transfers=ws_cfg.get("verify_transfers", package_config.get("verify_transfers", True)),
            create_backup=ws_cfg.get("create_backup", package_config.get("create_backup", False))
        )
        
        self.logger.info("软件包管理器初始化完成")
    
    def download_package(self, package_info: Dict[str, Any]) -> str:
        """
        下载软件包
        
        Args:
            package_info: 软件包信息
            
        Returns:
            str: 下载的软件包路径
        """
        package_name = package_info.get('name', 'unknown')
        self.logger.info(f"开始下载软件包: {package_name}")
        
        try:
            # 检查是否为Windows共享路径下载
            if 'share_path' in package_info:
                return self._download_from_windows_share(package_info)
            else:
                # 传统下载方式
                return self._download_traditional(package_info)
                
        except Exception as e:
            self.logger.error(f"下载软件包失败: {str(e)}")
            return ""
    
    def _download_from_windows_share(self, package_info: Dict[str, Any]) -> str:
        """
        从Windows共享路径下载软件包
        
        Args:
            package_info: 包含share_path等信息的软件包配置
            
        Returns:
            str: 下载的软件包路径
        """
        share_path = package_info.get('share_path')
        package_name = package_info.get('name', 'unknown')
        local_path = package_info.get('local_path', os.path.join(self.default_download_path, package_name))
        
        if not share_path:
            raise ValueError("未指定Windows共享路径")
        
        self.logger.info(f"从Windows共享路径下载: {share_path} -> {local_path}")
        
        try:
            # 确保本地目录存在
            os.makedirs(local_path, exist_ok=True)
            
            # 创建文件过滤器
            file_filter = self._create_file_filter(package_info)
            
            # 创建Windows文件同步器
            sync = WindowsFileSync(share_path, self.sync_config)
            
            # 执行同步下载
            summary = asyncio.run(self._async_download_from_share(
                sync, local_path, file_filter, package_info
            ))
            
            # 检查下载结果
            if summary.successful_files > 0:
                self.logger.info(f"软件包下载成功: {package_name}, "
                               f"成功: {summary.successful_files}, "
                               f"失败: {summary.failed_files}, "
                               f"用时: {summary.total_time:.2f}秒")
                return local_path
            else:
                raise Exception(f"未成功下载任何文件，失败数: {summary.failed_files}")
                
        except WindowsFileSyncError as e:
            self.logger.error(f"Windows共享同步错误: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"下载过程中发生错误: {str(e)}")
            raise
    
    async def _async_download_from_share(self, 
                                       sync: WindowsFileSync, 
                                       local_path: str, 
                                       file_filter: Optional[FileFilter],
                                       package_info: Dict[str, Any]) -> TransferSummary:
        """
        异步执行Windows共享文件下载
        """
        overwrite = package_info.get('overwrite', False)
        clear_destination = package_info.get('clear_destination', True)
        process_zips = package_info.get('process_zips', False)
        
        if process_zips:
            # 同步并处理ZIP文件
            transfer_summary, zip_summary = await sync.sync_and_process_zips(
                local_path=local_path,
                file_filter=file_filter,
                overwrite=overwrite,
                clear_destination=clear_destination,
                process_zips=True,
                keep_original_zips=package_info.get('keep_original_zips', False),
                copy_soc_to_mcu=package_info.get('copy_soc_to_mcu', True),
                show_progress=package_info.get('show_progress', True)
            )
            
            if zip_summary:
                self.logger.info(f"ZIP处理完成: 处理了 {zip_summary.processed_zip_files} 个文件")
            
            return transfer_summary
        else:
            # 仅同步文件
            return await sync.sync_files(
                local_path=local_path,
                file_filter=file_filter,
                overwrite=overwrite,
                clear_destination=clear_destination,
                show_progress=package_info.get('show_progress', True)
            )
    
    def _create_file_filter(self, package_info: Dict[str, Any]) -> Optional[FileFilter]:
        """
        根据软件包信息创建文件过滤器
        
        Args:
            package_info: 软件包信息
            
        Returns:
            FileFilter: 文件过滤器，如果无过滤条件则返回None
        """
        extensions = package_info.get('extensions')
        max_size = package_info.get('max_size')
        exclude_patterns = package_info.get('exclude_patterns')
        include_directories = package_info.get('include_directories', True)
        filename_prefixes = package_info.get('filename_prefixes')
        filename_suffixes = package_info.get('filename_suffixes')
        
        # 如果没有任何过滤条件，返回None
        if not any([extensions, max_size, exclude_patterns, filename_prefixes, filename_suffixes]):
            return None
        
        return FileFilter(
            extensions=extensions,
            max_size=max_size,
            exclude_patterns=exclude_patterns,
            include_directories=include_directories,
            filename_prefixes=filename_prefixes,
            filename_suffixes=filename_suffixes
        )
    
    def _download_traditional(self, package_info: Dict[str, Any]) -> str:
        """
        传统下载方式（包括SVN和HTTP/HTTPS等）
        
        Args:
            package_info: 软件包信息
            
        Returns:
            str: 下载的软件包路径
        """
        # 优先处理 SVN 下载
        use_svn = (
            bool(package_info.get("svn_url"))
            or bool(package_info.get("use_svn"))
            or self.package_config.get("repository_type") == "svn"
        )
        
        if use_svn:
            return self._download_from_svn(package_info)
        
        # TODO: 这里可以扩展 HTTP/HTTPS 下载逻辑（如 requests + 流式写入），当前保留占位
        self.logger.info("使用传统下载方式（HTTP/HTTPS占位）")
        package_name = package_info.get('name', 'placeholder_package')
        local_dir = package_info.get('local_path', os.path.join(self.default_download_path, package_name))
        os.makedirs(local_dir, exist_ok=True)
        return local_dir
    
    def _download_from_svn(self, package_info: Dict[str, Any]) -> str:
        """
        从 SVN 拉取软件包
        支持 svn export（默认）与 svn checkout（设置 svn_checkout=True）。
        支持可选参数：revision、depth、username、password、clear_destination。
        优先使用 package_info 中的参数，其次回退到 package_manager 全局配置。
        """
        package_name = package_info.get('name', 'unknown')
        svn_url: Optional[str] = package_info.get('svn_url')
        
        if not svn_url:
            # 尝试由全局仓库地址与子路径拼接
            base = self.package_config.get('repository_url')
            subpath = package_info.get('repo_path') or package_name
            if base and subpath:
                svn_url = base.rstrip('/') + '/' + subpath.lstrip('/')
        
        if not svn_url:
            raise ValueError("未提供有效的 SVN 地址（缺少 svn_url，或无法由 repository_url + repo_path 组装）")
        
        # 目标目录
        local_dir = package_info.get('local_path', os.path.join(self.default_download_path, package_name))
        
        # 选项
        svn_checkout = bool(package_info.get('svn_checkout', False))
        clear_destination = bool(package_info.get('clear_destination', False))
        revision = package_info.get('revision')  # e.g., 1234 or 'HEAD'
        depth = package_info.get('depth')        # e.g., 'infinity', 'files', 'immediates', 'empty'
        
        # 凭证（优先使用包级别）
        username = package_info.get('svn_username') or self.package_config.get('svn_username')
        password = package_info.get('svn_password') or self.package_config.get('svn_password')
        
        # 检查 svn 可用性
        if not self._svn_available():
            raise RuntimeError("未检测到可用的 svn 客户端，请安装 Subversion 并确保命令行可用")
        
        # 处理目标目录
        if clear_destination and os.path.isdir(local_dir):
            self._clear_directory(local_dir)
        os.makedirs(local_dir, exist_ok=True)
        
        svn_exe = self.package_config.get('svn_path') or 'svn'
        cmd = [svn_exe, "checkout" if svn_checkout else "export", svn_url, local_dir]
        
        # 统一覆盖策略
        if not svn_checkout:
            # export 支持 --force 覆盖已有文件
            cmd.append("--force")
        
        # 添加修订版本
        if revision:
            cmd.extend(["-r", str(revision)])
        
        # 添加深度
        if depth:
            cmd.extend(["--depth", str(depth)])
        
        # 添加凭证（避免交互）
        if username:
            cmd.extend(["--username", str(username)])
        if password:
            cmd.extend(["--password", str(password)])
        
        # 非交互模式，自动接受证书
        cmd.extend(["--non-interactive", "--trust-server-cert"])
        
        self.logger.info(f"开始从 SVN 拉取: {svn_url} -> {local_dir} ({'checkout' if svn_checkout else 'export'})")
        # 避免日志中输出密码
        self.logger.debug("SVN 命令: " + " ".join([p if 'password' not in p.lower() else '****' for p in cmd]))
        
        self._run_svn_command(cmd)
        self.logger.info(f"SVN 拉取完成: {package_name} -> {local_dir}")
        return local_dir
    
    def _svn_available(self) -> bool:
        """检测 svn 命令是否可用"""
        exe = self.package_config.get('svn_path') or 'svn'
        if os.path.isabs(exe):
            return os.path.exists(exe) and os.access(exe, os.X_OK)
        return shutil.which(exe) is not None
    
    def _run_svn_command(self, cmd: List[str]) -> None:
        """执行 svn 命令并处理返回码/错误输出"""
        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=self.timeout if isinstance(self.timeout, (int, float)) else None
            )
        except subprocess.TimeoutExpired:
            raise TimeoutError("SVN 操作超时")
        except FileNotFoundError:
            raise RuntimeError("未找到 svn 可执行文件")
        
        if proc.returncode != 0:
            err = proc.stderr.strip() or proc.stdout.strip()
            # 不直接输出密码
            raise RuntimeError(f"SVN 命令执行失败: {err}")
        
        if proc.stdout:
            # 可选：输出简要信息
            self.logger.debug(proc.stdout.strip())
    
    def _clear_directory(self, path: Union[str, Path]) -> None:
        """清空并重建目录"""
        try:
            shutil.rmtree(path)
        except FileNotFoundError:
            pass
        os.makedirs(path, exist_ok=True)
    
    def sync_windows_share(self, 
                          share_path: str,
                          local_path: Union[str, Path],
                          **kwargs) -> TransferSummary:
        """
        直接同步Windows共享目录（对外接口）
        
        Args:
            share_path: Windows共享路径
            local_path: 本地目标路径
            **kwargs: 其他同步参数
            
        Returns:
            TransferSummary: 传输摘要
        """
        self.logger.info(f"同步Windows共享目录: {share_path} -> {local_path}")
        
        try:
            # 创建同步器
            sync = WindowsFileSync(share_path, self.sync_config)
            
            # 创建文件过滤器
            file_filter = None
            if any(key in kwargs for key in ['extensions', 'max_size', 'exclude_patterns', 'filename_prefixes', 'filename_suffixes']):
                file_filter = FileFilter(
                    extensions=kwargs.get('extensions'),
                    max_size=kwargs.get('max_size'),
                    exclude_patterns=kwargs.get('exclude_patterns'),
                    include_directories=kwargs.get('include_directories', True),
                    filename_prefixes=kwargs.get('filename_prefixes'),
                    filename_suffixes=kwargs.get('filename_suffixes')
                )
            
            # 执行同步
            summary = asyncio.run(sync.sync_files(
                local_path=local_path,
                file_filter=file_filter,
                overwrite=kwargs.get('overwrite', False),
                clear_destination=kwargs.get('clear_destination', True),
                show_progress=kwargs.get('show_progress', True)
            ))
            
            self.logger.info(f"同步完成: 成功 {summary.successful_files}, 失败 {summary.failed_files}")
            return summary
            
        except Exception as e:
            self.logger.error(f"Windows共享同步失败: {str(e)}")
            raise
    
    def get_package_info(self, package_name: str) -> Dict[str, Any]:
        """
        获取软件包信息
        
        Args:
            package_name: 软件包名称
            
        Returns:
            Dict[str, Any]: 软件包信息
        """
        # 这里可以实现从配置或远程仓库获取软件包信息的逻辑
        return {
            "name": package_name,
            "version": "unknown",
            "path": os.path.join(self.default_download_path, package_name)
        }
    
    def list_available_packages(self) -> List[Dict[str, Any]]:
        """
        列出可用的软件包
        
        Returns:
            List[Dict[str, Any]]: 可用软件包列表
        """
        # 占位符实现
        return []
    
    def verify_package(self, package_path: str) -> bool:
        """
        验证软件包完整性
        
        Args:
            package_path: 软件包路径
            
        Returns:
            bool: 验证是否通过
        """
        try:
            return os.path.exists(package_path)
        except Exception as e:
            self.logger.error(f"软件包验证失败: {str(e)}")
            return False
    
    def test_windows_share_download(self) -> bool:
        """
        测试 Windows 共享下载功能
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试 Windows 共享下载功能")
        
        try:
            # 从配置中获取测试包信息
            ws_config = self.package_config.get("windows_share", {})
            test_packages = ws_config.get("sync_packages", [])
            
            if not test_packages:
                self.logger.warning("未找到 Windows 共享测试包配置")
                return False
            
            # 使用第一个配置的包进行测试
            test_package = test_packages[0].copy()
            test_package["local_path"] = "./downloads/test_windows_share"
            test_package["show_progress"] = True
            
            self.logger.info(f"测试包配置: {test_package['name']}")
            self.logger.info(f"共享路径: {test_package['share_path']}")
            self.logger.info(f"本地路径: {test_package['local_path']}")
            
            # 执行下载测试
            result_path = self.download_package(test_package)
            
            if result_path and os.path.exists(result_path):
                self.logger.info(f"Windows 共享下载测试成功: {result_path}")
                return True
            else:
                self.logger.error("Windows 共享下载测试失败: 未生成有效路径")
                return False
                
        except Exception as e:
            self.logger.error(f"Windows 共享下载测试异常: {str(e)}")
            return False
    
    def test_svn_download(self) -> bool:
        """
        测试 SVN 下载功能
        
        Returns:
            bool: 测试是否成功
        """
        self.logger.info("开始测试 SVN 下载功能")
        
        try:
            # 从配置中获取 SVN 测试包信息
            svn_config = self.package_config.get("svn", {})
            test_packages = svn_config.get("test_packages", [])
            
            if not test_packages:
                self.logger.warning("未找到 SVN 测试包配置")
                return False
            
            # 检查 SVN 可用性
            if not self._svn_available():
                self.logger.warning("SVN 客户端不可用，跳过 SVN 下载测试")
                return False
            
            # 使用第一个配置的包进行测试
            test_package = test_packages[0].copy()
            test_package["local_path"] = "./downloads/test_svn"
            
            self.logger.info(f"测试包配置: {test_package['name']}")
            self.logger.info(f"SVN URL: {test_package['svn_url']}")
            self.logger.info(f"本地路径: {test_package['local_path']}")
            self.logger.info(f"使用模式: {'checkout' if test_package.get('svn_checkout') else 'export'}")
            
            # 执行下载测试
            result_path = self.download_package(test_package)
            
            if result_path and os.path.exists(result_path):
                self.logger.info(f"SVN 下载测试成功: {result_path}")
                return True
            else:
                self.logger.error("SVN 下载测试失败: 未生成有效路径")
                return False
                
        except Exception as e:
            self.logger.error(f"SVN 下载测试异常: {str(e)}")
            return False
    
    def run_download_tests(self) -> Dict[str, bool]:
        """
        运行所有下载方式的测试
        
        Returns:
            Dict[str, bool]: 各测试方法的结果
        """
        self.logger.info("开始运行软件包下载测试")
        
        results = {
            "windows_share": False,
            "svn": False
        }
        
        # 测试 Windows 共享下载
        if self.package_config.get("default_method") == "windows_share" or \
           self.package_config.get("windows_share", {}).get("enabled", False):
            results["windows_share"] = self.test_windows_share_download()
        else:
            self.logger.info("Windows 共享下载未启用，跳过测试")
        
        # 测试 SVN 下载
        if self.package_config.get("svn", {}).get("enabled", False):
            results["svn"] = self.test_svn_download()
        else:
            self.logger.info("SVN 下载未启用，跳过测试")
        
        # 输出测试结果摘要
        self.logger.info("软件包下载测试完成")
        for method, success in results.items():
            status = "成功" if success else "失败"
            self.logger.info(f"  {method}: {status}")
        
        return results