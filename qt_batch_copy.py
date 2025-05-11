#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import yaml
import logging
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QCheckBox, QComboBox,
    QTextEdit, QFileDialog, QMessageBox, QGroupBox, QScrollArea, QFrame,
    QMenuBar, QMenu, QAction, QStatusBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from batch_copy import BatchCopy, CopyConfig, CopyMode
import locale

class CopyWorker(QThread):
    """复制工作线程"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    error = pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.is_running = True

    def run(self):
        try:
            # 重定向日志到GUI
            class LogHandler(logging.Handler):
                def __init__(self, signal):
                    super().__init__()
                    self.signal = signal

                def emit(self, record):
                    try:
                        msg = self.format(record)
                        self.signal.emit(msg)
                    except UnicodeDecodeError:
                        # 如果遇到编码错误，尝试使用不同的编码方式
                        try:
                            msg = self.format(record).encode('latin1').decode('utf-8', errors='replace')
                            self.signal.emit(msg)
                        except:
                            self.signal.emit("无法显示的消息（编码错误）")

            # 设置日志处理器
            handler = LogHandler(self.progress)
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logging.getLogger().addHandler(handler)

            # 执行复制
            batch_copy = BatchCopy(self.config)
            batch_copy.execute()
            self.finished.emit(True, "复制完成")
        except UnicodeDecodeError as e:
            error_msg = f"编码错误：{str(e)}。请确保所有文件路径使用 UTF-8 编码。"
            self.error.emit(error_msg)
            self.finished.emit(False, error_msg)
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(False, str(e))
        finally:
            logging.getLogger().removeHandler(handler)

    def stop(self):
        self.is_running = False

class BatchCopyGUI(QMainWindow):
    """批量复制GUI主窗口"""
    
    def __init__(self):
        super().__init__()
        self.current_language = self.get_system_language()
        self.load_config()
        self.source_paths = []
        self.init_ui()
        self.copy_worker = None

    def get_system_language(self):
        """获取系统语言"""
        try:
            # 使用新的推荐API
            system_lang = locale.getlocale()[0]
            if not system_lang:
                system_lang = locale.getdefaultlocale()[0]
        except:
            # 如果新API失败，回退到旧API
            system_lang = locale.getdefaultlocale()[0]
            
        if system_lang.startswith('zh'):
            if 'TW' in system_lang or 'HK' in system_lang:
                return 'zh_tw'
            return 'zh_cn'
        return 'en'

    def load_config(self):
        """加载配置文件"""
        with open('config.yaml', 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

    def get_text(self, key_path):
        """获取当前语言的文本"""
        keys = key_path.split('.')
        value = self.config
        for key in keys:
            value = value[key]
        if isinstance(value, dict) and self.current_language in value:
            return value[self.current_language]
        return value

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(self.get_text('ui.window.title'))
        self.setGeometry(100, 100, 
                        self.config['ui']['window']['width'],
                        self.config['ui']['window']['height'])

        # 创建菜单栏
        self.create_menu_bar()

        # 创建状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage(self.get_text('ui.status.ready'))

        # 创建主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 源目录选择区域
        source_layout = QVBoxLayout()
        source_header = QHBoxLayout()
        self.source_label = QLabel(self.get_text('ui.layout.source_path.label'))
        self.source_paths_label = QLabel("")
        self.add_source_btn = QPushButton(self.get_text('ui.layout.add_source.button'))
        self.add_source_btn.setStyleSheet(self.config['ui']['style']['button']['normal'])
        self.add_source_btn.clicked.connect(self.add_source_path)
        source_header.addWidget(self.source_label)
        source_header.addWidget(self.source_paths_label)
        source_header.addWidget(self.add_source_btn)
        source_header.addStretch()
        source_layout.addLayout(source_header)

        # 源目录错误提示
        self.source_error = QLabel("")
        self.source_error.setStyleSheet(self.config['ui']['style']['error_label'])
        self.source_error.hide()
        source_layout.addWidget(self.source_error)

        layout.addLayout(source_layout)

        # 目标目录选择区域
        target_layout = QVBoxLayout()
        target_header = QHBoxLayout()
        self.target_label = QLabel(self.get_text('ui.layout.target_path.label'))
        self.target_path = QLineEdit()
        self.target_path.setReadOnly(True)
        self.select_target_btn = QPushButton(self.get_text('ui.layout.target_path.button'))
        self.select_target_btn.setStyleSheet(self.config['ui']['style']['button']['normal'])
        self.select_target_btn.clicked.connect(self.select_target_path)
        target_header.addWidget(self.target_label)
        target_header.addWidget(self.target_path)
        target_header.addWidget(self.select_target_btn)
        target_layout.addLayout(target_header)

        # 目标目录错误提示
        self.target_error = QLabel("")
        self.target_error.setStyleSheet(self.config['ui']['style']['error_label'])
        self.target_error.hide()
        target_layout.addWidget(self.target_error)

        layout.addLayout(target_layout)

        # 片段列表选择区域
        clip_layout = QVBoxLayout()
        clip_header = QHBoxLayout()
        self.clip_label = QLabel(self.get_text('ui.layout.clip_list.label'))
        self.clip_list_path = QLineEdit()
        self.clip_list_path.setReadOnly(True)
        self.select_clip_btn = QPushButton(self.get_text('ui.layout.clip_list.button'))
        self.select_clip_btn.setStyleSheet(self.config['ui']['style']['button']['normal'])
        self.select_clip_btn.clicked.connect(self.select_clip_list)
        clip_header.addWidget(self.clip_label)
        clip_header.addWidget(self.clip_list_path)
        clip_header.addWidget(self.select_clip_btn)
        clip_layout.addLayout(clip_header)

        # 片段列表错误提示
        self.clip_error = QLabel("")
        self.clip_error.setStyleSheet(self.config['ui']['style']['error_label'])
        self.clip_error.hide()
        clip_layout.addWidget(self.clip_error)

        layout.addLayout(clip_layout)

        # 复制模式选择
        mode_layout = QHBoxLayout()
        self.mode_label = QLabel(self.get_text('ui.layout.copy_mode.label'))
        self.copy_mode = QComboBox()
        self.copy_mode.addItem(self.get_text('ui.combobox.copy_mode.flat'), 'flat')
        self.copy_mode.addItem(self.get_text('ui.combobox.copy_mode.structure'), 'structure')
        mode_layout.addWidget(self.mode_label)
        mode_layout.addWidget(self.copy_mode)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # 选项区域
        options_layout = QHBoxLayout()
        self.options_label = QLabel(self.get_text('ui.layout.options.label'))
        self.checksum_checkbox = QCheckBox(self.get_text('ui.checkboxes.checksum'))
        self.handle_red_checkbox = QCheckBox(self.get_text('ui.checkboxes.handle_red_folders'))
        self.handle_red_checkbox.setChecked(True)

        options_layout.addWidget(self.options_label)
        options_layout.addWidget(self.checksum_checkbox)
        options_layout.addWidget(self.handle_red_checkbox)
        options_layout.addStretch()
        layout.addLayout(options_layout)

        # 控制按钮
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton(self.get_text('ui.buttons.start_copy'))
        self.start_btn.setStyleSheet(self.config['ui']['style']['button']['primary'])
        self.start_btn.clicked.connect(self.start_copy)
        self.stop_btn = QPushButton(self.get_text('ui.buttons.stop_copy'))
        self.stop_btn.setStyleSheet(self.config['ui']['style']['button']['normal'])
        self.stop_btn.clicked.connect(self.stop_copy)
        self.stop_btn.setEnabled(False)

        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addStretch()
        layout.addLayout(control_layout)

        # 日志区域
        log_frame = QFrame()
        log_frame.setFrameStyle(QFrame.StyledPanel)
        log_layout = QVBoxLayout()
        log_header = QHBoxLayout()
        self.log_label = QLabel(self.get_text('ui.log.title'))
        self.clear_log_btn = QPushButton(self.get_text('ui.buttons.clear_log'))
        self.clear_log_btn.setStyleSheet(self.config['ui']['style']['button']['normal'])
        self.clear_log_btn.clicked.connect(self.clear_log)
        self.save_log_btn = QPushButton(self.get_text('ui.buttons.save_log'))
        self.save_log_btn.setStyleSheet(self.config['ui']['style']['button']['normal'])
        self.save_log_btn.clicked.connect(self.save_log)

        log_header.addWidget(self.log_label)
        log_header.addStretch()
        log_header.addWidget(self.clear_log_btn)
        log_header.addWidget(self.save_log_btn)
        log_layout.addLayout(log_header)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_frame.setLayout(log_layout)
        layout.addWidget(log_frame)

        # 版权信息
        bottom_info = QHBoxLayout()
        self.copyright_label = QLabel(self.get_text('app.copyright'))
        self.copyright_label.setAlignment(Qt.AlignLeft)
        bottom_info.addWidget(self.copyright_label)
        
        # 版本信息（右对齐）
        version_label = QLabel(f"v{self.config['app']['version']}")
        version_label.setStyleSheet("color: gray;")
        version_label.setAlignment(Qt.AlignRight)
        bottom_info.addWidget(version_label)
        self.version_label = version_label
        
        layout.addLayout(bottom_info)

        # 设置工具提示
        self.set_tooltips()

    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu(self.get_text('ui.menu.file'))
        exit_action = QAction(self.get_text('ui.menu.exit'), self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu(self.get_text('ui.menu.help'))
        usage_action = QAction(self.get_text('ui.menu.usage'), self)
        usage_action.triggered.connect(self.show_usage)
        help_menu.addAction(usage_action)
        
        about_action = QAction(self.get_text('ui.menu.about'), self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        # 语言菜单（独立菜单）
        language_menu = menubar.addMenu(self.get_text('ui.menu.language'))
        
        # 中文简体
        zh_cn_action = QAction("简体中文", self)
        zh_cn_action.triggered.connect(lambda: self.change_language('zh_cn'))
        language_menu.addAction(zh_cn_action)
        
        # 中文繁体
        zh_tw_action = QAction("繁體中文", self)
        zh_tw_action.triggered.connect(lambda: self.change_language('zh_tw'))
        language_menu.addAction(zh_tw_action)
        
        # 英文
        en_action = QAction("English", self)
        en_action.triggered.connect(lambda: self.change_language('en'))
        language_menu.addAction(en_action)

    def change_language(self, lang_code):
        """切换语言"""
        self.current_language = lang_code
        self.update_ui_text()

    def update_ui_text(self):
        """更新UI文本"""
        # 更新窗口标题
        self.setWindowTitle(self.get_text('ui.window.title'))
        
        # 更新状态栏
        self.statusBar.showMessage(self.get_text('ui.status.ready'))
        
        # 更新菜单文本
        menubar = self.menuBar()
        # 更新文件菜单
        file_menu = menubar.actions()[0]
        file_menu.setText(self.get_text('ui.menu.file'))
        file_menu.menu().actions()[0].setText(self.get_text('ui.menu.exit'))
        
        # 更新帮助菜单
        help_menu = menubar.actions()[1]
        help_menu.setText(self.get_text('ui.menu.help'))
        help_actions = help_menu.menu().actions()
        help_actions[0].setText(self.get_text('ui.menu.usage'))
        help_actions[1].setText(self.get_text('ui.menu.about'))
        
        # 更新语言菜单
        language_menu = menubar.actions()[2]
        language_menu.setText(self.get_text('ui.menu.language'))
        
        # 更新源目录区域
        self.source_label.setText(self.get_text('ui.layout.source_path.label'))
        self.add_source_btn.setText(self.get_text('ui.layout.add_source.button'))
        
        # 更新目标目录区域
        self.target_label.setText(self.get_text('ui.layout.target_path.label'))
        self.target_path.setPlaceholderText(self.get_text('ui.layout.target_path.placeholder'))
        self.select_target_btn.setText(self.get_text('ui.layout.target_path.button'))
        
        # 更新片段列表区域
        self.clip_label.setText(self.get_text('ui.layout.clip_list.label'))
        self.clip_list_path.setPlaceholderText(self.get_text('ui.layout.clip_list.placeholder'))
        self.select_clip_btn.setText(self.get_text('ui.layout.clip_list.button'))
        
        # 更新复制模式选项
        self.mode_label.setText(self.get_text('ui.layout.copy_mode.label'))
        self.copy_mode.setItemText(0, self.get_text('ui.combobox.copy_mode.flat'))
        self.copy_mode.setItemText(1, self.get_text('ui.combobox.copy_mode.structure'))
        
        # 更新选项区域
        self.options_label.setText(self.get_text('ui.layout.options.label'))
        self.checksum_checkbox.setText(self.get_text('ui.checkboxes.checksum'))
        self.handle_red_checkbox.setText(self.get_text('ui.checkboxes.handle_red_folders'))
        
        # 更新按钮文本
        self.start_btn.setText(self.get_text('ui.buttons.start_copy'))
        self.stop_btn.setText(self.get_text('ui.buttons.stop_copy'))
        
        # 更新日志区域
        self.log_label.setText(self.get_text('ui.log.title'))
        self.clear_log_btn.setText(self.get_text('ui.buttons.clear_log'))
        self.save_log_btn.setText(self.get_text('ui.buttons.save_log'))
        
        # 更新版权信息
        self.copyright_label.setText(self.get_text('app.copyright'))
        
        # 更新版本信息
        self.version_label.setText(f"v{self.config['app']['version']}")
        
        # 更新工具提示
        self.set_tooltips()

    def show_usage(self):
        """显示使用说明"""
        usage_text = "\n".join(self.config['usage_steps'][self.current_language])
        QMessageBox.information(self, 
                              self.get_text('ui.menu.usage'),
                              usage_text)

    def show_about(self):
        """显示关于对话框"""
        about_text = f"{self.get_text('app.name')}\n" \
                    f"{self.get_text('app.version')}\n" \
                    f"{self.get_text('app.copyright')}"
        QMessageBox.about(self, 
                         self.get_text('ui.menu.about'),
                         about_text)

    def set_tooltips(self):
        self.checksum_checkbox.setToolTip(self.get_text('ui.tooltips.checksum'))
        self.handle_red_checkbox.setToolTip(self.get_text('ui.tooltips.handle_red_folders'))
        self.copy_mode.setToolTip(self.get_text('ui.tooltips.copy_mode'))

    def add_source_path(self):
        """选择源目录"""
        path = QFileDialog.getExistingDirectory(self, self.get_text('ui.layout.source_path.label'))
        if path:
            self.source_paths.append(Path(path))
            self.update_source_paths_label()
            self.source_error.hide()

    def update_source_paths_label(self):
        paths = [str(p) for p in self.source_paths]
        self.source_paths_label.setText(" | ".join(paths))

    def select_target_path(self):
        """选择目标目录"""
        path = QFileDialog.getExistingDirectory(self, self.get_text('ui.layout.target_path.label'))
        if path:
            self.target_path.setText(path)
            self.target_error.hide()

    def select_clip_list(self):
        """选择片段列表文件"""
        path, _ = QFileDialog.getOpenFileName(
            self, 
            self.get_text('ui.layout.clip_list.label'),
            "",
            "EDL and Text Files (*.edl *.txt);;All Files (*.*)"
        )
        if path:
            self.clip_list_path.setText(path)
            self.clip_error.hide()
            self.validate_inputs()

    def validate_inputs(self):
        is_valid = True
        
        if not self.source_paths:
            self.source_error.setText(self.get_text('ui.messages.no_source'))
            self.source_error.show()
            is_valid = False
            
        if not self.target_path.text():
            self.target_error.setText(self.get_text('ui.messages.no_target'))
            self.target_error.show()
            is_valid = False
            
        if not self.clip_list_path.text():
            self.clip_error.setText(self.get_text('ui.messages.no_clip_list'))
            self.clip_error.show()
            is_valid = False
            
        return is_valid

    def start_copy(self):
        """开始复制"""
        if not self.validate_inputs():
            return

        config = CopyConfig(
            source_paths=self.source_paths,
            target_path=Path(self.target_path.text()),
            clip_list_path=Path(self.clip_list_path.text()),
            copy_mode=CopyMode.STRUCTURE if self.copy_mode.currentData() == 
                     'structure' else CopyMode.FLAT,
            checksum=self.checksum_checkbox.isChecked(),
            handle_red_folders=self.handle_red_checkbox.isChecked()
        )

        # 创建并启动工作线程
        self.copy_worker = CopyWorker(config)
        self.copy_worker.progress.connect(self.update_log)
        self.copy_worker.finished.connect(self.copy_finished)
        self.copy_worker.error.connect(self.show_error)
        self.copy_worker.start()

        # 更新UI状态
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.statusBar.showMessage(self.get_text('ui.status.processing'))
        self.log_text.append(self.get_text('ui.status.processing'))

    def stop_copy(self):
        """停止复制"""
        if self.copy_worker:
            self.copy_worker.stop()
            self.copy_worker.wait()
            self.log_text.append(self.get_text('ui.status.stopped'))
            self.statusBar.showMessage(self.get_text('ui.status.stopped'))
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def copy_finished(self, success, message):
        """复制完成处理"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if success:
            self.statusBar.showMessage(self.get_text('ui.status.complete'))
            QMessageBox.information(self, 
                                  self.get_text('ui.status.complete'),
                                  message)
        else:
            self.statusBar.showMessage(self.get_text('ui.status.error').format(message))
            QMessageBox.critical(self, 
                               self.get_text('ui.status.error').format(""),
                               message)

    def update_log(self, message):
        """更新日志"""
        self.log_text.append(message)

    def clear_log(self):
        """清除日志"""
        self.log_text.clear()

    def save_log(self):
        """保存日志"""
        path, _ = QFileDialog.getSaveFileName(
            self, 
            self.get_text('ui.buttons.save_log'),
            "",
            "Text Files (*.txt);;All Files (*.*)"
        )
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.log_text.toPlainText())

    def show_error(self, message):
        """显示错误消息"""
        QMessageBox.critical(self, self.get_text('ui.messages.error'), message)

def main():
    app = QApplication(sys.argv)
    window = BatchCopyGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 