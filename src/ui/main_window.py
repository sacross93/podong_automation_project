"""
메인 윈도우 UI - Modern Design
"""
import flet as ft
import pandas as pd
import threading
import logging
import os
from pathlib import Path
from typing import Optional

from ..core.data_processor import DataProcessor
from ..core.exception_manager import ExceptionManager
from ..core.file_manager import FileManager
from .components.exception_editor import ExceptionEditor
from .components.error_handler import ErrorViewer

logger = logging.getLogger(__name__)


class MainWindow:

    # Design Tokens
    PRIMARY = "#4F46E5"
    PRIMARY_LIGHT = "#E0E7FF"
    PRIMARY_DARK = "#3730A3"
    BG = "#F1F5F9"
    SURFACE = "#FFFFFF"
    TEXT_H = "#0F172A"
    TEXT_P = "#334155"
    TEXT_S = "#64748B"
    TEXT_M = "#94A3B8"
    BORDER = "#E2E8F0"
    SUCCESS = "#10B981"
    SUCCESS_BG = "#ECFDF5"
    WARNING = "#F59E0B"
    WARNING_BG = "#FFFBEB"
    ERROR = "#EF4444"
    ERROR_BG = "#FEF2F2"
    INFO = "#3B82F6"
    INFO_BG = "#EFF6FF"

    def __init__(self, page: ft.Page):
        self.page = page
        self.data_processor = DataProcessor()
        self.exception_manager = ExceptionManager()
        self.file_manager = FileManager()

        self.stock_file_path = None
        self.sale_file_path = None
        self.processed_data = None
        self._saved_file_path = None
        self.error_log_path = None

        self.stock_file_picker = None
        self.sale_file_picker = None
        self.stock_file_info = None
        self.sale_file_info = None
        self.progress_bar = None
        self.status_text = None
        self.process_button = None
        self.result_container = None
        self.exception_count_text = None

        self._setup_page()
        self._build_ui()

    # ─── Page Setup ───

    def _setup_page(self):
        self.page.title = "포동 재고관리"
        self.page.bgcolor = self.BG
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.LIGHT
        try:
            screen = self.page.window
            sw = getattr(screen, 'width', 1600) or 1600
            sh = getattr(screen, 'height', 900) or 900
        except Exception:
            sw, sh = 1600, 900
        self.page.window_width = int(sw * 0.8)
        self.page.window_height = int(sh * 0.98)
        self.page.window_min_width = 900
        self.page.window_min_height = 600
        try:
            self.page.window_maximized = True
        except Exception:
            pass
        self.page.theme = ft.Theme(
            color_scheme_seed=self.PRIMARY,
            visual_density=ft.VisualDensity.COMFORTABLE,
        )

    # ─── UI Build ───

    def _build_ui(self):
        self.stock_file_picker = ft.FilePicker(on_result=self._on_stock_file_picked)
        self.sale_file_picker = ft.FilePicker(on_result=self._on_sale_file_picked)
        self.page.overlay.extend([self.stock_file_picker, self.sale_file_picker])

        product_count = len(self.exception_manager.get_all_products())
        self.exception_count_text = ft.Text(
            f"현재 {product_count}개의 제품에 대한 예외 처리가 설정되어 있습니다.",
            size=14, color=self.TEXT_S,
        )

        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=80,
            min_extended_width=160,
            bgcolor=self.SURFACE,
            indicator_color=self.PRIMARY_LIGHT,
            leading=ft.Container(
                content=ft.Icon(ft.Icons.INVENTORY_2_ROUNDED, size=28, color=self.PRIMARY),
                padding=ft.padding.only(top=16, bottom=24),
            ),
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.HOME_OUTLINED,
                    selected_icon=ft.Icons.HOME_ROUNDED,
                    label="홈",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.TUNE_OUTLINED,
                    selected_icon=ft.Icons.TUNE_ROUNDED,
                    label="예외 관리",
                ),
            ],
            on_change=self._on_nav_change,
        )

        self.home_view = self._build_home_view()
        self.exception_view = self._build_exception_view()

        self.content_area = ft.Container(
            content=self.home_view,
            expand=True,
        )

        self.page.add(
            ft.Row([
                self.nav_rail,
                ft.VerticalDivider(width=1, color=self.BORDER),
                self.content_area,
            ], expand=True, spacing=0)
        )

    def _on_nav_change(self, e):
        idx = e.control.selected_index
        self.content_area.content = self.home_view if idx == 0 else self.exception_view
        self.page.update()

    # ─── Helpers ───

    def _card(self, content, **kwargs):
        defaults = dict(
            padding=24,
            bgcolor=self.SURFACE,
            border_radius=16,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=10,
                color=ft.Colors.BLACK12,
                offset=ft.Offset(0, 2),
            ),
        )
        defaults.update(kwargs)
        return ft.Container(content=content, **defaults)

    def _pill_button(self, text, icon, color, on_click, height=44):
        return ft.ElevatedButton(
            text, icon=icon, on_click=on_click, height=height,
            style=ft.ButtonStyle(
                color=self.SURFACE,
                bgcolor=color,
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.padding.symmetric(horizontal=20, vertical=12),
            ),
        )

    # ─── Home View ───

    def _build_home_view(self):
        file_section = self._build_file_section()
        action_section = self._build_action_section()
        self.result_container = ft.Column([], spacing=16)

        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Text("재고 데이터 처리", size=28, weight=ft.FontWeight.BOLD, color=self.TEXT_H),
                        ft.Text(
                            "재고 파일과 판매 데이터를 매칭하여 주문 필요 품목을 분석합니다",
                            size=14, color=self.TEXT_S,
                        ),
                    ], spacing=4),
                    padding=ft.padding.only(bottom=8),
                ),
                file_section,
                action_section,
                self.result_container,
            ], scroll=ft.ScrollMode.AUTO, expand=True, spacing=20),
            padding=32,
            expand=True,
        )

    def _build_file_section(self):
        self.stock_file_info = ft.Text("파일을 선택해주세요", color=self.TEXT_M, size=13)
        self.sale_file_info = ft.Text("파일을 선택해주세요", color=self.TEXT_M, size=13)

        stock_card = self._build_file_card(
            icon=ft.Icons.DESCRIPTION_OUTLINED,
            icon_color=self.SUCCESS, icon_bg=self.SUCCESS_BG,
            label="재고 파일", sub_label=".xlsx / .xls",
            file_info=self.stock_file_info,
            on_click=lambda _: self.stock_file_picker.pick_files(allowed_extensions=['xlsx', 'xls']),
            border_color="#D1FAE5",
        )
        sale_card = self._build_file_card(
            icon=ft.Icons.POINT_OF_SALE_OUTLINED,
            icon_color=self.WARNING, icon_bg=self.WARNING_BG,
            label="판매 데이터", sub_label=".csv / .xlsx",
            file_info=self.sale_file_info,
            on_click=lambda _: self.sale_file_picker.pick_files(allowed_extensions=['csv', 'xlsx', 'xls']),
            border_color="#FEF3C7",
        )

        return ft.Row([stock_card, sale_card], spacing=16)

    def _build_file_card(self, icon, icon_color, icon_bg, label, sub_label, file_info, on_click, border_color):
        return ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.CLICK,
            on_tap=on_click,
            content=ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=ft.Icon(icon, size=28, color=icon_color),
                        width=56, height=56,
                        bgcolor=icon_bg,
                        border_radius=14,
                        alignment=ft.alignment.center,
                    ),
                    ft.Container(height=4),
                    ft.Text(label, size=15, weight=ft.FontWeight.W_600, color=self.TEXT_H),
                    ft.Text(sub_label, size=12, color=self.TEXT_M),
                    ft.Container(height=4),
                    file_info,
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                padding=28,
                border=ft.border.all(1.5, border_color),
                border_radius=16,
                bgcolor=self.SURFACE,
                expand=True,
                alignment=ft.alignment.center,
                shadow=ft.BoxShadow(
                    spread_radius=0, blur_radius=6,
                    color=ft.Colors.BLACK12,
                    offset=ft.Offset(0, 1),
                ),
            ),
        )

    def _build_action_section(self):
        self.progress_bar = ft.ProgressBar(
            value=0, color=self.PRIMARY, bgcolor=self.BORDER,
        )
        self.status_text = ft.Text("대기 중", size=13, color=self.TEXT_M)
        self.process_button = ft.ElevatedButton(
            "처리 시작",
            icon=ft.Icons.PLAY_ARROW_ROUNDED,
            on_click=self._start_processing,
            disabled=True,
            height=48,
            style=ft.ButtonStyle(
                color=self.SURFACE, bgcolor=self.PRIMARY,
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.padding.symmetric(horizontal=28, vertical=14),
            ),
        )

        return self._card(
            content=ft.Row([
                self.process_button,
                ft.Container(width=20),
                ft.Container(
                    content=ft.Column([self.status_text, self.progress_bar], spacing=6),
                    expand=True,
                ),
            ]),
        )

    # ─── Exception View ───

    def _build_exception_view(self):
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Text("예외 처리 관리", size=28, weight=ft.FontWeight.BOLD, color=self.TEXT_H),
                        ft.Text(
                            "판매 데이터와 재고 데이터의 특수 매핑 규칙을 관리합니다",
                            size=14, color=self.TEXT_S,
                        ),
                    ], spacing=4),
                    padding=ft.padding.only(bottom=24),
                ),
                self._card(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Icon(ft.Icons.PLAYLIST_ADD_CHECK_ROUNDED, size=24, color=self.PRIMARY),
                            width=44, height=44,
                            bgcolor=self.PRIMARY_LIGHT,
                            border_radius=10,
                            alignment=ft.alignment.center,
                        ),
                        ft.Container(width=12),
                        self.exception_count_text,
                    ]),
                ),
                ft.Container(height=20),
                ft.Text("관리 도구", size=16, weight=ft.FontWeight.W_600, color=self.TEXT_P),
                ft.Container(height=12),
                ft.Row([
                    self._pill_button("예외 목록 편집", ft.Icons.EDIT_NOTE_ROUNDED, self.PRIMARY, self._open_exception_editor),
                    self._pill_button("RAW JSON 편집", ft.Icons.CODE_ROUNDED, self.TEXT_S, self._open_raw_json_editor),
                ], spacing=12),
                ft.Container(height=8),
                ft.Row([
                    self._pill_button("JSON 파일 선택", ft.Icons.FOLDER_OPEN_ROUNDED, self.TEXT_S, self._pick_exception_json),
                    self._pill_button("기본 에디터로 열기", ft.Icons.OPEN_IN_NEW_ROUNDED, self.TEXT_S, self._open_exception_json),
                ], spacing=12),
            ]),
            padding=32,
            expand=True,
        )

    # ─── Stat Card ───

    def _build_stat_card(self, value, label, icon, color, bg_color):
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(icon, size=22, color=color),
                    width=44, height=44,
                    bgcolor=bg_color,
                    border_radius=10,
                    alignment=ft.alignment.center,
                ),
                ft.Container(width=12),
                ft.Column([
                    ft.Text(f"{value:,}", size=22, weight=ft.FontWeight.BOLD, color=self.TEXT_H),
                    ft.Text(label, size=12, color=self.TEXT_S),
                ], spacing=0),
            ]),
            padding=20,
            bgcolor=self.SURFACE,
            border_radius=14,
            shadow=ft.BoxShadow(
                spread_radius=0, blur_radius=8,
                color=ft.Colors.BLACK12,
                offset=ft.Offset(0, 2),
            ),
            expand=True,
        )

    # ─── File Events ───

    def _on_stock_file_picked(self, e: ft.FilePickerResultEvent):
        if e.files:
            self.stock_file_path = e.files[0].path
            file_info = self.file_manager.get_file_info(self.stock_file_path)
            if "error" not in file_info:
                self.stock_file_info.value = f"✓ {file_info['name']} ({file_info['size_mb']} MB)"
                self.stock_file_info.color = self.SUCCESS
                is_valid, message = self.file_manager.validate_file_structure(self.stock_file_path, 'stock')
                if not is_valid:
                    self._show_snack_bar(f"재고 파일 경고: {message}", self.WARNING)
            else:
                self.stock_file_info.value = f"✗ 오류: {file_info['error']}"
                self.stock_file_info.color = self.ERROR
            self._update_process_button_state()
            self.page.update()

    def _on_sale_file_picked(self, e: ft.FilePickerResultEvent):
        if e.files:
            self.sale_file_path = e.files[0].path
            file_info = self.file_manager.get_file_info(self.sale_file_path)
            if "error" not in file_info:
                self.sale_file_info.value = f"✓ {file_info['name']} ({file_info['size_mb']} MB)"
                self.sale_file_info.color = self.SUCCESS
                is_valid, message = self.file_manager.validate_file_structure(self.sale_file_path, 'sale')
                if not is_valid:
                    self._show_snack_bar(f"판매 데이터 경고: {message}", self.WARNING)
            else:
                self.sale_file_info.value = f"✗ 오류: {file_info['error']}"
                self.sale_file_info.color = self.ERROR
            self._update_process_button_state()
            self.page.update()

    def _update_process_button_state(self):
        self.process_button.disabled = not (self.stock_file_path and self.sale_file_path)
        self.page.update()

    # ─── Processing ───

    def _start_processing(self, e):
        self.process_button.disabled = True
        self.process_button.text = "처리 중..."
        self.page.update()
        threading.Thread(target=self._process_data, daemon=True).start()

    def _process_data(self):
        try:
            self._update_progress(0.1, "재고 파일 로딩 중...")
            self.data_processor.clear_errors()
            self.data_processor.process_stock_file(self.stock_file_path)

            self._update_progress(0.3, "판매 데이터 로딩 중...")
            sale_path = Path(self.sale_file_path)
            if sale_path.suffix.lower() in [".xlsx", ".xls"]:
                sale_data = pd.read_excel(self.sale_file_path)
            else:
                sale_data = self.file_manager.read_csv_file(self.sale_file_path)

            self._update_progress(0.5, "데이터 매칭 중...")
            self.processed_data = self.data_processor.process_sale_data(
                sale_data, self.exception_manager.get_exception_data()
            )

            self._update_progress(0.8, "결과 저장 중...")
            output_xlsx = f"./{self.data_processor.date}_stock_match.xlsx"
            output_csv = f"./{self.data_processor.date}_stock_match.csv"
            try:
                self.file_manager.save_excel_with_formatting(self.processed_data, output_xlsx)
                self.file_manager.save_csv_file(self.processed_data, output_csv)
                self._saved_file_path = str(Path(output_xlsx).resolve())
            except Exception as save_ex:
                logger.error(f"결과 자동 저장 오류: {str(save_ex)}")
                self._saved_file_path = f"자동 저장 실패: {str(save_ex)}"

            self.error_log_path = self.data_processor.save_error_log()
            self._update_results()
            self._update_progress(1.0, "처리 완료")

        except Exception as ex:
            logger.error(f"데이터 처리 오류: {str(ex)}")
            self._show_snack_bar(f"처리 오류: {str(ex)}", self.ERROR)
            self._update_progress(0, "오류 발생")
            self.process_button.disabled = False
            self.process_button.text = "처리 시작"
            self.page.update()

    def _update_progress(self, value: float, status: str):
        self.progress_bar.value = value
        self.status_text.value = status
        if value >= 1.0:
            self.status_text.color = self.SUCCESS
        elif value <= 0:
            self.status_text.color = self.ERROR
        else:
            self.status_text.color = self.PRIMARY
        self.page.update()

    # ─── Results ───

    def _update_results(self):
        if self.processed_data is None:
            return

        total = len(self.processed_data)
        order_needed = int((self.processed_data['order_now'] == 1).sum()) if 'order_now' in self.processed_data.columns else 0
        no_sales = int((self.processed_data['order_now'] == -1).sum()) if 'order_now' in self.processed_data.columns else 0
        errors = self.data_processor.get_errors()

        stat_cards = ft.Row([
            self._build_stat_card(total, "총 품목", ft.Icons.INVENTORY_2_OUTLINED, self.PRIMARY, self.PRIMARY_LIGHT),
            self._build_stat_card(order_needed, "주문 필요", ft.Icons.SHOPPING_CART_OUTLINED, self.SUCCESS, self.SUCCESS_BG),
            self._build_stat_card(no_sales, "판매 없음", ft.Icons.REMOVE_SHOPPING_CART_OUTLINED, self.WARNING, self.WARNING_BG),
            self._build_stat_card(len(errors), "오류", ft.Icons.ERROR_OUTLINE_ROUNDED, self.ERROR, self.ERROR_BG),
        ], spacing=12)

        error_section = ft.Column([], spacing=0)
        if errors:
            error_viewer = ErrorViewer(
                self.page, errors,
                on_add_exception=self._handle_add_exception,
                on_fix_exception=self._handle_fix_exception,
            )
            error_section.controls = [error_viewer.get_ui()]
        else:
            error_section.controls = [
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, size=20, color=self.SUCCESS),
                        ft.Text("모든 항목이 정상적으로 매칭되었습니다", size=14, color=self.SUCCESS),
                    ], spacing=8),
                    padding=16, bgcolor=self.SUCCESS_BG, border_radius=10,
                ),
            ]

        download_row = ft.Row([
            self._pill_button("Excel 다운로드", ft.Icons.TABLE_VIEW_ROUNDED, self.SUCCESS, self._download_excel),
            self._pill_button("CSV 다운로드", ft.Icons.DOWNLOAD_ROUNDED, self.INFO, self._download_csv),
        ], spacing=12)

        save_info = ft.Text(
            f"자동 저장: {self._saved_file_path or ''}",
            size=12, color=self.TEXT_M,
        )
        log_info = ft.Text(
            f"에러 로그: {self.error_log_path or ''}",
            size=12, color=self.TEXT_M,
        )

        self.result_container.controls = [
            ft.Container(height=4),
            ft.Text("처리 결과", size=18, weight=ft.FontWeight.W_600, color=self.TEXT_P),
            stat_cards,
            self._card(content=error_section),
            download_row,
            save_info,
            log_info,
        ]

        self.process_button.disabled = False
        self.process_button.text = "처리 시작"
        self.page.update()

    # ─── Exception Management ───

    def _open_exception_editor(self, e):
        editor = ExceptionEditor(
            self.page, self.exception_manager,
            on_save=self._on_exception_updated,
        )
        editor.show()

    def _open_exception_json(self, e):
        try:
            path = getattr(self.exception_manager, 'file_path', 'exception_list.json')
            p = Path(path)
            if not p.exists():
                self._show_snack_bar("예외 목록 파일이 없습니다.", self.ERROR)
                return
            if os.name == 'nt':
                os.startfile(str(p))
            else:
                import subprocess
                subprocess.Popen(['xdg-open', str(p)])
            self._show_snack_bar("예외 JSON 파일을 열었습니다.", self.INFO)
        except Exception as ex:
            self._show_snack_bar(f"열기 오류: {str(ex)}", self.ERROR)

    def _open_raw_json_editor(self, e):
        import json
        try:
            initial_text = json.dumps(
                self.exception_manager.get_exception_data(),
                ensure_ascii=False, indent=2,
            )
        except Exception:
            initial_text = "{}"

        json_field = ft.TextField(
            value=initial_text, multiline=True,
            min_lines=20, max_lines=28, width=800,
            border_radius=10,
        )

        def save_json(ev):
            try:
                data = json.loads(json_field.value)
                self.exception_manager.update_exception_data(data)
                self.exception_manager.save_exceptions()
                dlg.open = False
                self.page.update()
                self._on_exception_updated()
                self._show_snack_bar("예외 JSON이 저장되었습니다.", self.SUCCESS)
            except Exception as ex:
                self._show_snack_bar(f"저장 실패: {str(ex)}", self.ERROR)

        dlg = ft.AlertDialog(
            title=ft.Text("RAW JSON 편집"),
            content=json_field,
            actions=[
                ft.TextButton("취소", on_click=lambda ev: setattr(dlg, 'open', False) or self.page.update()),
                ft.TextButton("저장", on_click=save_json),
            ],
            modal=True,
        )
        try:
            self.page.open(dlg)
        except Exception:
            self.page.dialog = dlg
            dlg.open = True
            self.page.update()

    def _pick_exception_json(self, e):
        def on_result(ev: ft.FilePickerResultEvent):
            if ev.files and len(ev.files) > 0:
                path = ev.files[0].path
                try:
                    self.exception_manager.set_file_path_and_reload(path)
                    self._on_exception_updated()
                    self._show_snack_bar("예외 JSON을 로드했습니다.", self.SUCCESS)
                except Exception as ex:
                    self._show_snack_bar(f"로드 실패: {str(ex)}", self.ERROR)

        picker = ft.FilePicker(on_result=on_result)
        self.page.overlay.append(picker)
        self.page.update()
        picker.pick_files(allowed_extensions=['json'])

    # ─── Downloads ───

    def _download_excel(self, e):
        if self.processed_data is not None:
            try:
                output_path = f"./{self.data_processor.date}_stock_match.xlsx"
                self.file_manager.save_excel_with_formatting(self.processed_data, output_path)
                abs_path = str(Path(output_path).resolve())
                self._show_snack_bar(f"Excel 저장 완료: {abs_path}", self.SUCCESS)
            except Exception as ex:
                self._show_snack_bar(f"Excel 저장 오류: {str(ex)}", self.ERROR)

    def _download_csv(self, e):
        if self.processed_data is not None:
            try:
                output_path = f"./{self.data_processor.date}_stock_match.csv"
                self.file_manager.save_csv_file(self.processed_data, output_path)
                abs_path = str(Path(output_path).resolve())
                self._show_snack_bar(f"CSV 저장 완료: {abs_path}", self.SUCCESS)
            except Exception as ex:
                self._show_snack_bar(f"CSV 저장 오류: {str(ex)}", self.ERROR)

    # ─── Callbacks ───

    def _on_exception_updated(self):
        try:
            product_count = len(self.exception_manager.get_all_products())
            self.exception_count_text.value = f"현재 {product_count}개의 제품에 대한 예외 처리가 설정되어 있습니다."
            self.page.update()
        except Exception as ex:
            logger.error(f"예외 처리 업데이트 오류: {str(ex)}")

    def _handle_add_exception(self, product_name: str, option: str):
        editor = ExceptionEditor(
            self.page, self.exception_manager,
            on_save=self._on_exception_updated,
            initial_product=product_name,
        )
        editor.show()

    def _handle_fix_exception(self, product_name: str, option: str, stock_item: str = None):
        editor = ExceptionEditor(
            self.page, self.exception_manager,
            on_save=self._on_exception_updated,
            initial_product=product_name,
        )
        editor.show()

    def _show_snack_bar(self, message: str, color: str):
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color=self.SURFACE),
            bgcolor=color,
        )
        self.page.snack_bar.open = True
        self.page.update()
