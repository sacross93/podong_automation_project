"""
에러 핸들링 시스템 - Modern ExpansionTile Design
"""
import flet as ft
import re
from typing import List, Dict, Optional, Callable
from enum import Enum


class ErrorType(Enum):
    MATCHING_FAILED = "matching_failed"
    EXCEPTION_NOT_FOUND = "exception_not_found"
    DOUBLE_SQUARE_RING = "double_square_ring"
    FILE_STRUCTURE = "file_structure"
    DATA_VALIDATION = "data_validation"
    UNKNOWN = "unknown"


class ErrorSolution:
    def __init__(self, title: str, description: str, actions: List[Dict] = None):
        self.title = title
        self.description = description
        self.actions = actions or []


class ErrorAnalyzer:
    ERROR_PATTERNS = {
        ErrorType.MATCHING_FAILED: [
            r"(.+?) / (.+?) → 추가 안됨 (.+)",
            r"매칭 실패: 상품명 '([^']+)', 옵션 '([^']+)'",
        ],
        ErrorType.EXCEPTION_NOT_FOUND: [
            r"예외처리 실패: 상품명 '([^']+)', 옵션 '([^']+)'에 해당하는 재고 '([^']+)'를 찾을 수 없습니다",
        ],
        ErrorType.DOUBLE_SQUARE_RING: [
            r"더블스퀘어링 공통옵션 '([^']+)'을 재고목록에서 찾을 수 없습니다",
            r"더블스퀘어링 추가옵션 '([^']+)' -> '([^']+)'를 재고목록에서 찾을 수 없습니다",
            r"더블스퀘어링 추가옵션 '([^']+)'이 예외 목록에 없습니다",
        ],
        ErrorType.FILE_STRUCTURE: [
            r"재고 파일 처리 오류: (.+)",
            r"판매 데이터 매칭 오류: (.+)",
        ],
        ErrorType.DATA_VALIDATION: [
            r"데이터 구조 오류: (.+)",
            r"품목 수와 재고 수량이 맞지 않습니다",
        ],
    }

    @classmethod
    def analyze_error(cls, error_message: str) -> tuple:
        for error_type, patterns in cls.ERROR_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, error_message)
                if match:
                    return error_type, {
                        'groups': match.groups(),
                        'full_match': match.group(0),
                        'message': error_message,
                    }
        return ErrorType.UNKNOWN, {'message': error_message}

    @classmethod
    def get_solution(cls, error_type: ErrorType, error_info: Dict) -> ErrorSolution:
        groups = error_info.get('groups', ())

        if error_type == ErrorType.MATCHING_FAILED:
            product = groups[0] if groups else "알 수 없음"
            option = groups[1] if len(groups) > 1 else "알 수 없음"
            reason = groups[2] if len(groups) > 2 else ""
            desc = f"'{product}' — '{option}' 매칭 실패"
            if reason:
                desc += f"\n사유: {reason}"
            return ErrorSolution(
                title="상품 매칭 실패", description=desc,
                actions=[{"type": "add_exception", "text": "예외 처리 추가",
                          "data": {"product": product, "option": option}}],
            )

        elif error_type == ErrorType.EXCEPTION_NOT_FOUND:
            product = groups[0] if groups else "알 수 없음"
            option = groups[1] if len(groups) > 1 else "알 수 없음"
            stock = groups[2] if len(groups) > 2 else "알 수 없음"
            return ErrorSolution(
                title="예외 처리 재고 항목 없음",
                description=f"'{product}' — '{option}'의 재고 항목 '{stock}'을 찾을 수 없습니다.",
                actions=[{"type": "fix_exception", "text": "예외 처리 수정",
                          "data": {"product": product, "option": option, "stock": stock}}],
            )

        elif error_type == ErrorType.DOUBLE_SQUARE_RING:
            if "공통옵션" in error_info['message']:
                opt = groups[0] if groups else ""
                return ErrorSolution(
                    title="더블스퀘어링 공통옵션 오류",
                    description=f"공통옵션 '{opt}'을 재고에서 찾을 수 없습니다.",
                    actions=[{"type": "fix_exception", "text": "공통옵션 수정",
                              "data": {"product": "더블스퀘어링", "type": "common", "option": opt}}],
                )
            else:
                opt = groups[0] if groups else ""
                stock = groups[1] if len(groups) > 1 else ""
                return ErrorSolution(
                    title="더블스퀘어링 추가옵션 오류",
                    description=f"추가옵션 '{opt}' → '{stock}' 매칭 실패",
                    actions=[{"type": "fix_exception", "text": "추가옵션 수정",
                              "data": {"product": "더블스퀘어링", "type": "additional", "option": opt, "stock": stock}}],
                )

        elif error_type == ErrorType.FILE_STRUCTURE:
            return ErrorSolution(
                title="파일 구조 오류",
                description="업로드한 파일의 구조에 문제가 있습니다.",
                actions=[{"type": "check_file", "text": "파일 형식 확인", "data": {}}],
            )

        elif error_type == ErrorType.DATA_VALIDATION:
            return ErrorSolution(
                title="데이터 검증 오류",
                description=error_info['message'],
                actions=[],
            )

        return ErrorSolution(
            title="기타 오류",
            description=error_info['message'],
            actions=[],
        )


