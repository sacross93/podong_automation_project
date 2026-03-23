"""
포동 재고관리 자동화 앱 메인 진입점
"""
import flet as ft
import logging
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.settings import app_settings, setup_logging
from src.ui.main_window import MainWindow

# 로깅 설정
setup_logging(app_settings)
logger = logging.getLogger(__name__)


def main(page: ft.Page):
    """메인 애플리케이션 함수"""
    try:
        print("🚀 애플리케이션 시작...")
        logger.info("애플리케이션 시작")
        
        # 메인 윈도우 생성
        print("🏠 메인 윈도우 생성 중...")
        main_window = MainWindow(page)
        
        print("✅ 메인 윈도우 초기화 완료!")
        logger.info("메인 윈도우 초기화 완료")
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        logger.error(f"애플리케이션 시작 오류: {str(e)}")
        import traceback
        print("상세 오류:")
        traceback.print_exc()
        
        # 오류 발생 시 간단한 오류 페이지 표시
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.ERROR, size=64, color=ft.Colors.RED),
                    ft.Text("애플리케이션 시작 중 오류가 발생했습니다", size=20),
                    ft.Text(f"오류: {str(e)}", color=ft.Colors.RED),
                    ft.Text("콘솔을 확인해주세요.", color=ft.Colors.GREY),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=50,
                alignment=ft.alignment.center,
                expand=True
            )
        )


if __name__ == "__main__":
    try:
        print("🎯 포동 재고관리 자동화 앱 시작...")
        logger.info("포동 재고관리 자동화 앱 시작")
        
        print("📦 Flet 앱 실행 중...")
        # Flet 앱 실행
        ft.app(
            target=main,
            name="포동 재고관리 자동화",
            assets_dir="assets" if Path("assets").exists() else None,
        )
        
    except Exception as e:
        print(f"❌ 앱 실행 오류: {str(e)}")
        logger.error(f"앱 실행 오류: {str(e)}")
        import traceback
        print("상세 오류:")
        traceback.print_exc()
        input("엔터를 눌러서 종료...")
    
    print("👋 애플리케이션 종료")
    logger.info("애플리케이션 종료")
