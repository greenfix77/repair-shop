import sys
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout,
                              QHBoxLayout, QPushButton, QDialog,
                              QLabel, QLineEdit, QFrame, QScrollArea,
                              QWidget)
from PyQt5.QtCore import Qt, QTimer, QEvent, QPoint, QRect
from PyQt5.QtGui import QFont
import jdatetime

from core.status import (
    STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_COMPLETED, STATUS_DELIVERED,
    ALL_STATUSES, ALL_STATUSES_WITH_ALL,
    STATUS_COLORS, DEFAULT_STATUS_COLOR,
    STATUS_FG_COLORS
)
from repair_manager.ui.components import PersianCalendarWidget, PersianDateEdit
from core.storage.sqlite_storage import SQLiteStorage
from services.statistics import update_statistics
from services.repair_manager_service import add_repair, delete_repair, get_repair_by_id, update_repair
from services.customer_stats_service import compute_customer_repair_stats
from services.date_service import today_persian
from services.calculations import calculate_invoice
from services.invoice_calculator import calculate_invoice_totals
from services.invoice_generator import generate_print_invoice_html, generate_web_invoice_html
from ui.status_styles import get_status_color
from ui.dialogs.repair_dialog import RepairDialog
from ui.dialogs.invoice_dialog import InvoicePreviewDialog
from ui.dialogs.customer_edit_dialog import CustomerEditDialog
from ui.dialogs.service_edit_dialog import ServiceEditDialog
from ui.dialogs.part_edit_dialog import PartEditDialog
from ui.dialogs.todo_edit_dialog import TodoEditDialog
from ui.main_window import build_ui, build_header, create_status_popup
from ui.customer_view import render_customer_rows
from ui.service_view import render_service_rows
from ui.part_view import render_part_rows
from ui.todo_view import render_todo_rows
from controllers.main_controller import MainController
from services.customer_workflow import CustomerWorkflow
from services.service_service import ServiceService
from services.part_service import PartService
from services.todo_service import TodoService
from services.notification_service import (
    show_info, show_warning, show_error, show_question
)
from ui.dialogs.shop_settings_dialog import ShopSettingsDialog
from services.logo_service import get_app_icon


