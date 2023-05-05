# -*- coding: utf-8 -*-
# Author: Chen Pei Yu
# Date: 2023 Jan.

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication
import sys
import Layout
        
StyleSheet = """
QPushButton{
    border: 1px solid #ADD8E6;
    border-radius: 4px;
    background-color: #ADD8E6; /*背景颜色*/
    margin:2px;
}
QPushButton:hover {
    background-color: #B0CFDE; /*鼠标悬停时背景颜色*/
}

QPushButton:pressed {
    background-color: #AFDCEC; /*鼠标按下不放时背景颜色*/
}


#progressBar {
    border: 1px solid grey;
    border-radius: 3px;
    background-color: transparent;
    text-align: center;
    qproperty-textVisible: false; /* 文本可见属性设为false，即为不可见 */
    height: 8px;
    margin:2px;
}

#progressBar::chunk {
  background-color: #83E800;
  width: 8px; /* 进度块宽度，垂直进度条则使用height */
  margin: 0.5px; /* 进度块间隔 */
  /* width与margin同时使用，可显示进度块 */
}

"""

class PluginApp(QtWidgets.QMainWindow, Layout.Ui_MainWindow):
    def __init__(self, parent=None):
        super(PluginApp, self).__init__(parent)
        self.setupUi(self)

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(StyleSheet)
    form = PluginApp()
    form.show()
    app.exec_()
    

    

if __name__ == '__main__':
        
    main()