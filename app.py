import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout,
                              QHBoxLayout, QPushButton, QTableWidgetItem,
                              QDialog, QLabel, QLineEdit, QTextEdit, QSpinBox,
                              QDoubleSpinBox, QCalendarWidget,
                              QTabWidget, QGridLayout,
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
from ui.dialogs.repair_dialog import RepairDialog
from ui.dialogs.invoice_dialog import InvoicePreviewDialog
from ui.main_window import build_ui
from services.notification_service import (
    show_info, show_warning, show_error, show_question
)


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
            
            show_info(self, "موفق", "تنظیمات با موفقیت ذخیره شد.")
            self.accept()
        except Exception as e:
            show_error(self, "خطا", f"خطا در ذخیره تنظیمات: {e}")
    
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
        build_ui(self)
    
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

            show_info(self, "موفق", "تعمیر با موفقیت ثبت شد.")

    def edit_repair(self):
        """ویرایش تعمیر"""
        selected_row = self.table.currentRow()
        
        if selected_row < 0:
            show_warning(self, "هشدار", "لطفاً یک ردیف را انتخاب کنید.")
            return
        
        repair_id = int(self.table.item(selected_row, 0).text())
        repair_data = get_repair_by_id(self.repairs, repair_id)
        
        if not repair_data:
            show_error(self, "خطا", "داده‌ای یافت نشد.")
            return
        
        dialog = RepairDialog(repair_data=repair_data, parent=self)
        
        if dialog.exec_() == QDialog.Accepted:
            updated_data = dialog.get_data()
            updated_data['id'] = repair_id
            
            # استفاده از سرویس برای به‌روزرسانی تعمیر
            self.repairs = update_repair(self.repairs, repair_id, updated_data)
            
            self.save_data()
            self.refresh_table()
            
            show_info(self, "موفق", "تعمیر با موفقیت ویرایش شد.")
    
    def delete_repair(self):
        """حذف تعمیر"""
        selected_row = self.table.currentRow()
        
        if selected_row < 0:
            show_warning(self, "هشدار", "لطفاً یک ردیف را انتخاب کنید.")
            return
        
        repair_id = int(self.table.item(selected_row, 0).text())
        customer_name = self.table.item(selected_row, 1).text()
        
        if show_question(self, "تأیید حذف", f"آیا از حذف تعمیر '{customer_name}' اطمینان دارید؟"):
            # استفاده از سرویس برای حذف تعمیر
            self.repairs = delete_repair(self.repairs, repair_id)
            
            self.save_data()
            self.refresh_table()
            
            show_info(self, "موفق", "تعمیر با موفقیت حذف شد.")
    
    def preview_invoice(self):
        """پیش‌نمایش فاکتور"""
        selected_row = self.table.currentRow()
        
        if selected_row < 0:
            show_warning(self, "هشدار", "لطفاً یک ردیف را انتخاب کنید.")
            return
        
        repair_id = int(self.table.item(selected_row, 0).text())
        repair_data = get_repair_by_id(self.repairs, repair_id)
        
        if not repair_data:
            show_error(self, "خطا", "داده‌ای یافت نشد.")
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
            show_error(self, "خطا", f"خطا در بارگذاری داده‌ها: {e}")
            self.repairs = []

    def save_data(self):
        """ذخیره داده‌ها در فایل"""
        try:
            self.storage.save_all(self.repairs)
        except Exception as e:
            show_error(self, "خطا", f"خطا در ذخیره داده‌ها: {e}")

    def closeEvent(self, event):
        """رویداد بستن برنامه"""
        if show_question(self, "خروج", "آیا از خروج از برنامه اطمینان دارید؟"):
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