class NotificationDialog(QDialog):
    """دیالوگ نمایش اعلان‌ها"""
    
    def __init__(self, notifications, parent=None, todo_items=None, todo_sections=None):
        super().__init__(parent)
        self.setWindowTitle("اعلان‌ها")
        self.setModal(True)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumSize(500, 300)

        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("یادآوری تعمیرات")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        container.setLayoutDirection(Qt.RightToLeft)
        list_layout = QVBoxLayout(container)
        list_layout.setSpacing(3)
        list_layout.setContentsMargins(0, 0, 0, 0)

        for notif in notifications:
            frame = QFrame()
            frame.setFrameShape(QFrame.Box)
            frame.setStyleSheet(
                "padding: 4px 8px; margin: 1px; border-radius: 4px; "
                "background-color: #F9FAFB; border: 1px solid #E5E7EB;"
            )

            notif_layout = QVBoxLayout()
            notif_layout.setSpacing(0)
            notif_layout.setContentsMargins(0, 0, 0, 0)

            message = QLabel(notif)
            message.setWordWrap(True)
            message.setLayoutDirection(Qt.RightToLeft)
            message.setStyleSheet("font-size: 10pt; background: transparent; border: none;")
            notif_layout.addWidget(message)

            frame.setLayout(notif_layout)
            list_layout.addWidget(frame)

        sections_data = todo_sections if todo_sections is not None else (
            {"today": todo_items} if todo_items else None
        )

        # --- بخش وظایف ---
        if sections_data is not None:
            separator = QFrame()
            separator.setFixedHeight(1)
            separator.setStyleSheet("background-color: #E5E7EB; border: none; margin: 6px 0;")
            list_layout.addWidget(separator)

            section_specs = [
                ("overdue", "وظایف عقب‌افتاده", "#DC2626"),
                ("today", "وظایف امروز", "#D97706"),
                ("upcoming", "وظایف آینده", "#059669"),
            ]
            for key, header, color in section_specs:
                items = sections_data.get(key) or []
                if not items:
                    continue
                self._render_todo_section(list_layout, header, color, items)

        list_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        close_btn = QPushButton("بستن")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)

        # نمایش حدوداً ۵ مورد اول بدون اسکرول؛ موارد بیشتر با اسکرول
        item_height = 52
        todo_item_height = 56
        todos_section_title_space = 36
        if sections_data is not None:
            todo_total = sum(len(sections_data.get(k) or []) for k in ("overdue", "today", "upcoming"))
        else:
            todo_total = len(todo_items) if todo_items else 0
        total_counts = len(notifications) + todo_total
        button_space = 44
        extra_todo_space = todo_item_height * todo_total
        sec_title = todos_section_title_space if sections_data is not None or todo_items is not None else 0
        base = sec_title + button_space
        visible = min(total_counts, 5)
        preferred = base + visible * item_height + extra_todo_space
        self.resize(500, min(preferred, 600))

    def _render_todo_section(self, list_layout, header_text, header_color, items):
        """Render a single todo section (header + items)."""
        section_title = QLabel(header_text)
        section_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        section_title.setAlignment(Qt.AlignCenter)
        section_title.setStyleSheet(
            f"color: {header_color}; background: transparent; border: none; "
            "padding: 4px 0;"
        )
        list_layout.addWidget(section_title)

        priority_colors = {
            "فوری": "#DC2626",
            "زیاد": "#D97706",
            "معمولی": "#2563EB",
            "کم": "#6B7280",
        }
        priority_marks = {
            "فوری": "🔴",
            "زیاد": "🟠",
            "معمولی": "🔵",
            "کم": "⚪",
        }

        for t in items:
            priority = t.get('priority', 'معمولی')
            mark = priority_marks.get(priority, "⚪")
            color = priority_colors.get(priority, "#6B7280")
            title_text = t.get('title', '') or ''
            due = t.get('due_date', '') or ''

            line = QFrame()
            line.setFrameShape(QFrame.Box)
            line.setStyleSheet(
                "padding: 4px 8px; margin: 1px; border-radius: 4px; "
                "background-color: #FFFBEB; border: 1px solid #FDE68A;"
            )

            line_layout = QVBoxLayout()
            line_layout.setSpacing(0)
            line_layout.setContentsMargins(0, 0, 0, 0)

            head = QLabel(f"{mark} {title_text}")
            head.setWordWrap(True)
            head.setLayoutDirection(Qt.RightToLeft)
            head.setStyleSheet(
                "font-size: 10pt; font-weight: bold; "
                f"color: {color}; background: transparent; border: none;"
            )
            line_layout.addWidget(head)

            foot = QLabel(f"📅 سررسید: {due}   |   اولویت: {priority}")
            foot.setLayoutDirection(Qt.RightToLeft)
            foot.setStyleSheet(
                "font-size: 9pt; background: transparent; border: none; "
                f"color: #D97706;"
            )
            line_layout.addWidget(foot)

            line.setLayout(line_layout)
            list_layout.addWidget(line)


