"""
    @author: Siyu Chen
    @email: chensy57@mail2.sysu.edu.cn
    @version: 3.4 (Robust SHP CRS Handling)
    @date: 2025/06/11
    @license: MIT License
    @description: An advanced geospatial data viewer for NetCDF and Shapefiles with a modern UI,
                 using PyQt5, Matplotlib, Geopandas, and Cartopy.
    @requirements: PyQt5, netCDF4, matplotlib, geopandas, cartopy, numpy, qtawesome
    @envinfo: pyqt_env
"""

import sys
import os
import netCDF4
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import cartopy.crs as ccrs
import qtawesome as qta

from PyQt5.QtWidgets import (QApplication, QMainWindow, QTextEdit, QPushButton, QVBoxLayout,
                             QWidget, QFileDialog, QHBoxLayout, QSplitter, QListWidget,
                             QTabWidget, QMessageBox, QListWidgetItem, QLabel)
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor, QFont
from PyQt5.QtCore import Qt, QSize

# --- Matplotlib and Cartopy Global Configuration ---
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

# --- Modern UI Stylesheet (QSS) ---
MODERN_STYLE_SHEET = """
    QMainWindow {
        background-color: #fcfcfc;
    }
    QWidget {
        font-family: 'Segoe UI', 'Microsoft YaHei';
        font-size: 10pt;
    }
    QSplitter::handle {
        background-color: #e0e0e0;
        width: 1px;
    }
    QSplitter::handle:hover {
        background-color: #b0b0b0;
    }
    QTabWidget::pane {
        border: 1px solid #e0e0e0;
        border-radius: 4px;
    }
    QTabBar::tab {
        background: #f0f0f0;
        border: 1px solid #e0e0e0;
        border-bottom: none;
        padding: 8px 20px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    QTabBar::tab:selected {
        background: #fcfcfc;
        border-bottom: 1px solid #fcfcfc;
    }
    QTabBar::tab:!selected:hover {
        background: #e6e6e6;
    }
    QPushButton {
        background-color: #0078d7;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #005a9e;
    }
    QPushButton:pressed {
        background-color: #004578;
    }
    QListWidget {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        padding: 5px;
    }
    QListWidget::item {
        padding: 8px;
    }
    QListWidget::item:hover {
        background-color: #f0f8ff;
    }
    QListWidget::item:selected {
        background-color: #0078d7;
        color: white;
    }
    QTextEdit {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        padding: 5px;
        font-size: 10pt;
    }
    /* Style for Matplotlib Toolbar */
    #matplotlib-toolbar {
        background-color: #fcfcfc;
    }
    /* ScrollBar Styling */
    QScrollBar:vertical {
        border: none;
        background: #fcfcfc;
        width: 10px;
        margin: 0px 0px 0px 0px;
    }
    QScrollBar::handle:vertical {
        background: #c0c0c0;
        min-height: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical:hover {
        background: #a0a0a0;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar:horizontal {
        border: none;
        background: #fcfcfc;
        height: 10px;
        margin: 0px 0px 0px 0px;
    }
    QScrollBar::handle:horizontal {
        background: #c0c0c0;
        min-width: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:horizontal:hover {
        background: #a0a0a0;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }
"""

# --- Custom Navigation Toolbar to prevent Cartopy errors ---
class SafeCartopyToolbar(NavigationToolbar):
    def __init__(self, canvas, parent=None):
        super().__init__(canvas, parent)

    def home(self, *args):
        """Override home button to handle GeoAxes without crashing."""
        try:
            super().home(*args)
        except AttributeError:
            # This error occurs with GeoAxes. We'll manually reset the view.
            for ax in self.canvas.figure.axes:
                if isinstance(ax, ccrs.GeoAxes):
                    ax.set_global()
                ax._autoscaleXon = False
                ax._autoscaleYon = False
            self.canvas.draw_idle()

    def back(self, *args):
        """Override back button to prevent crash on GeoAxes."""
        try:
            super().back(*args)
        except AttributeError:
            pass  # Ignore error for cartopy

    def forward(self, *args):
        """Override forward button to prevent crash on GeoAxes."""
        try:
            super().forward(*args)
        except AttributeError:
            pass  # Ignore error for cartopy

class GeospatialTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.nc_dataset = None
        self.history_file = "history.txt"
        self.history = self.loadHistory()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('地理空间数据可视化工具 (NC/SHP) - V3.4')
        self.setGeometry(100, 100, 1400, 900)
        self.setWindowIcon(qta.icon('fa5s.globe-americas', color='#0078d7'))

        main_layout = QHBoxLayout()
        splitter = QSplitter(Qt.Horizontal)

        # --- Left Panel ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 10, 10, 10)
        left_layout.setSpacing(10)

        # Action Buttons
        btn_open_file = QPushButton(qta.icon('fa5s.folder-open', color='white'), ' 打开文件')
        btn_open_file.clicked.connect(self.show_file_dialog)
        btn_open_file.setIconSize(QSize(16, 16))

        btn_show_history = QPushButton(qta.icon('fa5s.history', color='white'), ' 显示历史')
        btn_show_history.clicked.connect(self.display_history)
        btn_show_history.setIconSize(QSize(16, 16))

        button_layout = QHBoxLayout()
        button_layout.addWidget(btn_open_file)
        button_layout.addWidget(btn_show_history)

        # Variable List
        variable_label = QLabel("可绘制变量 (双击绘图)")
        variable_label.setStyleSheet("font-weight: bold; padding: 5px 0;")
        self.variable_list = QListWidget(self)
        self.variable_list.itemDoubleClicked.connect(self.on_variable_selected)

        left_layout.addLayout(button_layout)
        left_layout.addWidget(variable_label)
        left_layout.addWidget(self.variable_list)

        # --- Main Area (Tabs) ---
        self.tabs = QTabWidget()
        self.info_tab = QWidget()
        self.plot_tab = QWidget()
        self.tabs.addTab(self.info_tab, "文件元数据")
        self.tabs.addTab(self.plot_tab, "数据可视化")

        # Info Tab
        info_layout = QVBoxLayout(self.info_tab)
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        info_layout.addWidget(self.text_edit)

        # Plot Tab
        plot_layout = QVBoxLayout(self.plot_tab)
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        # Use the new safe toolbar instead of the default one
        self.toolbar = SafeCartopyToolbar(self.canvas, self)
        self.toolbar.setObjectName("matplotlib-toolbar") # ID for styling
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)

        # Assembly
        splitter.addWidget(left_panel)
        splitter.addWidget(self.tabs)
        splitter.setSizes([350, 1050]) # Initial size distribution
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.load_file(files[0])

    def show_file_dialog(self):
        fname, _ = QFileDialog.getOpenFileName(self, '打开文件', '',
                                               "All Supported Files (*.nc *.shp);;NetCDF files (*.nc);;Shapefiles (*.shp)")
        if fname:
            self.load_file(fname)

    def on_variable_selected(self, item):
        if self.nc_dataset:
            variable_name = item.text().split(' ')[0]
            self.plot_nc_variable(variable_name)

    def load_file(self, filepath):
        self.text_edit.clear()
        self.variable_list.clear()
        self.clear_plot()

        _, ext = os.path.splitext(filepath)
        if ext.lower() == '.nc':
            self.load_nc_file(filepath)
        elif ext.lower() == '.shp':
            self.load_shp_file(filepath)
        else:
            self.show_error_message(f"不支持的文件类型: {ext}")
            return

        if filepath not in self.history:
            self.history.append(filepath)
            self.saveHistory()

    def load_nc_file(self, filepath):
        try:
            if self.nc_dataset:
                self.nc_dataset.close()
            self.nc_dataset = netCDF4.Dataset(filepath, 'r')
            self.append_formatted_text(f"文件: {filepath}\n", title=True)
            self.display_nc_metadata()
            self.populate_variable_list()
            self.tabs.setCurrentWidget(self.info_tab)
        except Exception as e:
            self.show_error_message(f"读取NC文件失败 {filepath}: {e}")
            self.nc_dataset = None

    def load_shp_file(self, filepath):
        try:
            self.append_formatted_text(f"文件: {filepath}\n", title=True)
            gdf = gpd.read_file(filepath)
            self.append_formatted_text("Shapefile 信息:", header=True)
            self.append_formatted_text(f"  坐标参考系统 (CRS): {gdf.crs}")
            self.append_formatted_text(f"  要素数量: {len(gdf)}")
            self.append_formatted_text(f"  几何类型: {gdf.geom_type.unique()}")
            self.plot_shp_data(gdf)
            self.tabs.setCurrentWidget(self.plot_tab)
        except Exception as e:
            self.show_error_message(f"读取SHP文件失败 {filepath}: {e}")

    def display_nc_metadata(self):
        if not self.nc_dataset: return
        self.append_formatted_text("全局属性:", header=True)
        if not self.nc_dataset.ncattrs():
             self.append_formatted_text("  (无)", italic=True)
        for attr_name in self.nc_dataset.ncattrs():
            self.append_formatted_text(f"  {attr_name}: {getattr(self.nc_dataset, attr_name)}")
        self.append_formatted_text("\n维度信息:", header=True)
        for dim_name, dim in self.nc_dataset.dimensions.items():
            self.append_formatted_text(f"  {dim_name}: size = {len(dim)}")
        self.append_formatted_text("\n变量信息:", header=True)
        for var_name, var in self.nc_dataset.variables.items():
            self.append_formatted_text(f"  {var_name}: dims={var.dimensions}, shape={var.shape}, type={var.dtype}", bold=True)
            for attr_name in var.ncattrs():
                self.append_formatted_text(f"    {attr_name}: {getattr(var, attr_name)}")

    def populate_variable_list(self):
        self.variable_list.clear()
        if not self.nc_dataset: return
        for var_name, var in self.nc_dataset.variables.items():
            if len(var.shape) >= 2:
                item_text = f"{var_name} {var.shape}"
                list_item = QListWidgetItem(qta.icon('fa5s.ruler-combined', color='#0078d7'), item_text)
                self.variable_list.addItem(list_item)

    def plot_nc_variable(self, var_name):
        try:
            var = self.nc_dataset.variables[var_name]
            data = var[:]
            if data.ndim > 2: data = np.squeeze(data)
            if data.ndim != 2:
                self.show_error_message(f"变量 '{var_name}' 不是一个二维数组 (shape: {data.shape}).")
                return
            lon, lat = self.find_nc_coords(var)
            if lon is None or lat is None:
                self.show_error_message(f"无法自动找到 '{var_name}' 的经纬度坐标。")
                return

            self.clear_plot()
            ax = self.figure.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
            
            # --- FIX: Manually set autoscale attributes to prevent crash ---
            ax._autoscaleXon = False
            ax._autoscaleYon = False
            
            ax.set_global()
            im = ax.pcolormesh(lon, lat, data, transform=ccrs.PlateCarree(), cmap='viridis', shading='auto')
            ax.coastlines()
            ax.gridlines(draw_labels=True, linestyle='--', color='gray', alpha=0.5)
            cbar = plt.colorbar(im, ax=ax, orientation='vertical', pad=0.08, shrink=0.8)
            cbar.set_label(f"{var_name} ({getattr(var, 'units', '')})")
            ax.set_title(f"变量: {getattr(var, 'long_name', var_name)}", pad=20)
            self.canvas.draw()
            self.tabs.setCurrentWidget(self.plot_tab)
        except Exception as e:
            self.show_error_message(f"绘制变量 '{var_name}' 出错: {e}")

    def find_nc_coords(self, var):
        lon, lat = None, None
        possible_lon_names = ['lon', 'longitude', 'x']
        possible_lat_names = ['lat', 'latitude', 'y']
        for dim_name in var.dimensions:
            for name in possible_lon_names:
                if name in dim_name.lower() and dim_name in self.nc_dataset.variables:
                    lon = self.nc_dataset.variables[dim_name][:]
            for name in possible_lat_names:
                if name in dim_name.lower() and dim_name in self.nc_dataset.variables:
                    lat = self.nc_dataset.variables[dim_name][:]
        if lon is not None and lat is not None and lon.ndim == 1 and lat.ndim == 1:
            lon, lat = np.meshgrid(lon, lat)
        return lon, lat

    def plot_shp_data(self, gdf):
        try:
            self.clear_plot()

            source_crs = gdf.crs
            cartopy_crs = None

            # --- FIX STARTS HERE: More robust CRS handling ---
            if source_crs:
                try:
                    # First, try the direct EPSG conversion
                    epsg = source_crs.to_epsg()
                    if epsg:
                        cartopy_crs = ccrs.epsg(epsg)
                except Exception:
                    # If direct conversion fails, check if it's a geographic CRS (like WGS84)
                    if source_crs.is_geographic:
                        # For geographic CRS, PlateCarree is the correct Cartopy equivalent
                        cartopy_crs = ccrs.PlateCarree()
                        self.append_formatted_text("  提示: 已自动识别为WGS84地理坐标系。", italic=True)
                    else:
                        # If it's a projected CRS we can't easily convert, show an error
                        self.show_error_message("无法自动转换投影坐标系。请使用标准EPSG代码的Shapefile。")
                        return
            
            if not cartopy_crs:
                self.show_error_message("Shapefile缺少有效的或可识别的坐标参考系统(CRS)，无法绘图。")
                return
            # --- FIX ENDS HERE ---

            ax = self.figure.add_subplot(1, 1, 1, projection=ccrs.Mercator())

            # --- FIX: Manually set autoscale attributes to prevent crash ---
            ax._autoscaleXon = False
            ax._autoscaleYon = False

            minx, miny, maxx, maxy = gdf.total_bounds
            
            # Use the newly created cartopy_crs for setting the extent
            ax.set_extent([minx, maxx, miny, maxy], crs=cartopy_crs)

            ax.coastlines()
            ax.gridlines(draw_labels=True, linestyle='--', color='gray', alpha=0.5)
            
            # Use the cartopy_crs for the transform argument
            gdf.plot(ax=ax, edgecolor='#333333', facecolor='#0078d7', alpha=0.6, transform=cartopy_crs)
            
            ax.set_title("Shapefile 可视化", pad=20)
            self.canvas.draw()
        except Exception as e:
            self.show_error_message(f"绘制SHP文件出错: {e}")

    def clear_plot(self):
        self.figure.clear()
        self.canvas.draw()

    def display_history(self):
        self.text_edit.clear()
        self.variable_list.clear()
        self.clear_plot()
        if self.history:
            self.append_formatted_text("历史记录:", title=True)
            for filepath in self.history:
                self.append_formatted_text(filepath)
        else:
            self.append_formatted_text("没有历史记录.", italic=True)
        self.tabs.setCurrentWidget(self.info_tab)

    def loadHistory(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding='utf-8') as file:
                    return [line.strip() for line in file if line.strip()]
            except Exception as e:
                print(f"Warning: Could not load history file. {e}")
        return []

    def saveHistory(self):
        try:
            with open(self.history_file, "w", encoding='utf-8') as file:
                file.write("\n".join(self.history))
        except Exception as e:
            print(f"Warning: Could not save history file. {e}")

    def closeEvent(self, event):
        if self.nc_dataset: self.nc_dataset.close()
        event.accept()

    def append_formatted_text(self, text, title=False, header=False, bold=False, italic=False):
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.End)
        char_format = QTextCharFormat()
        font = QFont("Segoe UI", 10)
        char_format.setFont(font)
        if title:
            font.setBold(True)
            font.setPointSize(15)
            char_format.setFont(font)
            char_format.setForeground(QColor("#0078d7"))
        elif header:
            font.setBold(True)
            font.setPointSize(12)
            char_format.setFont(font)
            char_format.setForeground(QColor("#333333"))
        elif bold:
            font.setBold(True)
            char_format.setFont(font)
        elif italic:
            font.setItalic(True)
            char_format.setFont(font)
            char_format.setForeground(QColor("gray"))
        cursor.insertText(text + "\n", char_format)
        self.text_edit.ensureCursorVisible()

    def show_error_message(self, message):
        QMessageBox.critical(self, "错误", message)
        self.append_formatted_text(f"错误: {message}", italic=True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(MODERN_STYLE_SHEET) # Apply the modern stylesheet
    ex = GeospatialTool()
    ex.show()
    sys.exit(app.exec_())
