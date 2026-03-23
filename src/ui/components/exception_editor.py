"""
예외 처리 목록 편집기 컴포넌트
"""
import flet as ft
from typing import Dict, List, Callable, Optional
import logging

from ...core.exception_manager import ExceptionManager

logger = logging.getLogger(__name__)


class ExceptionEditor:
    """예외 처리 목록을 편집할 수 있는 다이얼로그"""
    
    def __init__(self, page: ft.Page, exception_manager: ExceptionManager, on_save: Optional[Callable] = None, initial_product: Optional[str] = None):
        self.page = page
        self.exception_manager = exception_manager
        self.on_save = on_save
        self.initial_product = initial_product
        
        # UI 컴포넌트들
        self.dialog = None
        self.product_list = None
        self.option_list = None
        self.stock_list = None
        self.search_field = None
        
        # 현재 선택된 항목들
        self.selected_product = None
        self.selected_option = None
        
        # 임시 데이터 (편집 중인 데이터)
        self.temp_data = exception_manager.get_exception_data()
        
        self._build_dialog()
    
    def _build_dialog(self):
        """편집기 다이얼로그 구성"""
        # 검색 필드
        self.search_field = ft.TextField(
            label="제품명 또는 옵션 검색",
            prefix_icon=ft.Icons.SEARCH,
            on_change=self._on_search,
            width=300,
        )
        
        # 제품 목록
        self.product_list = ft.ListView(
            controls=[],
            height=300,
            spacing=5,
        )
        
        # 옵션 목록
        self.option_list = ft.ListView(
            controls=[],
            height=200,
            spacing=5,
        )
        
        # 재고 항목 목록
        self.stock_list = ft.ListView(
            controls=[],
            height=150,
            spacing=5,
        )
        
        # 새 제품 추가 필드
        self.new_product_field = ft.TextField(
            label="새 제품명",
            width=200,
        )
        
        # 새 옵션 추가 필드
        self.new_option_field = ft.TextField(
            label="새 옵션",
            width=200,
        )
        
        # 새 재고 항목 추가 필드
        self.new_stock_field = ft.TextField(
            label="새 재고 항목",
            width=200,
        )
        
        # 상단 추가 버튼들(미리 생성 후 상태 제어)
        self.add_option_btn = ft.IconButton(
            icon=ft.Icons.ADD,
            tooltip="새 옵션 추가",
            on_click=self._show_add_option_dialog,
            icon_size=20,
            disabled=True,
        )
        self.add_stock_btn = ft.IconButton(
            icon=ft.Icons.ADD,
            tooltip="재고 항목 추가",
            on_click=self._show_add_stock_dialog,
            icon_size=20,
            disabled=True,
        )

        # 인라인 추가 폼(Row) 구성 - 기본 숨김
        self.add_product_row = ft.Row([
            self.new_product_field,
            ft.ElevatedButton("추가", on_click=self._confirm_add_product),
            ft.TextButton("취소", on_click=self._cancel_add_product)
        ], spacing=10, visible=False)

        self.add_option_row = ft.Row([
            self.new_option_field,
            ft.ElevatedButton("추가", on_click=self._confirm_add_option),
            ft.TextButton("취소", on_click=self._cancel_add_option)
        ], spacing=10, visible=False)

        self.add_stock_row = ft.Row([
            self.new_stock_field,
            ft.ElevatedButton("추가", on_click=self._confirm_add_stock),
            ft.TextButton("취소", on_click=self._cancel_add_stock)
        ], spacing=10, visible=False)
        
        # 다이얼로그 내용 구성
        content = ft.Container(
            content=ft.Column([
                # 헤더
                ft.Row([
                    ft.Icon(ft.Icons.EDIT, size=24),
                    ft.Text("예외 처리 목록 편집기", size=20, weight=ft.FontWeight.BOLD),
                ]),
                ft.Divider(),
                
                # 검색 영역
                ft.Row([
                    self.search_field,
                    ft.IconButton(
                        icon=ft.Icons.REFRESH,
                        tooltip="새로고침",
                        on_click=self._refresh_lists
                    ),
                ]),
                
                # 메인 편집 영역
                ft.Row([
                    # 왼쪽: 제품 목록
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text("제품 목록", size=16, weight=ft.FontWeight.W_500),
                                ft.IconButton(
                                    icon=ft.Icons.ADD,
                                    tooltip="새 제품 추가",
                                    on_click=self._show_add_product_dialog,
                                    icon_size=20,
                                ),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            self.add_product_row,
                            self.product_list,
                        ]),
                        width=250,
                        padding=10,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        border_radius=5,
                    ),
                    
                    # 중앙: 옵션 목록
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text("옵션 목록", size=16, weight=ft.FontWeight.W_500),
                                self.add_option_btn,
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            self.add_option_row,
                            self.option_list,
                        ]),
                        width=300,
                        padding=10,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        border_radius=5,
                    ),
                    
                    # 오른쪽: 재고 항목 목록
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text("대응하는 재고 항목", size=16, weight=ft.FontWeight.W_500),
                                self.add_stock_btn,
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            self.add_stock_row,
                            self.stock_list,
                        ]),
                        width=250,
                        padding=10,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        border_radius=5,
                    ),
                ], spacing=15),
                
                ft.Divider(),
                
                # 하단 버튼들
                ft.Row([
                    ft.ElevatedButton(
                        "취소",
                        on_click=self._close_dialog,
                        style=ft.ButtonStyle(color=ft.Colors.GREY_600)
                    ),
                    ft.ElevatedButton(
                        "저장",
                        on_click=self._save_changes,
                        style=ft.ButtonStyle(
                            color=ft.Colors.WHITE,
                            bgcolor=ft.Colors.BLUE_600,
                        )
                    ),
                    ft.ElevatedButton(
                        "다른 이름으로 저장",
                        on_click=self._save_changes_as,
                        style=ft.ButtonStyle(
                            color=ft.Colors.WHITE,
                            bgcolor=ft.Colors.BLUE_400,
                        )
                    ),
                ], alignment=ft.MainAxisAlignment.END),
            ], spacing=15),
            width=900,
            height=650,
            padding=20,
        )
        
        self.dialog = ft.AlertDialog(
            content=content,
            modal=True,
        )
        
        # 초기 데이터 로드
        self._refresh_lists()
        
        if self.initial_product and self.initial_product in self.temp_data:
            self._select_product(self.initial_product)
    
    def show(self):
        """편집기 다이얼로그 표시"""
        logger.info("예외 편집기: show() 호출")
        # 권장 방식: page.open(control)
        try:
            self.dialog.modal = True
            self.page.open(self.dialog)
            self.page.update()
            logger.info("예외 편집기: page.open 완료")
            return
        except Exception as ex:
            logger.warning("예외 편집기: page.open 실패, 폴백 사용 - %s", ex)
        # 폴백 방식: page.dialog에 바인딩
        try:
            self.page.dialog = self.dialog
            self.dialog.open = True
            self.page.update()
            logger.info("예외 편집기: page.dialog 폴백 완료")
        except Exception as ex:
            logger.error("예외 편집기: dialog 표시 실패 - %s", ex)
    
    def _refresh_lists(self, e=None):
        """목록들을 새로고침합니다"""
        self._update_product_list()
        self._update_option_list()
        self._update_stock_list()
    
    def _update_product_list(self, filter_text: str = ""):
        """제품 목록을 업데이트합니다"""
        self.product_list.controls.clear()
        
        products = self.temp_data.keys()
        if filter_text:
            products = [p for p in products if filter_text.lower() in p.lower()]
        
        for product in sorted(products):
            option_count = len(self.temp_data[product])
            
            tile = ft.ListTile(
                title=ft.Text(product, size=14),
                subtitle=ft.Text(f"{option_count} 개 옵션", size=12),
                leading=ft.Icon(ft.Icons.INVENTORY_2, size=20),
                trailing=ft.IconButton(
                    icon=ft.Icons.DELETE,
                    icon_color=ft.Colors.RED,
                    tooltip="제품 삭제",
                    on_click=lambda e, p=product: self._delete_product(p),
                ),
                on_click=lambda e, p=product: self._select_product(p),
                selected=product == self.selected_product,
            )
            self.product_list.controls.append(tile)
        
        self.page.update()
    
    def _update_option_list(self):
        """옵션 목록을 업데이트합니다"""
        self.option_list.controls.clear()
        # 옵션 추가 버튼 상태 업데이트 (직접 참조)
        if hasattr(self, 'add_option_btn'):
            self.add_option_btn.disabled = self.selected_product is None
        
        if not self.selected_product or self.selected_product not in self.temp_data:
            self.page.update()
            return
        
        options = self.temp_data[self.selected_product]
        for option in sorted(options.keys()):
            stock_count = len(options[option])
            
            tile = ft.ListTile(
                title=ft.Text(option, size=14),
                subtitle=ft.Text(f"{stock_count} 개 재고 항목", size=12),
                leading=ft.Icon(ft.Icons.SETTINGS, size=20),
                trailing=ft.IconButton(
                    icon=ft.Icons.DELETE,
                    icon_color=ft.Colors.RED,
                    tooltip="옵션 삭제",
                    on_click=lambda e, o=option: self._delete_option(o),
                ),
                on_click=lambda e, o=option: self._select_option(o),
                selected=option == self.selected_option,
            )
            self.option_list.controls.append(tile)
        
        self.page.update()
    
    def _update_stock_list(self):
        """재고 항목 목록을 업데이트합니다"""
        self.stock_list.controls.clear()
        # 재고 항목 추가 버튼 상태 업데이트 (직접 참조)
        if hasattr(self, 'add_stock_btn'):
            self.add_stock_btn.disabled = not (self.selected_product and self.selected_option)
        
        if not all([self.selected_product, self.selected_option]):
            self.page.update()
            return
        
        if (self.selected_product not in self.temp_data or 
            self.selected_option not in self.temp_data[self.selected_product]):
            self.page.update()
            return
        
        stock_items = self.temp_data[self.selected_product][self.selected_option]
        for i, stock_item in enumerate(stock_items):
            tile = ft.ListTile(
                title=ft.Text(stock_item, size=14),
                leading=ft.Icon(ft.Icons.INVENTORY, size=20),
                trailing=ft.IconButton(
                    icon=ft.Icons.DELETE,
                    icon_color=ft.Colors.RED,
                    tooltip="재고 항목 삭제",
                    on_click=lambda e, idx=i: self._delete_stock_item(idx),
                ),
            )
            self.stock_list.controls.append(tile)
        
        self.page.update()
    
    def _select_product(self, product: str):
        """제품을 선택합니다"""
        self.selected_product = product
        self.selected_option = None
        self._update_product_list()
        self._update_option_list()
        self._update_stock_list()
    
    def _select_option(self, option: str):
        """옵션을 선택합니다"""
        self.selected_option = option
        self._update_option_list()
        self._update_stock_list()
    
    def _on_search(self, e):
        """검색 이벤트 처리"""
        filter_text = e.control.value
        self._update_product_list(filter_text)
    
    def _show_add_product_dialog(self, e):
        """새 제품 추가 다이얼로그 표시"""
        logger.info("예외 편집기: 새 제품 추가 클릭")
        self.new_product_field.value = ""
        self.add_product_row.visible = True
        self.page.update()
    
    def _show_add_option_dialog(self, e):
        """새 옵션 추가 다이얼로그 표시"""
        if not self.selected_product:
            return
        logger.info("예외 편집기: 새 옵션 추가 클릭 - %s", self.selected_product)
        self.new_option_field.value = ""
        self.add_option_row.visible = True
        self.page.update()
    
    def _show_add_stock_dialog(self, e):
        """새 재고 항목 추가 다이얼로그 표시"""
        if not (self.selected_product and self.selected_option):
            return
        logger.info("예외 편집기: 새 재고 추가 클릭 - %s / %s", self.selected_product, self.selected_option)
        self.new_stock_field.value = ""
        self.add_stock_row.visible = True
        self.page.update()

    # 인라인 추가 폼 확정/취소 핸들러들
    def _confirm_add_product(self, e):
        product_name = self.new_product_field.value.strip()
        if product_name and product_name not in self.temp_data:
            self.temp_data[product_name] = {}
            self._refresh_lists()
        self.add_product_row.visible = False
        self.page.update()

    def _cancel_add_product(self, e):
        self.add_product_row.visible = False
        self.page.update()

    def _confirm_add_option(self, e):
        if not self.selected_product:
            return
        option_name = self.new_option_field.value.strip()
        if option_name and option_name not in self.temp_data[self.selected_product]:
            self.temp_data[self.selected_product][option_name] = []
            self._update_option_list()
        self.add_option_row.visible = False
        self.page.update()

    def _cancel_add_option(self, e):
        self.add_option_row.visible = False
        self.page.update()

    def _confirm_add_stock(self, e):
        if not (self.selected_product and self.selected_option):
            return
        stock_item = self.new_stock_field.value.strip()
        if stock_item:
            self.temp_data[self.selected_product][self.selected_option].append(stock_item)
            self._update_stock_list()
        self.add_stock_row.visible = False
        self.page.update()

    def _cancel_add_stock(self, e):
        self.add_stock_row.visible = False
        self.page.update()
    
    def _delete_product(self, product: str):
        """제품 삭제"""
        def confirm_delete(e):
            if product in self.temp_data:
                del self.temp_data[product]
                if self.selected_product == product:
                    self.selected_product = None
                    self.selected_option = None
                self._refresh_lists()
            dialog.open = False
            self.page.update()
        
        def cancel_delete(e):
            dialog.open = False
            self.page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("제품 삭제 확인"),
            content=ft.Text(f"'{product}' 제품과 모든 옵션을 삭제하시겠습니까?"),
            actions=[
                ft.TextButton("취소", on_click=cancel_delete),
                ft.TextButton("삭제", on_click=confirm_delete, style=ft.ButtonStyle(color=ft.Colors.RED)),
            ],
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def _delete_option(self, option: str):
        """옵션 삭제"""
        if not (self.selected_product and option in self.temp_data[self.selected_product]):
            return
        
        del self.temp_data[self.selected_product][option]
        if self.selected_option == option:
            self.selected_option = None
        
        # 제품에 옵션이 없으면 제품도 삭제
        if not self.temp_data[self.selected_product]:
            del self.temp_data[self.selected_product]
            self.selected_product = None
        
        self._refresh_lists()
    
    def _delete_stock_item(self, index: int):
        """재고 항목 삭제"""
        if not all([self.selected_product, self.selected_option]):
            return
        
        if (self.selected_product in self.temp_data and 
            self.selected_option in self.temp_data[self.selected_product] and
            0 <= index < len(self.temp_data[self.selected_product][self.selected_option])):
            
            del self.temp_data[self.selected_product][self.selected_option][index]
            self._update_stock_list()
    
    def _save_changes(self, e):
        """변경사항 저장"""
        try:
            logger.info("예외 편집기: 저장 버튼 클릭")
            self.page.update()
            # 유효성 검증
            errors = self._validate_data()
            if errors:
                error_text = "\\n".join(errors)
                self._show_error_dialog(f"데이터 유효성 오류:\\n{error_text}")
                return
            
            # 데이터 저장
            self.exception_manager.update_exception_data(self.temp_data)
            self.exception_manager.save_exceptions()
            logger.info("예외 편집기: 저장 완료 -> %s", getattr(self.exception_manager, 'file_path', 'exception_list.json'))
            
            if self.on_save:
                self.on_save()
            
            self._close_dialog()
            
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("예외 처리 목록이 저장되었습니다."),
                bgcolor=ft.Colors.GREEN,
            )
            self.page.snack_bar.open = True
            self.page.update()
            
        except Exception as ex:
            logger.error(f"예외 처리 목록 저장 오류: {str(ex)}")
            self._show_error_dialog(f"저장 오류: {str(ex)}")

    def _save_changes_as(self, e):
        """다른 이름으로 저장"""
        def on_result(ev: ft.FilePickerResultEvent):
            if ev.path:
                try:
                    self.exception_manager.update_exception_data(self.temp_data)
                    self.exception_manager.save_as(ev.path)
                    logger.info("예외 편집기: 다른 이름으로 저장 완료 -> %s", ev.path)
                    self.page.snack_bar = ft.SnackBar(
                        content=ft.Text("예외 처리 목록을 다른 이름으로 저장했습니다."),
                        bgcolor=ft.Colors.GREEN,
                    )
                    self.page.snack_bar.open = True
                    self.page.update()
                except Exception as ex:
                    self._show_error_dialog(f"저장 오류: {str(ex)}")

        picker = ft.FilePicker(on_result=on_result)
        self.page.overlay.append(picker)
        self.page.update()
        picker.save_file(file_name="exception_list.json", allowed_extensions=['json'])
    
    def _validate_data(self) -> List[str]:
        """데이터 유효성 검증"""
        errors = []
        
        for product, options in self.temp_data.items():
            if not product.strip():
                errors.append("제품명이 비어있습니다")
                continue
            
            if not isinstance(options, dict):
                errors.append(f"제품 '{product}': 잘못된 옵션 데이터")
                continue
            
            if not options:
                errors.append(f"제품 '{product}': 옵션이 없습니다")
                continue
            
            for option, stock_items in options.items():
                if not option.strip():
                    errors.append(f"제품 '{product}': 옵션명이 비어있습니다")
                
                if not isinstance(stock_items, list):
                    errors.append(f"제품 '{product}', 옵션 '{option}': 잘못된 재고 항목 데이터")
                    continue
                
                if not stock_items:
                    errors.append(f"제품 '{product}', 옵션 '{option}': 재고 항목이 없습니다")
                
                for stock_item in stock_items:
                    if not stock_item.strip():
                        errors.append(f"제품 '{product}', 옵션 '{option}': 빈 재고 항목이 있습니다")
        
        return errors
    
    def _show_error_dialog(self, message: str):
        """오류 다이얼로그 표시"""
        def close_error(e):
            error_dialog.open = False
            self.page.update()
        
        error_dialog = ft.AlertDialog(
            title=ft.Text("오류"),
            content=ft.Text(message),
            actions=[ft.TextButton("확인", on_click=close_error)],
        )
        
        self.page.dialog = error_dialog
        error_dialog.open = True
        self.page.update()
    
    def _close_dialog(self, e=None):
        """다이얼로그 닫기"""
        self.dialog.open = False
        self.page.update()
