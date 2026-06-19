from typing import List, Dict, Callable

from PyQt5.QtWidgets import QTableWidget

from services.table_service import build_table_rows
from ui.table_renderer import render_table_rows
from core.filters import search_repairs as search_repairs_service
from core.filters import filter_repairs as filter_repairs_service


class MainController:
    @staticmethod
    def refresh_table(
        table: QTableWidget,
        repairs: List[Dict],
        view_callback: Callable,
        invoice_callback: Callable,
        update_stats_callback: Callable,
    ):
        rows_data = build_table_rows(repairs)
        render_table_rows(table, rows_data, view_callback, invoice_callback)
        update_stats_callback()

    @staticmethod
    def search_repairs(table: QTableWidget, repairs: List[Dict], text: str):
        matching_indices = search_repairs_service(repairs, text)
        for row in range(table.rowCount()):
            table.setRowHidden(row, row not in matching_indices)

    @staticmethod
    def filter_repairs(table: QTableWidget, repairs: List[Dict], status: str):
        matching_indices = filter_repairs_service(repairs, status)
        for row in range(table.rowCount()):
            table.setRowHidden(row, row not in matching_indices)