class ErrorViewer:

    TYPE_CONFIG = {
        ErrorType.MATCHING_FAILED:    {"label": "매칭 실패",     "color": "#EF4444", "bg": "#FEF2F2", "icon": ft.Icons.LINK_OFF_ROUNDED},
        ErrorType.EXCEPTION_NOT_FOUND: {"label": "예외처리 오류", "color": "#F59E0B", "bg": "#FFFBEB", "icon": ft.Icons.WARNING_AMBER_ROUNDED},
        ErrorType.DOUBLE_SQUARE_RING:  {"label": "더블스퀘어링",  "color": "#8B5CF6", "bg": "#F5F3FF", "icon": ft.Icons.SETTINGS_ROUNDED},
        ErrorType.FILE_STRUCTURE:      {"label": "파일 오류",     "color": "#3B82F6", "bg": "#EFF6FF", "icon": ft.Icons.DESCRIPTION_ROUNDED},
        ErrorType.DATA_VALIDATION:     {"label": "데이터 오류",   "color": "#F59E0B", "bg": "#FFFBEB", "icon": ft.Icons.DATA_OBJECT},
        ErrorType.UNKNOWN:             {"label": "기타",          "color": "#64748B", "bg": "#F8FAFC", "icon": ft.Icons.HELP_OUTLINE_ROUNDED},
    }

    def __init__(self, page: ft.Page, errors: List[str],
                 on_add_exception: Optional[Callable] = None,
                 on_fix_exception: Optional[Callable] = None):
        self.page = page
        self.errors = errors
        self.on_add_exception = on_add_exception
        self.on_fix_exception = on_fix_exception
        self._cached_ui = None

    def get_ui(self):
        if self._cached_ui is None:
            self._cached_ui = self._build_ui()
        return self._cached_ui

    def _build_ui(self):
        stats = self._analyze_errors()

        stat_chips = []
        for etype, count in stats.items():
            if count > 0:
                cfg = self.TYPE_CONFIG.get(etype, self.TYPE_CONFIG[ErrorType.UNKNOWN])
                stat_chips.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(str(count), size=14, weight=ft.FontWeight.BOLD, color=cfg["color"]),
                            ft.Text(cfg["label"], size=12, color="#64748B"),
                        ], spacing=6),
                        padding=ft.padding.symmetric(horizontal=14, vertical=8),
                        bgcolor=cfg["bg"],
                        border_radius=20,
                    )
                )

        error_tiles = []
        for error in self.errors:
            etype, einfo = ErrorAnalyzer.analyze_error(error)
            solution = ErrorAnalyzer.get_solution(etype, einfo)
            error_tiles.append(self._build_error_tile(error, etype, solution))

        return ft.Column([
            ft.Row([
                ft.Text(f"오류 {len(self.errors)}건", size=16, weight=ft.FontWeight.W_600, color="#334155"),
                ft.Container(expand=True),
                ft.Row(stat_chips, spacing=8, wrap=True),
            ]),
            ft.Container(height=12),
            ft.Column(error_tiles, spacing=6),
        ])

    def _build_error_tile(self, error: str, etype: ErrorType, solution: ErrorSolution):
        cfg = self.TYPE_CONFIG.get(etype, self.TYPE_CONFIG[ErrorType.UNKNOWN])
        short = error[:100] + "..." if len(error) > 100 else error

        action_buttons = []
        for action in solution.actions:
            action_buttons.append(
                ft.OutlinedButton(
                    text=action['text'],
                    on_click=lambda e, a=action: self._handle_action(a),
                    style=ft.ButtonStyle(
                        color=cfg["color"],
                        shape=ft.RoundedRectangleBorder(radius=8),
                        side=ft.BorderSide(1, cfg["color"]),
                        padding=ft.padding.symmetric(horizontal=14, vertical=6),
                    ),
                    height=34,
                )
            )

        detail_controls = [
            ft.Text(solution.description, size=13, color="#475569"),
            ft.Container(height=8),
            ft.Container(
                content=ft.Text(error, size=11, color="#64748B", selectable=True),
                padding=12,
                bgcolor="#F8FAFC",
                border_radius=8,
            ),
        ]
        if action_buttons:
            detail_controls.append(ft.Container(height=10))
            detail_controls.append(ft.Row(action_buttons, spacing=8))

        return ft.Container(
            content=ft.ExpansionTile(
                leading=ft.Container(
                    content=ft.Icon(cfg["icon"], size=16, color="#FFFFFF"),
                    width=28, height=28,
                    bgcolor=cfg["color"],
                    border_radius=7,
                    alignment=ft.alignment.center,
                ),
                title=ft.Text(short, size=13, color="#334155"),
                subtitle=ft.Text(cfg["label"], size=11, color=cfg["color"]),
                tile_padding=ft.padding.symmetric(horizontal=12, vertical=4),
                controls=[
                    ft.Container(
                        content=ft.Column(detail_controls),
                        padding=ft.padding.only(left=52, right=16, bottom=14),
                    ),
                ],
            ),
            bgcolor="#FFFFFF",
            border_radius=10,
            border=ft.border.all(1, "#F1F5F9"),
        )

    def _analyze_errors(self) -> Dict[ErrorType, int]:
        stats = {}
        for error in self.errors:
            etype, _ = ErrorAnalyzer.analyze_error(error)
            stats[etype] = stats.get(etype, 0) + 1
        return stats

    def _handle_action(self, action: Dict):
        atype = action.get('type')
        data = action.get('data', {})
        if atype == 'add_exception' and self.on_add_exception:
            self.on_add_exception(data.get('product'), data.get('option'))
        elif atype == 'fix_exception' and self.on_fix_exception:
            self.on_fix_exception(data.get('product'), data.get('option'), data.get('stock'))
        elif atype == 'check_file':
            self._show_file_help()

    def _show_file_help(self):
        help_text = (
            "재고 파일 (Excel):\n"
            "  - 3번째 행이 헤더\n"
            "  - '품명', '위안', '원화' 컬럼 필요\n\n"
            "판매 데이터 (CSV):\n"
            "  - '상품명', '옵션', '판매수량' 컬럼 필요"
        )

        def close(e):
            dlg.open = False
            self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("파일 형식 안내"),
            content=ft.Text(help_text),
            actions=[ft.TextButton("확인", on_click=close)],
        )
        try:
            self.page.open(dlg)
        except Exception:
            self.page.dialog = dlg
            dlg.open = True
            self.page.update()
