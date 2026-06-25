import json
from pathlib import Path

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                              QLineEdit, QTextEdit, QLabel, QPushButton,
                              QFileDialog, QSpinBox, QCheckBox, QColorDialog,
                              QFrame)
from PyQt5.QtCore import Qt, QRegularExpression
from PyQt5.QtGui import QFont, QRegularExpressionValidator, QColor

from services.notification_service import show_info, show_error, show_warning, show_question


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
        self.phone_input.setValidator(QRegularExpressionValidator(QRegularExpression(r'^0\d{10}$')))
        form_layout.addWidget(self.phone_input, 2, 1)

        # موبایل
        form_layout.addWidget(QLabel("موبایل:"), 3, 0)
        self.mobile_input = QLineEdit()
        self.mobile_input.setPlaceholderText("شماره موبایل")
        self.mobile_input.setValidator(QRegularExpressionValidator(QRegularExpression(r'^0\d{10}$')))
        form_layout.addWidget(self.mobile_input, 3, 1)

        # ایمیل
        form_layout.addWidget(QLabel("ایمیل:"), 4, 0)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("آدرس ایمیل")
        self.email_input.setValidator(QRegularExpressionValidator(QRegularExpression(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')))
        form_layout.addWidget(self.email_input, 4, 1)

        # وبسایت
        form_layout.addWidget(QLabel("وبسایت:"), 5, 0)
        self.website_input = QLineEdit()
        self.website_input.setPlaceholderText("آدرس وبسایت")
        self.website_input.setValidator(QRegularExpressionValidator(QRegularExpression(r'^(https?://)?(www\.)?[A-Za-z0-9-]+\.[A-Za-z]{2,}.*$')))
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

        # اندازه لوگو در فاکتور
        form_layout.addWidget(QLabel("اندازه لوگو در فاکتور:"), 7, 0)
        self.invoice_logo_size_spin = QSpinBox()
        self.invoice_logo_size_spin.setRange(16, 256)
        self.invoice_logo_size_spin.setValue(96)
        self.invoice_logo_size_spin.setSuffix(" px")
        form_layout.addWidget(self.invoice_logo_size_spin, 7, 1)

        # اندازه لوگو در هدر برنامه
        form_layout.addWidget(QLabel("اندازه لوگو در هدر:"), 8, 0)
        self.header_logo_size_spin = QSpinBox()
        self.header_logo_size_spin.setRange(16, 512)
        self.header_logo_size_spin.setValue(32)
        self.header_logo_size_spin.setSuffix(" px")
        form_layout.addWidget(self.header_logo_size_spin, 8, 1)

        # اندازه فونت عنوان هدر
        form_layout.addWidget(QLabel("اندازه فونت عنوان هدر:"), 9, 0)
        self.header_title_size_spin = QSpinBox()
        self.header_title_size_spin.setRange(12, 48)
        self.header_title_size_spin.setValue(20)
        self.header_title_size_spin.setSuffix(" pt")
        form_layout.addWidget(self.header_title_size_spin, 9, 1)

        # رنگ عنوان هدر
        self._add_color_field(form_layout, "رنگ عنوان هدر:", 11, "#FFFFFF", "_header_title_color")

        # رنگ شروع گرادینت هدر
        self._add_color_field(form_layout, "رنگ شروع گرادینت:", 12, "#4F46E5", "_header_gradient_start")

        # رنگ پایان گرادینت هدر
        self._add_color_field(form_layout, "رنگ پایان گرادینت:", 13, "#7C3AED", "_header_gradient_end")

        # شعاع گوشه هدر
        form_layout.addWidget(QLabel("شعاع گوشه هدر:"), 14, 0)
        self.header_border_radius_spin = QSpinBox()
        self.header_border_radius_spin.setRange(0, 50)
        self.header_border_radius_spin.setValue(15)
        self.header_border_radius_spin.setSuffix(" px")
        form_layout.addWidget(self.header_border_radius_spin, 14, 1)

        # ارتفاع هدر
        form_layout.addWidget(QLabel("ارتفاع هدر:"), 15, 0)
        self.header_height_spin = QSpinBox()
        self.header_height_spin.setRange(40, 200)
        self.header_height_spin.setValue(60)
        self.header_height_spin.setSuffix(" px")
        form_layout.addWidget(self.header_height_spin, 15, 1)

        # استفاده از لوگو به عنوان آیکون
        self.use_logo_as_icon_check = QCheckBox("استفاده از لوگو به عنوان آیکون برنامه")
        form_layout.addWidget(self.use_logo_as_icon_check, 16, 1)

        # --- Dashboard popup settings ---
        dash_title = QLabel("تنظیمات داشبورد")
        dash_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        dash_title.setAlignment(Qt.AlignCenter)
        form_layout.addWidget(dash_title, 17, 0, 1, 2)

        self._add_color_field(form_layout, "رنگ پس‌زمینه داشبورد:", 18, "#FFFFFF", "_status_popup_background_color")
        self._add_color_field(form_layout, "رنگ حاشیه داشبورد:", 19, "#D1D5DB", "_status_popup_border_color")

        form_layout.addWidget(QLabel("ضخامت حاشیه داشبورد:"), 20, 0)
        self.status_popup_border_width_spin = QSpinBox()
        self.status_popup_border_width_spin.setRange(0, 5)
        self.status_popup_border_width_spin.setValue(1)
        self.status_popup_border_width_spin.setSuffix(" px")
        form_layout.addWidget(self.status_popup_border_width_spin, 20, 1)

        form_layout.addWidget(QLabel("شعاع گوشه داشبورد:"), 21, 0)
        self.status_popup_border_radius_spin = QSpinBox()
        self.status_popup_border_radius_spin.setRange(0, 30)
        self.status_popup_border_radius_spin.setValue(12)
        self.status_popup_border_radius_spin.setSuffix(" px")
        form_layout.addWidget(self.status_popup_border_radius_spin, 21, 1)

        self._add_color_field(form_layout, "رنگ متن داشبورد:", 22, "#111827", "_status_popup_text_color")
        self._add_color_field(form_layout, "رنگ تاریخ/ساعت:", 23, "#374151", "_status_popup_datetime_color")

        layout.addLayout(form_layout)

        # Restore defaults button
        restore_btn = QPushButton("بازگردانی تنظیمات پیش‌فرض")
        restore_btn.setStyleSheet("background-color: #FF9800; color: white; padding: 8px 20px; font-weight: bold;")
        restore_btn.clicked.connect(self.restore_defaults)
        layout.addWidget(restore_btn)

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

    def _add_color_field(self, form_layout, label, row, default_color, attr_name):
        form_layout.addWidget(QLabel(label), row, 0)
        hbox = QHBoxLayout()
        swatch = QFrame()
        swatch.setFixedSize(24, 24)
        swatch.setStyleSheet(f"background-color: {default_color}; border: 1px solid #888; border-radius: 3px;")
        btn = QPushButton("انتخاب رنگ")

        def pick():
            color = QColorDialog.getColor(QColor(getattr(self, attr_name, default_color)), self)
            if color.isValid():
                hex_color = color.name()
                setattr(self, attr_name, hex_color)
                swatch.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #888; border-radius: 3px;")

        btn.clicked.connect(pick)
        hbox.addWidget(swatch)
        hbox.addWidget(btn)
        form_layout.addLayout(hbox, row, 1)
        setattr(self, attr_name, default_color)

    def restore_defaults(self):
        """بازگردانی تنظیمات پیش‌فرض ظاهری"""
        if not show_question(self, "تأیید", "آیا از بازگردانی تنظیمات پیش‌فرض ظاهری اطمینان دارید؟"):
            return
        self._header_title_color = "#FFFFFF"
        self._header_gradient_start = "#4F46E5"
        self._header_gradient_end = "#7C3AED"
        self.header_border_radius_spin.setValue(15)
        self.header_height_spin.setValue(60)
        self.header_title_size_spin.setValue(20)
        self.header_logo_size_spin.setValue(32)
        self.invoice_logo_size_spin.setValue(96)
        self._status_popup_background_color = "#FFFFFF"
        self._status_popup_border_color = "#D1D5DB"
        self.status_popup_border_width_spin.setValue(1)
        self.status_popup_border_radius_spin.setValue(12)
        self._status_popup_text_color = "#111827"
        self._status_popup_datetime_color = "#374151"
        show_info(self, "موفق", "تنظیمات ظاهری به مقادیر پیش‌فرض بازگردانده شد.")

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

                self.invoice_logo_size_spin.setValue(settings.get("invoice_logo_size", 96))
                self.header_logo_size_spin.setValue(settings.get("header_logo_size", 32))
                self.header_title_size_spin.setValue(settings.get("header_title_size", 20))

                color = settings.get("header_title_color", "#FFFFFF")
                self._header_title_color = color
                # update swatch (note: this runs before UI so we just store the value)

                gs = settings.get("header_gradient_start", "#4F46E5")
                self._header_gradient_start = gs

                ge = settings.get("header_gradient_end", "#7C3AED")
                self._header_gradient_end = ge

                self.header_border_radius_spin.setValue(settings.get("header_border_radius", 15))
                self.header_height_spin.setValue(settings.get("header_height", 60))
                self.use_logo_as_icon_check.setChecked(settings.get("use_logo_as_app_icon", False))

                spbg = settings.get("status_popup_background_color", "#FFFFFF")
                self._status_popup_background_color = spbg
                spbc = settings.get("status_popup_border_color", "#D1D5DB")
                self._status_popup_border_color = spbc
                self.status_popup_border_width_spin.setValue(settings.get("status_popup_border_width", 1))
                self.status_popup_border_radius_spin.setValue(settings.get("status_popup_border_radius", 12))
                sptc = settings.get("status_popup_text_color", "#111827")
                self._status_popup_text_color = sptc
                spdc = settings.get("status_popup_datetime_color", "#374151")
                self._status_popup_datetime_color = spdc
        except Exception as e:
            print(f"خطا در بارگذاری تنظیمات: {e}")

    def save_settings(self):
        """ذخیره تنظیمات"""
        if self.phone_input.text() and not self.phone_input.hasAcceptableInput():
            show_warning(self, "خطا", "شماره تلفن باید ۱۱ رقم و با ۰ شروع شود")
            return
        if self.mobile_input.text() and not self.mobile_input.hasAcceptableInput():
            show_warning(self, "خطا", "شماره موبایل باید ۱۱ رقم و با ۰ شروع شود")
            return
        if self.email_input.text() and not self.email_input.hasAcceptableInput():
            show_warning(self, "خطا", "ایمیل وارد شده معتبر نیست")
            return
        if self.website_input.text() and not self.website_input.hasAcceptableInput():
            show_warning(self, "خطا", "وبسایت وارد شده معتبر نیست")
            return
        settings = {
            "shop_name": self.shop_name_input.text(),
            "address": self.address_input.toPlainText(),
            "phone": self.phone_input.text(),
            "mobile": self.mobile_input.text(),
            "email": self.email_input.text(),
            "website": self.website_input.text(),
            "logo": self.logo_path,
            "invoice_logo_size": self.invoice_logo_size_spin.value(),
            "header_logo_size": self.header_logo_size_spin.value(),
            "header_title_size": self.header_title_size_spin.value(),
            "header_title_color": getattr(self, "_header_title_color", "#FFFFFF"),
            "header_gradient_start": getattr(self, "_header_gradient_start", "#4F46E5"),
            "header_gradient_end": getattr(self, "_header_gradient_end", "#7C3AED"),
            "header_border_radius": self.header_border_radius_spin.value(),
            "header_height": self.header_height_spin.value(),
            "use_logo_as_app_icon": self.use_logo_as_icon_check.isChecked(),
            "status_popup_background_color": getattr(self, "_status_popup_background_color", "#FFFFFF"),
            "status_popup_border_color": getattr(self, "_status_popup_border_color", "#D1D5DB"),
            "status_popup_border_width": self.status_popup_border_width_spin.value(),
            "status_popup_border_radius": self.status_popup_border_radius_spin.value(),
            "status_popup_text_color": getattr(self, "_status_popup_text_color", "#111827"),
            "status_popup_datetime_color": getattr(self, "_status_popup_datetime_color", "#374151")
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
            "logo": "",
            "invoice_logo_size": 96,
            "header_logo_size": 32,
            "header_title_size": 20,
            "header_title_color": "#FFFFFF",
            "header_gradient_start": "#4F46E5",
            "header_gradient_end": "#7C3AED",
            "header_border_radius": 15,
            "header_height": 60,
            "use_logo_as_app_icon": False
        }

        try:
            if Path("shop_settings.json").exists():
                with open("shop_settings.json", "r", encoding="utf-8") as f:
                    return json.load(f)
        except:
            pass
        return default_settings
