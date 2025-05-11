#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
批量文件复制工具
支持从EDL或TXT文件中读取片段列表，并将对应的文件/目录复制到目标位置
支持多个源路径
支持选择是否校验和是否保留目录结构
支持RED相机特殊文件结构（.RDC文件夹）的处理
"""

import os
import re
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set, Optional, Union
import subprocess
from enum import Enum

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('batch_copy.log'),
        logging.StreamHandler()
    ]
)

class FileType(Enum):
    """文件类型枚举"""
    EDL = "edl"
    TXT = "txt"

class CopyMode(Enum):
    """复制模式枚举"""
    FLAT = "flat"  # 只复制文件，不保留目录结构
    STRUCTURE = "structure"  # 保留目录结构

@dataclass
class CopyConfig:
    """复制配置类"""
    source_paths: List[Path]  # 源路径列表
    target_path: Path
    clip_list_path: Path
    copy_mode: CopyMode = CopyMode.STRUCTURE  # 复制模式
    checksum: bool = True  # 是否进行校验和检查
    include_extensions: Optional[List[str]] = None  # 包含的文件扩展名
    exclude_extensions: Optional[List[str]] = None  # 排除的文件扩展名
    remove_extension_from_clip_list: bool = True  # 是否从片段列表中移除扩展名
    handle_red_folders: bool = True  # 是否处理RED相机的.RDC文件夹

class BatchCopy:
    """批量复制主类"""
    
    def __init__(self, config: CopyConfig):
        self.config = config
        self.clip_list: Set[str] = set()
        self.copy_commands: List[str] = []
        self._validate_paths()
        
    def _validate_paths(self) -> None:
        """验证路径的有效性"""
        # 验证所有源路径
        for source_path in self.config.source_paths:
            if not source_path.is_dir():
                raise ValueError(f"源路径不存在或不是目录: {source_path}")
        
        if not self.config.target_path.is_dir():
            raise ValueError(f"目标路径不存在或不是目录: {self.config.target_path}")
        if not self.config.clip_list_path.is_file():
            raise ValueError(f"片段列表文件不存在: {self.config.clip_list_path}")

    def _read_clip_list(self) -> None:
        """读取片段列表"""
        try:
            file_type = FileType(self.config.clip_list_path.suffix[1:].lower())
            
            if file_type == FileType.EDL:
                self._read_edl()
            else:
                # 直接读取 TXT 文件内容
                with open(self.config.clip_list_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self._process_txt_content(content)
        except UnicodeDecodeError:
            # 尝试使用不同的编码方式读取文件
            try:
                with open(self.config.clip_list_path, 'r', encoding='latin1') as f:
                    content = f.read()
                # 将内容转换为 UTF-8
                content = content.encode('latin1').decode('utf-8', errors='replace')
                # 根据文件类型处理内容
                if file_type == FileType.EDL:
                    if "FROM CLIP NAME:" in content:
                        self._process_edl_type1_content(content)
                    else:
                        self._process_edl_type2_content(content)
                else:
                    self._process_txt_content(content)
            except Exception as e:
                raise ValueError(f"无法读取文件：{str(e)}")

    def _read_edl(self) -> None:
        """读取EDL文件"""
        with open(self.config.clip_list_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 检查EDL类型
        if "FROM CLIP NAME:" in content:
            self._process_edl_type1_content(content)
        else:
            self._process_edl_type2_content(content)

    def _process_edl_type1_content(self, content: str) -> None:
        """处理类型1的EDL文件内容"""
        for line in content.splitlines():
            if "FROM CLIP NAME:" in line:
                clip_name = line.split("FROM CLIP NAME:")[1].strip()
                if self.config.remove_extension_from_clip_list:
                    clip_name = Path(clip_name).stem
                self.clip_list.add(clip_name)

    def _process_edl_type2_content(self, content: str) -> None:
        """处理类型2的EDL文件内容"""
        tc_pattern = r'^(\d{2,})(:|\.|;)(\d{2})(:|\.|;)(\d{2})(:|\.|;)(\d{2})$'
        
        for line in content.splitlines():
            elements = re.split(r"\s+", line.strip())
            if elements and elements[0].isdigit():
                for element in elements:
                    if re.match(tc_pattern, element.strip()):
                        clip_name = elements[1].strip()
                        if self.config.remove_extension_from_clip_list:
                            clip_name = Path(clip_name).stem
                        self.clip_list.add(clip_name)
                        break

    def _process_txt_content(self, content: str) -> None:
        """处理TXT文件内容"""
        for line in content.splitlines():
            clip_name = line.strip()
            if self.config.remove_extension_from_clip_list:
                clip_name = Path(clip_name).stem
            if clip_name:
                self.clip_list.add(clip_name)

    def _should_copy_file(self, file_path: Path) -> bool:
        """判断是否应该复制文件"""
        if not self.config.include_extensions and not self.config.exclude_extensions:
            return True
            
        ext = file_path.suffix.lower()[1:]  # 去掉点号
        
        if self.config.include_extensions:
            return ext in self.config.include_extensions
        if self.config.exclude_extensions:
            return ext not in self.config.exclude_extensions
            
        return True

    def _generate_copy_command(self, source: Path, target: Path) -> str:
        """生成复制命令"""
        try:
            rsync_args = ["rsync", "-avh"]
            
            # 添加校验和选项
            if self.config.checksum:
                rsync_args.append("--checksum")
                
            # 确保路径使用正确的编码
            source_str = str(source).encode('utf-8', errors='replace').decode('utf-8')
            target_str = str(target).encode('utf-8', errors='replace').decode('utf-8')
            rsync_args.extend([source_str, target_str])
            
            return " ".join(rsync_args)
        except Exception as e:
            logging.error(f"生成复制命令时出错：{str(e)}")
            raise

    def _get_target_path(self, source_path: Path, current_path: Path) -> Path:
        """根据复制模式获取目标路径"""
        if self.config.copy_mode == CopyMode.FLAT:
            return self.config.target_path / current_path.name
        else:
            # 计算相对于源路径的路径
            rel_path = current_path.relative_to(source_path)
            # 确保目标路径不包含源路径本身
            if rel_path == Path('.'):
                return self.config.target_path
            target_path = self.config.target_path / rel_path
            # 创建目标目录
            target_path.parent.mkdir(parents=True, exist_ok=True)
            return target_path

    def _is_red_folder(self, dir_name: str) -> bool:
        """判断是否是RED相机的文件夹"""
        return dir_name.endswith('.RDC')

    def _find_and_copy(self) -> None:
        """查找并复制文件"""
        for clip_name in self.clip_list:
            logging.info(f"正在查找片段: {clip_name}")
            
            # 在每个源路径中查找
            for source_path in self.config.source_paths:
                logging.info(f"在源路径中查找: {source_path}")
                
                # 查找匹配的文件和目录
                for root, dirs, files in os.walk(source_path):
                    root_path = Path(root)
                    
                    # 检查目录
                    for dir_name in dirs:
                        # 处理RED相机的特殊文件夹
                        if self._is_red_folder(dir_name):
                            base_name = dir_name[:-4]  # 移除.RDC后缀
                            if base_name == clip_name:
                                if self.config.handle_red_folders:
                                    # 如果启用了RED文件夹处理，按特殊方式处理
                                    dir_path = root_path / dir_name
                                    rel_path = root_path.relative_to(source_path)
                                    target_path = self.config.target_path / rel_path / dir_name
                                    target_path.parent.mkdir(parents=True, exist_ok=True)
                                    cmd = self._generate_copy_command(dir_path, target_path)
                                    self.copy_commands.append(cmd)
                                    logging.info(f"找到并处理RED相机文件夹: {dir_path}")
                                else:
                                    # 如果未启用RED文件夹处理，当作普通目录处理
                                    if clip_name in dir_name.split('.'):
                                        dir_path = root_path / dir_name
                                        target_path = self._get_target_path(source_path, dir_path)
                                        cmd = self._generate_copy_command(dir_path, target_path)
                                        self.copy_commands.append(cmd)
                                        logging.info(f"找到目录(未启用RED处理): {dir_path}")
                                continue
                        
                        # 常规目录处理
                        if clip_name in dir_name.split('.'):
                            dir_path = root_path / dir_name
                            target_path = self._get_target_path(source_path, dir_path)
                            cmd = self._generate_copy_command(dir_path, target_path)
                            self.copy_commands.append(cmd)
                            logging.info(f"找到目录: {dir_path}")
                    
                    # 检查文件
                    for file_name in files:
                        if clip_name in file_name.split('.'):
                            file_path = root_path / file_name
                            if self._should_copy_file(file_path):
                                target_path = self._get_target_path(source_path, file_path)
                                cmd = self._generate_copy_command(file_path, target_path)
                                self.copy_commands.append(cmd)
                                logging.info(f"找到文件: {file_path}")

    def execute(self) -> None:
        """执行复制操作"""
        try:
            self._read_clip_list()
            self._find_and_copy()
            
            # 执行复制命令
            for cmd in self.copy_commands:
                logging.info(f"执行命令: {cmd}")
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode != 0:
                    logging.error(f"命令执行失败: {cmd}")
                    logging.error(f"错误信息: {result.stderr}")
                else:
                    logging.info(f"命令执行成功: {cmd}")
                    
        except Exception as e:
            logging.error(f"执行过程中发生错误: {str(e)}")
            raise

def main():
    """主函数"""
    # 示例配置
    config = CopyConfig(
        source_paths=[
            Path("/path/to/source1"),
            Path("/path/to/source2"),
            Path("/path/to/source3")
        ],
        target_path=Path("/path/to/target"),
        clip_list_path=Path("/path/to/clip_list.edl"),
        copy_mode=CopyMode.STRUCTURE,  # 或 CopyMode.FLAT
        checksum=True,
        include_extensions=["mov", "mp4"],
        remove_extension_from_clip_list=True,
        handle_red_folders=True  # 启用RED相机文件夹处理
    )
    
    try:
        batch_copy = BatchCopy(config)
        batch_copy.execute()
    except Exception as e:
        logging.error(f"程序执行失败: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 