"""
    @author: Siyu Chen
    @email: chensy57@mail2.sysu.edu.cn
    @version: 1.0
    @date: 2024/12/01
    @license: MIT License
    @description: A NetCDF file information viewer using PyQt5.
    @requirements: PyQt5, netCDF4
"""

import sys
import os
import netCDF4
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QPushButton, QVBoxLayout, QWidget, QFileDialog, QHBoxLayout
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor, QFont

class NcInfoViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.history_file = "history.txt"
        self.history = self.loadHistory()  # 加载历史记录

    def initUI(self):
        self.setWindowTitle('NetCDF File Information Viewer')
        self.setGeometry(100, 100, 1000, 700)  # 增加窗口大小
        
        layout = QVBoxLayout()
        
        # 添加按钮
        self.btnOpen = QPushButton('Open NetCDF File', self)
        self.btnOpen.clicked.connect(self.showDialog)
        
        self.btnClear = QPushButton('Clear', self)
        self.btnClear.clicked.connect(self.clearText)

        self.btnShowHistory = QPushButton('Show History', self)
        self.btnShowHistory.clicked.connect(self.displayHistory)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.btnOpen)
        buttonLayout.addWidget(self.btnClear)
        buttonLayout.addWidget(self.btnShowHistory)

        # 创建文本编辑框，用于显示文件信息
        self.textEdit = QTextEdit(self)
        self.textEdit.setReadOnly(True)  # 设置为只读
        self.textEdit.setStyleSheet("font-size: 14px;")  # 增加字体大小

        layout.addLayout(buttonLayout)
        layout.addWidget(self.textEdit)

        centralWidget = QWidget()
        centralWidget.setLayout(layout)
        self.setCentralWidget(centralWidget)

        # 启用拖拽功能
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        """拖拽进入事件，判断是否为文件"""
        if event.mimeData().hasUrls():  # 确保拖拽的内容是文件
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """拖放事件，获取文件路径并加载信息"""
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.loadNcInfo(files[0])

    def showDialog(self):
        fname = QFileDialog.getOpenFileName(self, 'Open file', '', "NetCDF files (*.nc)")
        if fname[0]:
            self.loadNcInfo(fname[0])

    def loadNcInfo(self, filepath, append=False):
        try:
            # 打开 NetCDF 文件
            nc_dataset = netCDF4.Dataset(filepath, 'r')

            if not append:
                self.textEdit.clear()  # 清空当前显示

            self.appendFormattedText(f"File: {filepath}", header=True)
            
            # 读取全局属性
            self.appendFormattedText("Global Attributes:", header=True)
            for attr_name in nc_dataset.ncattrs():
                self.appendFormattedText(f"  {attr_name}: {getattr(nc_dataset, attr_name)}", header=False)
            
            # 读取维度信息
            self.appendFormattedText("Dimensions:", header=True)
            for dim_name, dim in nc_dataset.dimensions.items():
                self.appendFormattedText(f"  {dim_name}: size = {len(dim)}", header=False)
            
            # 读取变量信息
            self.appendFormattedText("Variables:", header=True)
            for var_name, var in nc_dataset.variables.items():
                self.appendFormattedText(f"  {var_name}: dimensions={var.dimensions}, type={var.dtype}", header=False)
                for attr_name in var.ncattrs():
                    self.appendFormattedText(f"    {attr_name}: {getattr(var, attr_name)}", header=False)
            
            nc_dataset.close()

            # 保存到历史记录
            if filepath not in self.history:
                self.history.append(filepath)
                self.saveHistory()

            if append:
                # 添加分隔线
                self.appendSeparator()

        except Exception as e:
            self.appendFormattedText(f"Error reading file {filepath}: {e}", header=False)

    def appendFormattedText(self, text, header=False):
        """格式化文本显示"""
        cursor = self.textEdit.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        char_format = QTextCharFormat()
        if header:
            # 设置标题样式
            char_format.setFont(QFont("Times New Roman", 14, QFont.Bold))
            char_format.setBackground(QColor("red"))
            char_format.setForeground(QColor("white"))
        else:
            # 设置普通文本样式
            char_format.setFont(QFont("Times New Roman", 12))
            char_format.setBackground(QColor("white"))
            char_format.setForeground(QColor("black"))
        
        cursor.insertText(text + "\n", char_format)

    def appendSeparator(self):
        """添加分隔线"""
        cursor = self.textEdit.textCursor()
        cursor.movePosition(QTextCursor.End)

        # 设置分隔线的格式
        char_format = QTextCharFormat()
        char_format.setFont(QFont("Times New Roman", 12))
        char_format.setForeground(QColor("gray"))

        separator_line = "-" * 80  # 可以调整长度
        cursor.insertText(separator_line + "\n", char_format)

    def clearText(self):
        """清除显示区域的内容"""
        self.textEdit.clear()

    def displayHistory(self):
        """显示历史记录"""
        self.textEdit.clear()
        if self.history:
            for idx, filepath in enumerate(self.history):
                self.loadNcInfo(filepath, append=True)
        else:
            self.appendFormattedText("No history available.", header=False)

    def loadHistory(self):
        """加载历史记录"""
        if os.path.exists(self.history_file):
            with open(self.history_file, "r") as file:
                return file.read().splitlines()
        return []

    def saveHistory(self):
        """保存历史记录到文件"""
        with open(self.history_file, "w") as file:
            file.write("\n".join(self.history))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = NcInfoViewer()
    ex.show()
    sys.exit(app.exec_())