class LaptopRepairManager(QMainWindow):
    """کلاس اصلی برنامه مدیریت تعمیرات"""
    
    def __init__(self):
        super().__init__()
        self.storage = SQLiteStorage()
        self.repairs = []
        self.controller = MainController()
        self._customer_workflow = CustomerWorkflow()
        self._customer_stats = {}
        self._service_service = ServiceService()
        self._part_service = PartService()
        self._todo_service = TodoService()
        self.load_data()
        self.init_ui()
        self.refresh_table()  # پر کردن جدول با داده‌های بارگذاری شده
        self.check_notifications()
    
    def init_ui(self):
        """ایجاد رابط کاربری"""
        build_ui(self)
        QApplication.instance().installEventFilter(self)
    
    def update_date_label(self):
        """به‌روزرسانی تاریخ"""
        self.date_label.setText(f"📅 {today_persian()}")
        now = datetime.now()
        self.header_datetime_label.setText(f"📅 {today_persian()}\n🕒 {now.strftime('%H:%M')}")
        
        # تایمر برای به‌روزرسانی روزانه
        QTimer.singleShot(60000, self.update_date_label)
    
    def open_shop_settings(self):
        """باز کردن تنظیمات فروشگاه"""
        dialog = ShopSettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.rebuild_header()

    def rebuild_header(self):
        """بازسازی هدر پس از تغییر تنظیمات"""
        idx = self.main_layout.indexOf(self.header_widget)
        self.main_layout.removeWidget(self.header_widget)
        self.header_widget.deleteLater()
        self.status_popup.deleteLater()
        self.status_popup = create_status_popup(self)
        self.header_widget = build_header(self)
        self.main_layout.insertWidget(idx, self.header_widget)
        now = datetime.now()
        self.header_datetime_label.setText(f"{today_persian()}\n{now.strftime('%H:%M')}")

    def toggle_status_popup(self):
        """نمایش/پنهان کردن پاپ‌آپ وضعیت‌ها"""
        if self.status_popup.isVisible():
            self.status_popup.hide()
            return
        pos = self.status_btn.mapToGlobal(QPoint(0, self.status_btn.height()))
        self.status_popup.move(pos)
        self.status_popup.show()
        self.status_popup.raise_()

    def eventFilter(self, obj, event):
        """بستن پاپ‌آپ هنگام کلیک خارج از آن یا ESC"""
        if self.status_popup.isVisible():
            if event.type() == QEvent.MouseButtonPress:
                global_pos = event.globalPos()
                popup_rect = QRect(
                    self.status_popup.mapToGlobal(QPoint(0, 0)),
                    self.status_popup.size()
                )
                btn_rect = QRect(
                    self.status_btn.mapToGlobal(QPoint(0, 0)),
                    self.status_btn.size()
                )
                if not popup_rect.contains(global_pos) and not btn_rect.contains(global_pos):
                    self.status_popup.hide()
            if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
                self.status_popup.hide()
        return super().eventFilter(obj, event)
    
    def add_repair(self):
        """افزودن تعمیر جدید"""
        dialog = RepairDialog(parent=self)

        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            
            # استفاده از سرویس برای افزودن تعمیر
            self.repairs = add_repair(self.repairs, data)
            
            self.save_data()
            self.refresh_table()
            self._refresh_customer_table_if_visible()

            show_info(self, "موفق", "تعمیر با موفقیت ثبت شد.")

    def edit_repair(self):
        """ویرایش تعمیر"""
        selected_row = self.table.currentRow()
        
        if selected_row < 0:
            show_warning(self, "هشدار", "لطفاً یک ردیف را انتخاب کنید.")
            return
        
        repair_id = int(self.table.item(selected_row, 1).text())
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
            self._refresh_customer_table_if_visible()
            
            show_info(self, "موفق", "تعمیر با موفقیت ویرایش شد.")
    
    def delete_repair(self):
        """حذف تعمیر"""
        selected_row = self.table.currentRow()
        
        if selected_row < 0:
            show_warning(self, "هشدار", "لطفاً یک ردیف را انتخاب کنید.")
            return
        
        repair_id = int(self.table.item(selected_row, 1).text())
        customer_name = self.table.item(selected_row, 2).text()
        
        if show_question(self, "تأیید حذف", f"آیا از حذف تعمیر '{customer_name}' اطمینان دارید؟"):
            # استفاده از سرویس برای حذف تعمیر
            self.repairs = delete_repair(self.repairs, repair_id)
            
            self.save_data()
            self.refresh_table()
            self._refresh_customer_table_if_visible()
            
            show_info(self, "موفق", "تعمیر با موفقیت حذف شد.")
    
    def delete_selected_repairs(self):
        """حذف تعمیرات انتخاب‌شده (چک‌باکس‌دار) در یک عملیات"""
        table = self.table
        selected_ids = []
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item is not None and item.checkState() == Qt.Checked:
                rid = item.data(Qt.UserRole)
                if rid is not None:
                    selected_ids.append(rid)

        if not selected_ids:
            show_warning(self, "هشدار", "هیچ تعمیری انتخاب نشده است.")
            return

        if not show_question(
            self, "تأیید حذف",
            f"آیا از حذف {len(selected_ids)} تعمیر انتخاب‌شده اطمینان دارید؟"
        ):
            return

        id_set = set(selected_ids)
        self.repairs = [r for r in self.repairs if r.get('id') not in id_set]

        self.save_data()
        self.refresh_table()
        self._refresh_customer_table_if_visible()

        show_info(self, "موفق", f"{len(selected_ids)} تعمیر با موفقیت حذف شد.")
    
    def preview_invoice(self):
        """پیش‌نمایش فاکتور"""
        selected_row = self.table.currentRow()
        
        if selected_row < 0:
            show_warning(self, "هشدار", "لطفاً یک ردیف را انتخاب کنید.")
            return
        
        repair_id = int(self.table.item(selected_row, 1).text())
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

    # --- مدیریت مشتریان ---

    def show_repairs_view(self):
        """نمایش نمای تعمیرات"""
        self.view_stack.setCurrentIndex(0)
        self.repairs_nav_btn.setStyleSheet(
            "background-color: #4F46E5; color: white; font-weight: bold;"
        )
        self.customers_nav_btn.setStyleSheet(
            "background-color: #607D8B; color: white;"
        )
        self.services_nav_btn.setStyleSheet(
            "background-color: #607D8B; color: white;"
        )
        self.parts_nav_btn.setStyleSheet(
            "background-color: #607D8B; color: white;"
        )
        self.todos_nav_btn.setStyleSheet(
            "background-color: #607D8B; color: white;"
        )

    def show_customers_view(self):
        """نمایش نمای مشتریان"""
        self.view_stack.setCurrentIndex(1)
        self.repairs_nav_btn.setStyleSheet(
            "background-color: #607D8B; color: white;"
        )
        self.customers_nav_btn.setStyleSheet(
            "background-color: #4F46E5; color: white; font-weight: bold;"
        )
        self.services_nav_btn.setStyleSheet(
            "background-color: #607D8B; color: white;"
        )
        self.parts_nav_btn.setStyleSheet(
            "background-color: #607D8B; color: white;"
        )
        self.todos_nav_btn.setStyleSheet(
            "background-color: #607D8B; color: white;"
        )
        self.refresh_customer_table()

    # --- مدیریت خدمات ---

    def show_services_view(self):
        """نمایش نمای خدمات"""
        self.view_stack.setCurrentIndex(2)
        self.repairs_nav_btn.setStyleSheet(
            "background-color: #607D8B; color: white;"
        )
        self.customers_nav_btn.setStyleSheet(
            "background-color: #607D8B; color: white;"
        )
        self.services_nav_btn.setStyleSheet(
            "background-color: #4F46E5; color: white; font-weight: bold;"
        )
        self.parts_nav_btn.setStyleSheet(
            "background-color: #607D8B; color: white;"
        )
        self.todos_nav_btn.setStyleSheet(
            "background-color: #607D8B; color: white;"
        )
        self.refresh_service_table()

    # --- مدیریت قطعات ---

    def show_parts_view(self):
        """نمایش نمای قطعات"""
        self.view_stack.setCurrentIndex(3)
        self.repairs_nav_btn.setStyleSheet(
            "background-color: #607D8B; color: white;"
        )
        self.customers_nav_btn.setStyleSheet(
            "background-color: #607D8B; color: white;"
        )
        self.services_nav_btn.setStyleSheet(
            "background-color: #607D8B; color: white;"
        )
        self.parts_nav_btn.setStyleSheet(
            "background-color: #4F46E5; color: white; font-weight: bold;"
        )
        self.todos_nav_btn.setStyleSheet(
            "background-color: #607D8B; color: white;"
        )
        self.refresh_part_table()

    # --- مدیریت وظایف ---

    def show_todos_view(self):
        """نمایش نمای وظایف"""
        self.view_stack.setCurrentIndex(4)
        self.repairs_nav_btn.setStyleSheet(
            "background-color: #607D8B; color: white;"
        )
        self.customers_nav_btn.setStyleSheet(
            "background-color: #607D8B; color: white;"
        )
        self.services_nav_btn.setStyleSheet(
            "background-color: #607D8B; color: white;"
        )
        self.parts_nav_btn.setStyleSheet(
            "background-color: #607D8B; color: white;"
        )
        self.todos_nav_btn.setStyleSheet(
            "background-color: #4F46E5; color: white; font-weight: bold;"
        )
        self.refresh_todo_table()

    def refresh_todo_table(self):
        """بارگذاری و نمایش لیست وظایف"""
        todos = self._todo_service.list_all()
        render_todo_rows(self.todo_table, todos, self.edit_todo)

    def search_todos(self, text):
        """جستجوی وظایف"""
        results = self._todo_service.search(text)
        render_todo_rows(self.todo_table, results, self.edit_todo)

    def add_todo(self):
        """افزودن وظیفه جدید"""
        dialog = TodoEditDialog(todo_id=None, parent=self)
        if getattr(dialog, '_init_failed', False):
            return
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_todo_table()

    def edit_todo(self, todo_id):
        """ویرایش یک وظیفه از طریق دیالوگ اختصاصی"""
        if todo_id is None:
            return
        dialog = TodoEditDialog(todo_id, parent=self)
        if getattr(dialog, '_init_failed', False):
            return
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_todo_table()

    def toggle_selected_todo_done(self):
        """تغییر وضعیت انجام‌شدن وظایف انتخاب‌شده (انجام شد / بازگردانی)"""
        table = self.todo_table
        selected_ids = []
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item is not None and item.checkState() == Qt.Checked:
                tid = item.data(Qt.UserRole)
                if tid is not None:
                    selected_ids.append(tid)

        if not selected_ids:
            show_warning(self, "هشدار", "هیچ وظیفه‌ای انتخاب نشده است.")
            return

        toggled = 0
        for tid in selected_ids:
            current = self._todo_service.get_todo(tid)
            if not current:
                continue
            if current.get('is_done'):
                self._todo_service.mark_pending(tid)
            else:
                self._todo_service.mark_done(tid)
            toggled += 1

        self.refresh_todo_table()
        if toggled > 0:
            show_info(self, "موفق", f"وضعیت {toggled} وظیفه با موفقیت تغییر کرد.")

    def delete_selected_todos(self):
        """حذف وظایف انتخاب‌شده"""
        table = self.todo_table
        selected_ids = []
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item is not None and item.checkState() == Qt.Checked:
                tid = item.data(Qt.UserRole)
                if tid is not None:
                    selected_ids.append(tid)

        if not selected_ids:
            show_warning(self, "هشدار", "هیچ وظیفه‌ای انتخاب نشده است.")
            return

        if not show_question(
            self, "تأیید حذف",
            f"آیا از حذف {len(selected_ids)} وظیفه انتخاب‌شده اطمینان دارید؟"
        ):
            return

        deleted = 0
        for tid in selected_ids:
            try:
                if self._todo_service.delete_todo(tid):
                    deleted += 1
            except Exception as e:
                show_error(self, "خطا", f"حذف وظیفه ناموفق بود: {e}")
                break

        self.refresh_todo_table()
        if deleted > 0:
            show_info(self, "موفق", f"{deleted} وظیفه با موفقیت حذف شد.")

    def refresh_part_table(self):
        """بارگذاری و نمایش لیست قطعات مرتب شده بر اساس نام"""
        parts = self._part_service.list_all()
        render_part_rows(self.part_table, parts, self.edit_part)

    def search_parts(self, text):
        """جستجوی قطعات"""
        results = self._part_service.search(text)
        render_part_rows(self.part_table, results, self.edit_part)

    def add_part(self):
        """افزودن قطعه جدید"""
        dialog = PartEditDialog(part_id=None, parent=self)
        if getattr(dialog, '_init_failed', False):
            return
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_part_table()

    def edit_part(self, part_id):
        """ویرایش یک قطعه از طریق دیالوگ اختصاصی"""
        if part_id is None:
            return
        dialog = PartEditDialog(part_id, parent=self)
        if getattr(dialog, '_init_failed', False):
            return
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_part_table()

    def delete_selected_parts(self):
        """حذف قطعات انتخاب‌شده"""
        table = self.part_table
        selected_ids = []
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item is not None and item.checkState() == Qt.Checked:
                pid = item.data(Qt.UserRole)
                if pid is not None:
                    selected_ids.append(pid)

        if not selected_ids:
            show_warning(self, "هشدار", "هیچ قطعه‌ای انتخاب نشده است.")
            return

        if not show_question(
            self, "تأیید حذف",
            f"آیا از حذف {len(selected_ids)} قطعه انتخاب‌شده اطمینان دارید؟"
        ):
            return

        deleted = 0
        for pid in selected_ids:
            try:
                if self._part_service.delete_part(pid):
                    deleted += 1
            except Exception as e:
                show_error(self, "خطا", f"حذف قطعه ناموفق بود: {e}")
                break

        self.refresh_part_table()
        if deleted > 0:
            show_info(self, "موفق", f"{deleted} قطعه با موفقیت حذف شد.")

    def refresh_service_table(self):
        """بارگذاری و نمایش لیست خدمات مرتب شده بر اساس نام"""
        services = self._service_service.list_all()
        render_service_rows(self.service_table, services, self.edit_service)

    def search_services(self, text):
        """جستجوی خدمات"""
        results = self._service_service.search(text)
        render_service_rows(self.service_table, results, self.edit_service)

    def add_service(self):
        """افزودن خدمت جدید"""
        dialog = ServiceEditDialog(service_id=None, parent=self)
        if getattr(dialog, '_init_failed', False):
            return
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_service_table()

    def edit_service(self, service_id):
        """ویرایش یک خدمت از طریق دیالوگ اختصاصی"""
        if service_id is None:
            return
        dialog = ServiceEditDialog(service_id, parent=self)
        if getattr(dialog, '_init_failed', False):
            return
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_service_table()

    def delete_selected_services(self):
        """حذف خدمات انتخاب‌شده"""
        table = self.service_table
        selected_ids = []
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item is not None and item.checkState() == Qt.Checked:
                sid = item.data(Qt.UserRole)
                if sid is not None:
                    selected_ids.append(sid)

        if not selected_ids:
            show_warning(self, "هشدار", "هیچ خدمتی انتخاب نشده است.")
            return

        if not show_question(
            self, "تأیید حذف",
            f"آیا از حذف {len(selected_ids)} خدمت انتخاب‌شده اطمینان دارید؟"
        ):
            return

        deleted = 0
        for sid in selected_ids:
            try:
                if self._service_service.delete_service(sid):
                    deleted += 1
            except Exception as e:
                show_error(self, "خطا", f"حذف خدمت ناموفق بود: {e}")
                break

        self.refresh_service_table()
        if deleted > 0:
            show_info(self, "موفق", f"{deleted} خدمت با موفقیت حذف شد.")

    def refresh_customer_table(self):
        """بارگذاری و نمایش لیست مشتریان مرتب شده بر اساس نام"""
        customers = self._customer_workflow.get_all_customers()
        stats = compute_customer_repair_stats(self.repairs, customers)
        render_customer_rows(self.customer_table, customers, self.edit_customer, stats)
        self._customer_stats = stats

    def _refresh_customer_table_if_visible(self):
        """به‌روزرسانی جدول مشتریان در صورت نمایش نمای مشتریان"""
        if hasattr(self, 'view_stack') and self.view_stack.currentIndex() == 1:
            self.refresh_customer_table()

    def add_customer(self):
        """افزودن مشتری جدید از طریق دیالوگ اختصاصی"""
        dialog = CustomerEditDialog(customer_id=None, parent=self)
        if getattr(dialog, '_init_failed', False):
            return
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_customer_table()

    def edit_customer(self, customer_id):
        """ویرایش یک مشتری از طریق دیالوگ اختصاصی"""
        if customer_id is None:
            return
        dialog = CustomerEditDialog(customer_id, parent=self)
        if getattr(dialog, '_init_failed', False):
            return
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_customer_table()

    def _has_related_repairs(self, customer):
        """بررسی وجود تعمیر مرتبط برای یک مشتری"""
        name = (customer.get('full_name') or '').strip()
        phone = (customer.get('phone') or '').strip()
        for r in self.repairs:
            if phone and r.get('phone', '').strip() == phone:
                return True
            if name and r.get('customer_name', '').strip() == name:
                return True
        return False

    def delete_selected_customers(self):
        """حذف مشتریان انتخاب‌شده با احتیاط"""
        table = self.customer_table
        selected_ids = []
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item is not None and item.checkState() == Qt.Checked:
                cid = item.data(Qt.UserRole)
                if cid is not None:
                    selected_ids.append(cid)

        if not selected_ids:
            show_warning(self, "هشدار", "هیچ مشتری انتخاب نشده است.")
            return

        customers = self._customer_workflow.get_all_customers()
        by_id = {c.get('id'): c for c in customers}

        blocked = []
        safe = []
        for cid in selected_ids:
            c = by_id.get(cid)
            if c is None:
                continue
            if self._has_related_repairs(c):
                blocked.append(c)
            else:
                safe.append(c)

        if blocked:
            names = '\n'.join(
                c.get('full_name', '') or '(بی‌نام)' for c in blocked
            )
            show_warning(
                self, "حذف ممکن نیست",
                "مشتریان زیر دارای تعمیر مرتبط هستند و حذف نمی‌شوند:\n\n"
                f"{names}\n\n"
                "برای حذف این مشتریان ابتدا تعمیرات مرتبط را حذف کنید."
            )

        if not safe:
            return

        if not show_question(
            self, "تأیید حذف",
            f"آیا از حذف {len(safe)} مشتری انتخاب‌شده اطمینان دارید؟"
        ):
            return

        deleted = 0
        for c in safe:
            try:
                if self._customer_workflow.delete_customer(c.get('id')):
                    deleted += 1
            except Exception as e:
                show_error(self, "خطا", f"حذف مشتری ناموفق بود: {e}")
                break

        self.refresh_customer_table()
        if deleted > 0:
            show_info(self, "موفق", f"{deleted} مشتری با موفقیت حذف شد.")

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
        
        self.header_pending_count.setText(str(pending))
        self.header_in_progress_count.setText(str(in_progress))
        self.header_completed_count.setText(str(completed))
        self.header_delivered_count.setText(str(delivered))
    
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

        today_str = today_persian().strip()
        today_date = jdatetime.date.today()
        overdue_items = []
        today_items = []
        upcoming_items = []
        try:
            for t in self._todo_service.get_pending():
                due = (t.get('due_date', '') or '').strip()
                if not due:
                    continue
                try:
                    y, m, d = (int(x) for x in due.split('/'))
                    due_d = jdatetime.date(y, m, d)
                except Exception:
                    continue
                delta = (due_d - today_date).days
                if delta < 0:
                    overdue_items.append(t)
                elif delta == 0:
                    today_items.append(t)
                elif 0 < delta <= 3:
                    upcoming_items.append(t)
        except Exception:
            pass

        for bucket in (overdue_items, today_items, upcoming_items):
            bucket.sort(key=lambda x: (x.get('due_date', '') or '').strip())

        todo_sections = {
            "overdue": overdue_items,
            "today": today_items,
            "upcoming": upcoming_items,
        }

        if notifications or any(todo_sections.values()):
            dialog = NotificationDialog(
                notifications, self, todo_sections=todo_sections
            )
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

    # تنظیم آیکون برنامه از لوگو
    icon = get_app_icon()
    if icon:
        app.setWindowIcon(icon)

    # تنظیم راست‌چین
    app.setLayoutDirection(Qt.RightToLeft)

    # ایجاد و نمایش پنجره اصلی
    window = LaptopRepairManager()
    window.showMaximized()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
