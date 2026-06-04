import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
                             QDialog, QLabel, QLineEdit, QTextEdit, QSpinBox, 
                             QDoubleSpinBox, QComboBox, QCalendarWidget, QMessageBox,
                             QHeaderView, QAbstractItemView, QTabWidget, QGridLayout,
                             QFrame, QFileDialog, QRadioButton, QButtonGroup)
from PyQt5.QtCore import Qt, QDate, QTimer, pyqtSignal, QLocale
from PyQt5.QtGui import QFont, QColor, QTextDocument, QIcon
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
import jdatetime


class PersianCalendarWidget(QCalendarWidget):
    """ویجت تقویم شمسی سفارشی"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLocale(QLocale(QLocale.Persian, QLocale.Iran))  # ← اصلاح شد
        self.setFirstDayOfWeek(Qt.Saturday)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        
        font = QFont("Segoe UI", 10)
        self.setFont(font)
        
        today = jdatetime.date.today()
        gregorian_date = today.togregorian()
        self.setSelectedDate(QDate(gregorian_date.year, gregorian_date.month, gregorian_date.day))
    
    def get_persian_date(self):
        """دریافت تاریخ شمسی انتخاب شده"""
        selected = self.selectedDate()
        gregorian = datetime(selected.year(), selected.month(), selected.day())
        jalali = jdatetime.date.fromgregorian(date=gregorian.date())
        return jalali.strftime("%Y/%m/%d")



class PersianDateEdit(QLineEdit):
    """ویجت ورودی تاریخ شمسی"""
    
    dateChanged = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("YYYY/MM/DD")
        self.setReadOnly(True)
        
        # تنظیم تاریخ امروز
        today = jdatetime.date.today()
        self.setText(today.strftime("%Y/%m/%d"))
        
        # دکمه انتخاب تاریخ
        self.calendar_btn = QPushButton("📅", self)
        self.calendar_btn.setFixedSize(30, 25)
        self.calendar_btn.clicked.connect(self.show_calendar)
        
        # چیدمان
        self.setStyleSheet("padding-right: 35px;")
        
    def resizeEvent(self, event):
        """تنظیم موقعیت دکمه"""
        super().resizeEvent(event)
        self.calendar_btn.move(5, 2)
    
    def show_calendar(self):
        """نمایش تقویم"""
        dialog = QDialog(self)
        dialog.setWindowTitle("انتخاب تاریخ")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        calendar = PersianCalendarWidget()
        layout.addWidget(calendar)
        
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("تأیید")
        cancel_btn = QPushButton("انصراف")
        
        ok_btn.clicked.connect(lambda: self.set_date(calendar.get_persian_date(), dialog))
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def set_date(self, date_str, dialog):
        """تنظیم تاریخ"""
        self.setText(date_str)
        self.dateChanged.emit(date_str)
        dialog.accept()
    
    def get_date(self):
        """دریافت تاریخ"""
        return self.text()