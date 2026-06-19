from PyQt5.QtWidgets import QMessageBox


def show_info(parent, title, message):
    """نمایش پیام اطلاعات"""
    QMessageBox.information(parent, title, message)


def show_warning(parent, title, message):
    """نمایش پیام هشدار"""
    QMessageBox.warning(parent, title, message)


def show_error(parent, title, message):
    """نمایش پیام خطا"""
    QMessageBox.critical(parent, title, message)


def show_question(parent, title, message):
    """نمایش پیام تأیید"""
    reply = QMessageBox.question(
        parent, title, message,
        QMessageBox.Yes | QMessageBox.No
    )
    return reply == QMessageBox.Yes
