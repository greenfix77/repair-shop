import sys
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout,
                              QHBoxLayout, QPushButton, QDialog,
                              QLabel, QLineEdit, QFrame)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
import jdatetime

from core.status import (
    STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_COMPLETED, STATUS_DELIVERED,
    ALL_STATUSES, ALL_STATUSES_WITH_ALL,
    STATUS_COLORS, DEFAULT_STATUS_COLOR,
    STATUS_FG_COLORS
)
from repair_manager.ui.components import PersianCalendarWidget, PersianDateEdit
from core.storage.dual_storage import DualStorage
from services.statistics import update_statistics
from services.repair_manager_service import add_repair, delete_repair, get_repair_by_id, update_repair
from services.date_service import today_persian
from services.calculations import calculate_invoice
from services.invoice_calculator import calculate_invoice_totals
from services.invoice_generator import generate_print_invoice_html, generate_web_invoice_html
from ui.status_styles import get_status_color
from ui.dialogs.repair_dialog import RepairDialog
from ui.dialogs.invoice_dialog import InvoicePreviewDialog
from ui.main_window import build_ui
from controllers.main_controller import MainController
from services.notification_service import (
    show_info, show_warning, show_error, show_question
)
from ui.dialogs.shop_settings_dialog import ShopSettingsDialog


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
        self.storage = DualStorage()
        self.repairs = []
        self.controller = MainController()
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
        self.controller.search_repairs(self.table, self.repairs, text)

    def filter_repairs(self, status):
        """فیلتر بر اساس وضعیت"""
        self.controller.filter_repairs(self.table, self.repairs, status)
        
    def refresh_table(self):
        """به‌روزرسانی جدول"""
        self.controller.refresh_table(
            self.table, self.repairs,
            self.view_repair, self.quick_invoice,
            self.update_statistics,
        )
    
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
