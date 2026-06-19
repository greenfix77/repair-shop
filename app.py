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

from core.status import (
    STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_COMPLETED, STATUS_DELIVERED,
    ALL_STATUSES, ALL_STATUSES_WITH_ALL,
    STATUS_COLORS, DEFAULT_STATUS_COLOR,
    STATUS_FG_COLORS
)
from repair_manager.ui.components import PersianCalendarWidget, PersianDateEdit
from ui.table_renderer import render_table_rows
from core.storage.repairs_storage import RepairsStorage
from services.statistics import update_statistics
from core.filters import search_repairs, filter_repairs
from services.table_service import build_table_rows
from services.repair_service import add_repair, delete_repair, get_repair_by_id, update_repair
from services.date_service import today_persian
from services.calculations import calculate_invoice
from services.invoice_calculator import calculate_invoice_totals
from services.invoice_generator import generate_print_invoice_html, generate_web_invoice_html
from ui.status_styles import get_status_color
from ui.table_renderer import (
    create_table_item,
    set_status_styling,
    set_total_styling
)

class InvoicePreviewDialog(QDialog):
    """دیالوگ پیش‌نمایش و چاپ فاکتور"""
    
    def __init__(self, repair_data, parent=None):
        super().__init__(parent)
        self.repair_data = repair_data
        self.shop_settings = ShopSettingsDialog.get_settings()
        
        self.setWindowTitle("پیش‌نمایش فاکتور")
        self.setMinimumSize(900, 700)
        
        self.init_ui()
    
    def init_ui(self):
        """ایجاد رابط کاربری"""
        layout = QVBoxLayout()
        
        # انتخاب نوع فاکتور
        type_layout = QHBoxLayout()
        type_label = QLabel("نوع فاکتور:")
        type_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        
        self.type_group = QButtonGroup()
        self.print_radio = QRadioButton("چاپی (سیاه و سفید)")
        self.web_radio = QRadioButton("وب (رنگی)")
        
        self.type_group.addButton(self.print_radio)
        self.type_group.addButton(self.web_radio)
        self.print_radio.setChecked(True)
        
        self.print_radio.toggled.connect(self.update_preview)
        
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.print_radio)
        type_layout.addWidget(self.web_radio)
        type_layout.addStretch()
        
        layout.addLayout(type_layout)
        
        # پیش‌نمایش
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        layout.addWidget(self.preview)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        
        print_btn = QPushButton("چاپ")
        print_btn.setIcon(self.style().standardIcon(self.style().SP_FileDialogDetailedView))
        print_btn.clicked.connect(self.print_invoice)
        
        save_btn = QPushButton("ذخیره PDF")
        save_btn.clicked.connect(self.save_pdf)
        
        close_btn = QPushButton("بستن")
        close_btn.clicked.connect(self.close)
        
        btn_layout.addWidget(print_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
        # نمایش پیش‌نمایش اولیه
        self.update_preview()

    def print_invoice(self):
        """چاپ فاکتور"""
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        
        if dialog.exec_() == QDialog.Accepted:
            self.preview.document().print_(printer)
    
    def save_pdf(self):
        """ذخیره به صورت PDF"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره PDF",
            f"invoice_{self.repair_data.get('id', 'new')}.pdf",
            "PDF Files (*.pdf)"
        )
        
        if file_path:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            self.preview.document().print_(printer)
            QMessageBox.information(self, "موفق", "فایل PDF با موفقیت ذخیره شد.")

    def update_preview(self):
        """به‌روزرسانی پیش‌نمایش فاکتور"""
        if self.print_radio.isChecked():
            html = generate_print_invoice_html(self.repair_data, self.shop_settings)
        else:
            html = generate_web_invoice_html(self.repair_data, self.shop_settings)
        
        self.preview.setHtml(html)


class ShopSettingsDialog(QDialog):
    """دیالوگ تنظیمات فروشگاه"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تنظیمات فروشگاه")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.logo_path = ""
        
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """ایجاد رابط کاربری"""
        layout = QVBoxLayout()
        
        # عنوان
        title = QLabel("تنظیمات اطلاعات فروشگاه")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # فرم
        form_layout = QGridLayout()
        
        # نام فروشگاه
        form_layout.addWidget(QLabel("نام فروشگاه:"), 0, 0)
        self.shop_name_input = QLineEdit()
        self.shop_name_input.setPlaceholderText("نام فروشگاه خود را وارد کنید")
        form_layout.addWidget(self.shop_name_input, 0, 1)
        
        # آدرس
        form_layout.addWidget(QLabel("آدرس:"), 1, 0)
        self.address_input = QTextEdit()
        self.address_input.setMaximumHeight(60)
        self.address_input.setPlaceholderText("آدرس کامل فروشگاه")
        form_layout.addWidget(self.address_input, 1, 1)
        
        # تلفن
        form_layout.addWidget(QLabel("تلفن:"), 2, 0)
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("شماره تماس")
        form_layout.addWidget(self.phone_input, 2, 1)
        
        # موبایل
        form_layout.addWidget(QLabel("موبایل:"), 3, 0)
        self.mobile_input = QLineEdit()
        self.mobile_input.setPlaceholderText("شماره موبایل")
        form_layout.addWidget(self.mobile_input, 3, 1)
        
        # ایمیل
        form_layout.addWidget(QLabel("ایمیل:"), 4, 0)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("آدرس ایمیل")
        form_layout.addWidget(self.email_input, 4, 1)
        
        # وبسایت
        form_layout.addWidget(QLabel("وبسایت:"), 5, 0)
        self.website_input = QLineEdit()
        self.website_input.setPlaceholderText("آدرس وبسایت")
        form_layout.addWidget(self.website_input, 5, 1)
        
        # لوگو
        form_layout.addWidget(QLabel("لوگو:"), 6, 0)
        logo_layout = QHBoxLayout()
        self.logo_label = QLabel("لوگویی انتخاب نشده")
        self.logo_label.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 3px;")
        logo_btn = QPushButton("انتخاب لوگو")
        logo_btn.clicked.connect(self.select_logo)
        logo_layout.addWidget(self.logo_label, 1)
        logo_layout.addWidget(logo_btn)
        form_layout.addLayout(logo_layout, 6, 1)
        
        layout.addLayout(form_layout)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("ذخیره")
        cancel_btn = QPushButton("انصراف")
        
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px 20px; font-weight: bold;")
        cancel_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px 20px;")
        
        save_btn.clicked.connect(self.save_settings)
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def select_logo(self):
        """انتخاب فایل لوگو"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "انتخاب لوگو",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_path:
            self.logo_path = file_path
            self.logo_label.setText(Path(file_path).name)
    
    def load_settings(self):
        """بارگذاری تنظیمات"""
        try:
            if Path("shop_settings.json").exists():
                with open("shop_settings.json", "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    
                self.shop_name_input.setText(settings.get("shop_name", ""))
                self.address_input.setText(settings.get("address", ""))
                self.phone_input.setText(settings.get("phone", ""))
                self.mobile_input.setText(settings.get("mobile", ""))
                self.email_input.setText(settings.get("email", ""))
                self.website_input.setText(settings.get("website", ""))
                
                logo = settings.get("logo", "")
                if logo:
                    self.logo_path = logo
                    self.logo_label.setText(Path(logo).name if Path(logo).exists() else "فایل یافت نشد")
        except Exception as e:
            print(f"خطا در بارگذاری تنظیمات: {e}")
    
    def save_settings(self):
        """ذخیره تنظیمات"""
        settings = {
            "shop_name": self.shop_name_input.text(),
            "address": self.address_input.toPlainText(),
            "phone": self.phone_input.text(),
            "mobile": self.mobile_input.text(),
            "email": self.email_input.text(),
            "website": self.website_input.text(),
            "logo": self.logo_path
        }
        
        try:
            with open("shop_settings.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
            
            QMessageBox.information(self, "موفق", "تنظیمات با موفقیت ذخیره شد.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در ذخیره تنظیمات: {e}")
    
    @staticmethod
    def get_settings():
        """دریافت تنظیمات فروشگاه"""
        default_settings = {
            "shop_name": "تعمیرگاه لپ‌تاپ",
            "address": "آدرس فروشگاه",
            "phone": "021-12345678",
            "mobile": "0912-1234567",
            "email": "info@shop.com",
            "website": "www.shop.com",
            "logo": ""
        }
        
        try:
            if Path("shop_settings.json").exists():
                with open("shop_settings.json", "r", encoding="utf-8") as f:
                    return json.load(f)
        except:
            pass
        return default_settings

class NotificationDialog(QDialog):
    """دیالوگ نمایش اعلان‌ها"""
    
    def __init__(self, notifications, parent=None):
        super().__init__(parent)
        self.setWindowTitle("اعلان‌ها")
        self.setModal(True)
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        
        title = QLabel("یادآوری تعمیرات")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        for notif in notifications:
            frame = QFrame()
            frame.setFrameShape(QFrame.Box)
            frame.setStyleSheet("padding: 10px; margin: 5px; border-radius: 5px;")
            
            notif_layout = QVBoxLayout()
            
            message = QLabel(notif)
            message.setWordWrap(True)
            message.setStyleSheet("font-size: 11pt;")
            notif_layout.addWidget(message)
            
            frame.setLayout(notif_layout)
            layout.addWidget(frame)
        
        close_btn = QPushButton("بستن")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)

class RepairDialog(QDialog):
    """دیالوگ افزودن/ویرایش تعمیر"""
    
    def __init__(self, repair_data=None, parent=None):
        super().__init__(parent)
        self.repair_data = repair_data
        
        self.setWindowTitle("ثبت/ویرایش تعمیر")
        self.setModal(True)
        self.setMinimumSize(700, 600)
        
        self.init_ui()
        
        if repair_data:
            self.load_data(repair_data)
        else:
            self.calculate_total(0)
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        tabs = QTabWidget()
        
        # تب اطلاعات اصلی
        main_tab = QWidget()
        main_layout = QGridLayout()
        
        main_layout.addWidget(QLabel("نام مشتری:"), 0, 0)
        self.customer_name_input = QLineEdit()
        main_layout.addWidget(self.customer_name_input, 0, 1)
        
        main_layout.addWidget(QLabel("تلفن:"), 1, 0)
        self.phone_input = QLineEdit()
        main_layout.addWidget(self.phone_input, 1, 1)
        
        main_layout.addWidget(QLabel("برند:"), 2, 0)
        self.brand_input = QLineEdit()
        main_layout.addWidget(self.brand_input, 2, 1)
        
        main_layout.addWidget(QLabel("مدل:"), 3, 0)
        self.model_input = QLineEdit()
        main_layout.addWidget(self.model_input, 3, 1)
        
        main_layout.addWidget(QLabel("ایراد:"), 4, 0)
        self.issue_input = QTextEdit()
        self.issue_input.setMaximumHeight(80)
        main_layout.addWidget(self.issue_input, 4, 1)
        
        main_layout.addWidget(QLabel("وضعیت:"), 5, 0)
        self.status_input = QComboBox()
        self.status_input.addItems(ALL_STATUSES)
        main_layout.addWidget(self.status_input, 5, 1)
        
        main_layout.addWidget(QLabel("تاریخ دریافت:"), 6, 0)
        self.receive_date_input = PersianDateEdit()
        main_layout.addWidget(self.receive_date_input, 6, 1)
        
        main_layout.addWidget(QLabel("تاریخ تحویل:"), 7, 0)
        self.delivery_date_input = PersianDateEdit()
        main_layout.addWidget(self.delivery_date_input, 7, 1)
        
        main_tab.setLayout(main_layout)
        
        # تب مالی
        financial_tab = QWidget()
        financial_layout = QGridLayout()
        
        financial_layout.addWidget(QLabel("هزینه قطعات:"), 0, 0)
        self.parts_cost_input = QSpinBox()
        self.parts_cost_input.setMaximum(999999999)
        self.parts_cost_input.valueChanged.connect(self.calculate_total)
        financial_layout.addWidget(self.parts_cost_input, 0, 1)
        
        financial_layout.addWidget(QLabel("هزینه تعمیر:"), 1, 0)
        self.labor_cost_input = QSpinBox()
        self.labor_cost_input.setMaximum(999999999)
        self.labor_cost_input.valueChanged.connect(self.calculate_total)
        financial_layout.addWidget(self.labor_cost_input, 1, 1)
        
        financial_layout.addWidget(QLabel("مالیات (%):"), 2, 0)
        self.tax_input = QDoubleSpinBox()
        self.tax_input.setMaximum(100)
        self.tax_input.valueChanged.connect(self.calculate_total)
        financial_layout.addWidget(self.tax_input, 2, 1)
        
        financial_layout.addWidget(QLabel("تخفیف:"), 3, 0)
        self.discount_input = QSpinBox()
        self.discount_input.setMaximum(999999999)
        self.discount_input.valueChanged.connect(self.calculate_total)
        financial_layout.addWidget(self.discount_input, 3, 1)
        
        financial_layout.addWidget(QLabel("مجموع:"), 4, 0)
        self.total_label = QLabel("0 تومان")
        self.total_label.setStyleSheet("font-weight: bold; color: green; font-size: 12pt;")
        financial_layout.addWidget(self.total_label, 4, 1)
        
        financial_tab.setLayout(financial_layout)

        # تب یادداشت و گارانتی
        notes_tab = QWidget()
        notes_layout = QGridLayout()
        
        notes_layout.addWidget(QLabel("یادداشت‌ها:"), 0, 0)
        self.notes_input = QTextEdit()
        notes_layout.addWidget(self.notes_input, 0, 1)
        
        notes_layout.addWidget(QLabel("گارانتی:"), 1, 0)
        self.warranty_input = QTextEdit()
        self.warranty_input.setMaximumHeight(80)
        notes_layout.addWidget(self.warranty_input, 1, 1)
        
        notes_tab.setLayout(notes_layout)
        
        tabs.addTab(main_tab, "اطلاعات اصلی")
        tabs.addTab(financial_tab, "اطلاعات مالی")
        tabs.addTab(notes_tab, "یادداشت و گارانتی")
        
        layout.addWidget(tabs)
        
        # دکمه‌ها
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("ذخیره")
        cancel_btn = QPushButton("انصراف")
        
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def calculate_total(self, value):
        """محاسبه مجموع هزینه‌ها"""
        data = {
            'parts_cost': self.parts_cost_input.value(),
            'labor_cost': self.labor_cost_input.value(),
            'tax': self.tax_input.value(),
            'discount': self.discount_input.value(),
        }
        fin = calculate_invoice_totals(data)
        self.total_label.setText(f"{int(fin['total']):,} تومان")
    
    def load_data(self, data):
        """بارگذاری داده‌ها"""
        self.customer_name_input.setText(data.get('customer_name', ''))
        self.phone_input.setText(data.get('phone', ''))
        self.brand_input.setText(data.get('brand', ''))
        self.model_input.setText(data.get('model', ''))
        self.issue_input.setText(data.get('issue', ''))
        self.status_input.setCurrentText(data.get('status', STATUS_PENDING))
        self.receive_date_input.setText(data.get('receive_date', ''))
        self.delivery_date_input.setText(data.get('delivery_date', ''))
        self.parts_cost_input.setValue(data.get('parts_cost', 0))
        self.labor_cost_input.setValue(data.get('labor_cost', 0))
        self.tax_input.setValue(data.get('tax', 0))
        self.discount_input.setValue(data.get('discount', 0))
        self.notes_input.setText(data.get('notes', ''))
        self.warranty_input.setText(data.get('warranty', ''))
        self.calculate_total(0)
    
    def get_data(self):
        """دریافت داده‌ها"""
        return {
            'customer_name': self.customer_name_input.text(),
            'phone': self.phone_input.text(),
            'brand': self.brand_input.text(),
            'model': self.model_input.text(),
            'issue': self.issue_input.toPlainText(),
            'status': self.status_input.currentText(),
            'receive_date': self.receive_date_input.get_date(),
            'delivery_date': self.delivery_date_input.get_date(),
            'parts_cost': self.parts_cost_input.value(),
            'labor_cost': self.labor_cost_input.value(),
            'tax': self.tax_input.value(),
            'discount': self.discount_input.value(),
            'notes': self.notes_input.toPlainText(),
            'warranty': self.warranty_input.toPlainText()
        }

class LaptopRepairManager(QMainWindow):
    """کلاس اصلی برنامه مدیریت تعمیرات"""
    
    def __init__(self):
        super().__init__()
        self.storage = RepairsStorage()
        self.repairs = []
        self.load_data()
        self.init_ui()
        self.refresh_table()  # پر کردن جدول با داده‌های بارگذاری شده
        self.check_notifications()
    
    def init_ui(self):
        """ایجاد رابط کاربری"""
        self.setWindowTitle("سیستم مدیریت تعمیرات لپ‌تاپ")
        self.setGeometry(100, 100, 1200, 700)
        
        # ویجت مرکزی
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # لایه اصلی
        main_layout = QVBoxLayout()
        
        # هدر
        header = self.create_header()
        main_layout.addWidget(header)
        
        # نوار ابزار
        toolbar = self.create_toolbar()
        main_layout.addWidget(toolbar)
        
        # جدول
        self.table = self.create_table()
        main_layout.addWidget(self.table)
        
        # نوار وضعیت
        self.status_bar = self.create_status_bar()
        main_layout.addWidget(self.status_bar)
        
        central_widget.setLayout(main_layout)
        
        # استایل کلی
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QPushButton {
                padding: 8px 15px;
                border-radius: 5px;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton:hover {
                opacity: 0.8;
            }
            QTableWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QHeaderView::section {
                background-color: #667eea;
                color: white;
                padding: 10px;
                font-weight: bold;
                border: none;
            }
        """)
    
    def create_header(self):
        """ایجاد هدر"""
        header = QFrame()
        header.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                       stop:0 #667eea, stop:1 #764ba2);
            border-radius: 10px;
            padding: 20px;
        """)
        
        layout = QHBoxLayout()
        
        title = QLabel("🔧 سیستم مدیریت تعمیرات لپ‌تاپ")
        title.setStyleSheet("color: white; font-size: 20pt; font-weight: bold;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # دکمه تنظیمات فروشگاه
        settings_btn = QPushButton("⚙️ تنظیمات فروشگاه")
        settings_btn.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.2);
            color: white;
            border: 2px solid white;
        """)
        settings_btn.clicked.connect(self.open_shop_settings)
        layout.addWidget(settings_btn)
        
        header.setLayout(layout)
        return header
    
    def create_toolbar(self):
        """ایجاد نوار ابزار"""
        toolbar = QFrame()
        toolbar.setStyleSheet("background-color: white; border-radius: 5px; padding: 10px;")
        
        layout = QHBoxLayout()
        
        # دکمه افزودن
        add_btn = QPushButton("➕ افزودن تعمیر")
        add_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        add_btn.clicked.connect(self.add_repair)
        layout.addWidget(add_btn)
        
        # دکمه ویرایش
        edit_btn = QPushButton("✏️ ویرایش")
        edit_btn.setStyleSheet("background-color: #2196F3; color: white;")
        edit_btn.clicked.connect(self.edit_repair)
        layout.addWidget(edit_btn)
        
        # دکمه حذف
        delete_btn = QPushButton("🗑️ حذف")
        delete_btn.setStyleSheet("background-color: #f44336; color: white;")
        delete_btn.clicked.connect(self.delete_repair)
        layout.addWidget(delete_btn)
        
        # دکمه پیش‌نمایش فاکتور
        invoice_btn = QPushButton("📄 پیش‌نمایش فاکتور")
        invoice_btn.setStyleSheet("background-color: #FF9800; color: white;")
        invoice_btn.clicked.connect(self.preview_invoice)
        layout.addWidget(invoice_btn)
        
        layout.addStretch()
        
        # جستجو
        search_label = QLabel("🔍 جستجو:")
        layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("نام، تلفن، برند یا مدل...")
        self.search_input.setMinimumWidth(250)
        self.search_input.textChanged.connect(self.search_repairs)
        layout.addWidget(self.search_input)
        
        # فیلتر وضعیت
        filter_label = QLabel("فیلتر:")
        layout.addWidget(filter_label)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(ALL_STATUSES_WITH_ALL)
        self.filter_combo.currentTextChanged.connect(self.filter_repairs)
        layout.addWidget(self.filter_combo)
        
        toolbar.setLayout(layout)
        return toolbar

    def create_table(self):
        """ایجاد جدول"""
        table = QTableWidget()
        table.setColumnCount(11)
        table.setHorizontalHeaderLabels([
            "شناسه", "نام مشتری", "تلفن", "برند", "مدل", 
            "ایراد", "وضعیت", "تاریخ دریافت", "تاریخ تحویل", 
            "هزینه کل", "عملیات"
        ])
        
        # تنظیمات جدول
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        
        # تنظیم عرض ستون‌ها
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(10, QHeaderView.ResizeToContents)
        
        # دابل کلیک برای ویرایش
        table.doubleClicked.connect(self.edit_repair)
        
        return table
    
    def create_status_bar(self):
        """ایجاد نوار وضعیت"""
        status_bar = QFrame()
        status_bar.setStyleSheet("background-color: white; border-radius: 5px; padding: 10px;")
        
        layout = QHBoxLayout()
        
        self.total_label = QLabel("تعداد کل: 0")
        self.total_label.setStyleSheet("font-weight: bold; color: #333;")
        layout.addWidget(self.total_label)
        
        layout.addWidget(QLabel("|"))
        
        self.pending_label = QLabel(f"{STATUS_PENDING}: 0")
        self.pending_label.setStyleSheet(f"color: {STATUS_FG_COLORS[STATUS_PENDING]}; font-weight: bold;")
        layout.addWidget(self.pending_label)
        
        layout.addWidget(QLabel("|"))
        
        self.in_progress_label = QLabel(f"{STATUS_IN_PROGRESS}: 0")
        self.in_progress_label.setStyleSheet(f"color: {STATUS_FG_COLORS[STATUS_IN_PROGRESS]}; font-weight: bold;")
        layout.addWidget(self.in_progress_label)
        
        layout.addWidget(QLabel("|"))
        
        self.completed_label = QLabel(f"{STATUS_COMPLETED}: 0")
        self.completed_label.setStyleSheet(f"color: {STATUS_FG_COLORS[STATUS_COMPLETED]}; font-weight: bold;")
        layout.addWidget(self.completed_label)
        
        layout.addWidget(QLabel("|"))
        
        self.delivered_label = QLabel(f"{STATUS_DELIVERED}: 0")
        self.delivered_label.setStyleSheet(f"color: {STATUS_FG_COLORS[STATUS_DELIVERED]}; font-weight: bold;")
        layout.addWidget(self.delivered_label)
        
        layout.addStretch()
        
        self.date_label = QLabel()
        self.update_date_label()
        layout.addWidget(self.date_label)
        
        status_bar.setLayout(layout)
        return status_bar
    
    def update_date_label(self):
        """به‌روزرسانی تاریخ"""
        self.date_label.setText(f"📅 {today_persian()}")
        
        # تایمر برای به‌روزرسانی روزانه
        QTimer.singleShot(60000, self.update_date_label)
    
    def open_shop_settings(self):
        """باز کردن تنظیمات فروشگاه"""
        dialog = ShopSettingsDialog(self)
        dialog.exec_()
    
    def add_repair(self):
        """افزودن تعمیر جدید"""
        dialog = RepairDialog(parent=self)

        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            
            # استفاده از سرویس برای افزودن تعمیر
            self.repairs = add_repair(self.repairs, data)
            
            self.save_data()
            self.refresh_table()

            QMessageBox.information(self, "موفق", "تعمیر با موفقیت ثبت شد.")

    def edit_repair(self):
        """ویرایش تعمیر"""
        selected_row = self.table.currentRow()
        
        if selected_row < 0:
            QMessageBox.warning(self, "هشدار", "لطفاً یک ردیف را انتخاب کنید.")
            return
        
        repair_id = int(self.table.item(selected_row, 0).text())
        repair_data = get_repair_by_id(self.repairs, repair_id)
        
        if not repair_data:
            QMessageBox.critical(self, "خطا", "داده‌ای یافت نشد.")
            return
        
        dialog = RepairDialog(repair_data=repair_data, parent=self)
        
        if dialog.exec_() == QDialog.Accepted:
            updated_data = dialog.get_data()
            updated_data['id'] = repair_id
            
            # استفاده از سرویس برای به‌روزرسانی تعمیر
            self.repairs = update_repair(self.repairs, repair_id, updated_data)
            
            self.save_data()
            self.refresh_table()
            
            QMessageBox.information(self, "موفق", "تعمیر با موفقیت ویرایش شد.")
    
    def delete_repair(self):
        """حذف تعمیر"""
        selected_row = self.table.currentRow()
        
        if selected_row < 0:
            QMessageBox.warning(self, "هشدار", "لطفاً یک ردیف را انتخاب کنید.")
            return
        
        repair_id = int(self.table.item(selected_row, 0).text())
        customer_name = self.table.item(selected_row, 1).text()
        
        reply = QMessageBox.question(
            self,
            "تأیید حذف",
            f"آیا از حذف تعمیر '{customer_name}' اطمینان دارید؟",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # استفاده از سرویس برای حذف تعمیر
            self.repairs = delete_repair(self.repairs, repair_id)
            
            self.save_data()
            self.refresh_table()
            
            QMessageBox.information(self, "موفق", "تعمیر با موفقیت حذف شد.")
    
    def preview_invoice(self):
        """پیش‌نمایش فاکتور"""
        selected_row = self.table.currentRow()
        
        if selected_row < 0:
            QMessageBox.warning(self, "هشدار", "لطفاً یک ردیف را انتخاب کنید.")
            return
        
        repair_id = int(self.table.item(selected_row, 0).text())
        repair_data = get_repair_by_id(self.repairs, repair_id)
        
        if not repair_data:
            QMessageBox.critical(self, "خطا", "داده‌ای یافت نشد.")
            return
        
        dialog = InvoicePreviewDialog(repair_data, parent=self)
        dialog.exec_()
    
    def search_repairs(self, text):
        """جستجوی تعمیرات"""
        matching_indices = search_repairs(self.repairs, text)

        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row, row not in matching_indices)

    def filter_repairs(self, status):
        """فیلتر بر اساس وضعیت"""
        matching_indices = filter_repairs(self.repairs, status)

        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row, row not in matching_indices)
        
    def refresh_table(self):
        """به‌روزرسانی جدول"""
        # دریافت داده‌های آماده‌شده از سرویس
        rows_data = build_table_rows(self.repairs)
        
        # رندر تمام ردیف‌ها با استفاده از table renderer
        render_table_rows(self.table, rows_data, self.view_repair, self.quick_invoice)
        
        # به‌روزرسانی آمار
        self.update_statistics()
    
    def view_repair(self, row):
        """مشاهده جزئیات تعمیر"""
        self.table.selectRow(row)
        self.edit_repair()
    
    def quick_invoice(self, row):
        """فاکتور سریع"""
        self.table.selectRow(row)
        self.preview_invoice()

    def update_statistics(self):
        """به‌روزرسانی آمار"""
        total, pending, in_progress, completed, delivered = update_statistics(self.repairs)
        
        self.total_label.setText(f"تعداد کل: {total}")
        self.pending_label.setText(f"{STATUS_PENDING}: {pending}")
        self.in_progress_label.setText(f"{STATUS_IN_PROGRESS}: {in_progress}")
        self.completed_label.setText(f"{STATUS_COMPLETED}: {completed}")
        self.delivered_label.setText(f"{STATUS_DELIVERED}: {delivered}")
    
    def check_notifications(self):
        """بررسی یادآوری‌ها"""
        notifications = []
        today = jdatetime.date.today()
        
        for repair in self.repairs:
            if repair.get('status') in (STATUS_PENDING, STATUS_IN_PROGRESS):
                delivery_date_str = repair.get('delivery_date', '')
                
                if delivery_date_str:
                    try:
                        parts = delivery_date_str.split('/')
                        delivery_date = jdatetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
                        
                        days_diff = (delivery_date - today).days
                        
                        if days_diff < 0:
                            notifications.append(
                                f"⚠️ تعمیر '{repair.get('customer_name')}' از تاریخ تحویل گذشته است! ({abs(days_diff)} روز تأخیر)"
                            )
                        elif days_diff == 0:
                            notifications.append(
                                f"🔔 تعمیر '{repair.get('customer_name')}' امروز باید تحویل داده شود!"
                            )
                        elif days_diff <= 2:
                            notifications.append(
                                f"⏰ تعمیر '{repair.get('customer_name')}' {days_diff} روز دیگر باید تحویل داده شود."
                            )
                    except:
                        pass
        
        if notifications:
            dialog = NotificationDialog(notifications, self)
            dialog.exec_()

    def load_data(self):
        """بارگذاری داده‌ها از فایل"""
        try:
            self.repairs = self.storage.load_all()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در بارگذاری داده‌ها: {e}")
            self.repairs = []

    def save_data(self):
        """ذخیره داده‌ها در فایل"""
        try:
            self.storage.save_all(self.repairs)
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در ذخیره داده‌ها: {e}")

    def closeEvent(self, event):
        """رویداد بستن برنامه"""
        reply = QMessageBox.question(
            self, "خروج", "آیا از خروج از برنامه اطمینان دارید؟",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.save_data()
            event.accept()
        else:
            event.ignore()


def main():
    """تابع اصلی"""
    app = QApplication(sys.argv)

    # تنظیم فونت فارسی
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # تنظیم راست‌چین
    app.setLayoutDirection(Qt.RightToLeft)

    # ایجاد و نمایش پنجره اصلی
    window = LaptopRepairManager()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
