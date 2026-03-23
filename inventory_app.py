import os
import sys
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, font
import threading
import datetime
from pathlib import Path
import traceback
import shutil
import pandas as pd
import numpy as np
import re
import logging
import concurrent.futures
from typing import Dict, List, Optional, Tuple, Union, Any
import matplotlib.pyplot as plt
import seaborn as sns
import google.generativeai as genai
from dotenv import load_dotenv
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# TkinterDnD2 라이브러리 가져오기 (드래그 앤 드롭 기능)
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
except ImportError:
    messagebox.showwarning("라이브러리 누락", "TkinterDnD2 라이브러리가 설치되지 않았습니다. 'pip install tkinterdnd2' 명령으로 설치해주세요.")
    TkinterDnD = tk.Tk

# 리소스 파일 경로 처리 함수
def resource_path(relative_path):
    """PyInstaller로 번들링된 앱에서 리소스 파일 경로를 가져옵니다."""
    try:
        # PyInstaller가 생성한 임시 폴더 경로
        base_path = sys._MEIPASS
    except Exception:
        # 일반 Python 스크립트로 실행 중인 경우
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# 환경 변수 설정 함수
def setup_environment():
    """환경 변수를 설정하고 필요한 파일을 추출합니다."""
    # 실행 파일 디렉토리에 config 폴더 생성
    config_dir = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "config")
    os.makedirs(config_dir, exist_ok=True)
    
    # .env 파일 생성 (내장된 API 키 사용)
    env_path = os.path.join(config_dir, ".env")
    if not os.path.exists(env_path):
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("GEMINI_API_KEY_JY = AIzaSyC2J-w8Y2bqf7oOxOrRBeAwT7CEA-IAQTs\n")
    
    # exception_list.json 파일 복사 (내장된 파일 사용)
    exception_file = os.path.join(config_dir, "exception_list.json")
    if not os.path.exists(exception_file):
        try:
            # 내장된 리소스에서 복사
            shutil.copy(resource_path("resources/exception_list.json"), exception_file)
        except Exception:
            # 내장된 리소스가 없는 경우 기본 파일 생성
            with open(exception_file, "w", encoding="utf-8") as f:
                f.write("{}\n")
    
    # 환경 변수 설정
    os.environ["GEMINI_API_KEY"] = "AIzaSyC2J-w8Y2bqf7oOxOrRBeAwT7CEA-IAQTs"
    
    return config_dir

# 로거 설정 함수 추가
def setup_logger():
    """애플리케이션 로거 설정"""
    logger = logging.getLogger('inventory_app')
    logger.setLevel(logging.INFO)
    
    # 이미 핸들러가 있는 경우 중복 설정 방지
    if logger.handlers:
        return logger
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 파일 핸들러
    try:
        log_dir = os.path.join("logs")
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"{datetime.datetime.now().strftime('%Y%m%d')}_app.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 포맷 설정
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # 핸들러 추가
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"로그 파일 설정 중 오류: {e}")
        # 콘솔 핸들러만 추가
        logger.addHandler(console_handler)
    
    return logger

# 기본 Gemini 프롬프트 템플릿
DEFAULT_PROMPT_TEMPLATE = """다음은 재고 관리 시스템의 로그 파일과 재고 매칭 파일에서 추출한 정보입니다:

### 로그 정보:
{log_content}

### 재고 정보:
- 총 항목 수: {total_items}개
- 카테고리 수: {categories}개
- 재고 없는 항목: {zero_inventory}개
- 재주문 필요 항목: {reorder_needed}개 (현재 재고가 2주 예상 판매량보다 적은 경우)
- 중복 항목: {duplicates}개
- 재고 없지만 판매된 항목: {zero_stock_with_sales}개

### 재고 데이터 샘플:
{sample_data}

### 재주문 우선순위가 높은 상품 (상위 10개):
{priority_reorder}

다음 내용을 포함한 종합 분석 보고서를 작성해주세요:

1. 재고 현황 요약 (총 항목 수, 카테고리별 분포, 재고 없는 항목 등)
2. 판매 현황 분석 (판매량 통계, 인기 상품, 판매 부진 상품 등)
3. 재고와 판매량의 상관관계 분석
4. 재주문이 필요한 상품 분석 (우선순위가 높은 상품 강조)
5. 카테고리별 성과 분석
6. 문제점 및 이상 징후 (재고 없는데 판매된 항목, 중복 항목 등)
7. 개선 권장사항 및 비즈니스 인사이트

보고서는 경영진이 이해하기 쉽도록 명확하고 간결하게 작성해주세요.
"""

class InventoryProcessor:
    """재고 데이터 처리를 위한 클래스"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        초기화 함수
        
        Args:
            config_path: 설정 파일 경로 (없으면 기본 설정 사용)
        """
        self.config = self._load_config(config_path)
        self.current_date = str(datetime.datetime.now().date()).replace('-', '')
        
        # 결과 디렉토리 생성
        self.results_dir = Path(self.config.get("results_directory", "results"))
        self.results_dir.mkdir(exist_ok=True)
        
        # 로거 설정
        self.logger = self._setup_logger()
        
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        설정 파일 로드
        
        Args:
            config_path: 설정 파일 경로
            
        Returns:
            설정 정보를 담은 딕셔너리
        """
        default_config = {
            "results_directory": "results",
            "parallel_processing": True,
            "visualization": True
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 기본 설정과 병합
                    default_config.update(config)
            except Exception as e:
                print(f"설정 파일 로드 중 오류 발생: {e}")
        
        return default_config
    
    def _setup_logger(self):
        """로거 설정"""
        logger = logging.getLogger('inventory_processor')
        logger.setLevel(logging.INFO)
        
        # 이미 핸들러가 있는 경우 중복 설정 방지
        if logger.handlers:
            return logger
        
        # 파일 핸들러 추가
        log_dir = Path(self.results_dir) / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"{self.current_date}_processing.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 포맷 설정
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # 핸들러 추가
        logger.addHandler(file_handler)
        
        return logger
    
    def process_inventory_data(self, input_file: str, sales_file: str, output_file: str, intermediate_file: str) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, int]]:
        """
        재고 데이터 처리 메인 함수
        
        Args:
            input_file: 입력 재고 파일 경로
            sales_file: 판매 데이터 파일 경로
            output_file: 출력 파일 경로
            intermediate_file: 중간 결과 파일 경로
            
        Returns:
            정규화된 데이터프레임, 매칭된 데이터프레임, 유효성 검사 결과
        """
        self.logger.info(f"재고 데이터 처리 시작: {input_file}")
        
        # 재고 데이터 로드
        inventory_df = self._load_inventory(input_file)
        
        # 판매 데이터 로드 (있는 경우)
        sales_df = None
        if sales_file and os.path.exists(sales_file):
            self.logger.info(f"판매 데이터 로드 중: {sales_file}")
            try:
                sales_df = self._load_sales_data(sales_file)
            except Exception as e:
                self.logger.error(f"판매 데이터 로드 실패: {e}")
                sales_df = None
        
        # 데이터 정규화
        normalized_df = self._normalize_inventory(inventory_df)
        
        # 판매 데이터와 매칭 (있는 경우)
        matched_df = normalized_df.copy()
        if sales_df is not None:
            matched_df = self._match_with_sales(normalized_df, sales_df)
        
        # 결과 저장
        self._save_results(matched_df, output_file)
        
        # 중간 결과 저장
        if intermediate_file:
            self._save_intermediate(matched_df, intermediate_file)
        
        # 유효성 검사 수행
        validation_results = self._validate_data(matched_df)
        
        self.logger.info("재고 데이터 처리 완료")
        
        # 간단한 디버깅 목적으로 빈 데이터프레임과 결과 반환
        # 실제 구현에서는 실제 데이터로 교체해야 함
        return normalized_df, matched_df, validation_results
    
    def _load_inventory(self, file_path: str) -> pd.DataFrame:
        """재고 데이터 로드"""
        self.logger.info(f"재고 파일 로드 중: {file_path}")
        
        # 예시 구현 - 간단한 빈 데이터프레임 반환
        # 실제 구현에서는 파일에서 데이터 로드 로직 구현
        df = pd.DataFrame({
            "품명": ["상품1", "상품2", "상품3"],
            "위안": [100, 150, 200],
            "수량": [10, 5, 0]
        })
        
        return df
    
    def _load_sales_data(self, file_path: str) -> pd.DataFrame:
        """판매 데이터 로드"""
        # 예시 구현
        df = pd.DataFrame({
            "상품명": ["상품1", "상품2"],
            "판매수량": [2, 3]
        })
        
        return df
    
    def _normalize_inventory(self, df: pd.DataFrame) -> pd.DataFrame:
        """재고 데이터 정규화"""
        # 예시 구현
        return df
    
    def _match_with_sales(self, inventory_df: pd.DataFrame, sales_df: pd.DataFrame) -> pd.DataFrame:
        """재고 데이터와 판매 데이터 매칭"""
        # 예시 구현
        return inventory_df
    
    def _save_results(self, df: pd.DataFrame, output_path: str) -> None:
        """결과 저장"""
        self.logger.info(f"결과 저장 중: {output_path}")
        
        # 예시 구현 - 실제로는 엑셀 파일로 저장
        try:
            directory = os.path.dirname(output_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                
            df.to_excel(output_path, index=False)
            self.logger.info(f"결과 저장 완료: {output_path}")
        except Exception as e:
            self.logger.error(f"결과 저장 실패: {e}")
    
    def _save_intermediate(self, df: pd.DataFrame, output_path: str) -> None:
        """중간 결과 저장"""
        # 예시 구현
        try:
            directory = os.path.dirname(output_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                
            df.to_excel(output_path, index=False)
        except Exception as e:
            self.logger.error(f"중간 결과 저장 실패: {e}")
    
    def _validate_data(self, df: pd.DataFrame) -> Dict[str, int]:
        """데이터 유효성 검사"""
        # 예시 구현 - 실제 구현에서는 실제 데이터 검증 로직 구현
        results = {
            "total_items": len(df),
            "reorder_needed": 1,  # 예시 값
            "zero_inventory": 1,  # 예시 값
            "duplicates": 0,
            "zero_stock_with_sales": 0
        }
        
        return results

class InventoryApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        
        # 환경 설정
        self.config_dir = setup_environment()
        
        # 로거 설정
        self.logger = setup_logger()
        
        # 커스텀 폰트 로드
        self.load_custom_font()
        
        # 앱 설정
        self.title("재고 관리 시스템")
        self.geometry("900x700")
        self.minsize(800, 600)
        
        # 아이콘 설정 (있는 경우)
        try:
            self.iconbitmap(resource_path("resources/icon.ico"))
        except:
            pass
        
        # 파스텔 톤 핑크 스타일 설정
        self.setup_pastel_pink_style()
        
        # 탭 컨트롤
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 탭 생성
        self.tab1 = ttk.Frame(self.notebook)  # 재고 처리 탭
        self.tab2 = ttk.Frame(self.notebook)  # 설정 탭
        self.tab3 = ttk.Frame(self.notebook)  # AI 프롬프트 탭
        self.tab4 = ttk.Frame(self.notebook)  # 로그 및 결과 탭
        
        self.notebook.add(self.tab1, text="재고 처리")
        self.notebook.add(self.tab2, text="설정")
        self.notebook.add(self.tab3, text="AI 프롬프트")
        self.notebook.add(self.tab4, text="로그 및 결과")
        
        # 상태 표시줄 설정
        self.status_var = tk.StringVar()
        self.status_var.set("준비")
        self.status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 로그 텍스트 위젯 생성 (전역)
        self.log_text = None
        
        # 탭 내용 설정
        self.setup_processing_tab()
        self.setup_settings_tab()
        self.setup_prompt_tab()  # 새로운 AI 프롬프트 탭
        self.setup_log_tab()
        
        # 기본 프롬프트 템플릿 로드
        self.load_prompt_template()
    
    def load_custom_font(self):
        """커스텀 폰트 로드"""
        try:
            # NotoSansKR 폰트 파일 경로
            font_path = os.path.join(os.path.dirname(__file__), "resources", "NotoSansKR-VariableFont_wght.ttf")
            
            # 폰트 등록
            font_id = font.add_file(font_path)
            
            # 표준 글꼴도 등록
            ongleaf_font_path = os.path.join(os.path.dirname(__file__), "resources", "온글잎 박다현체.ttf")
            if os.path.exists(ongleaf_font_path):
                font.add_file(ongleaf_font_path)
            
            self.custom_font_loaded = True
            self.logger.info("커스텀 폰트 로드 완료")
        except Exception as e:
            self.custom_font_loaded = False
            self.logger.error(f"폰트 로드 중 오류 발생: {e}")
    
    def setup_pastel_pink_style(self):
        """파스텔 톤 핑크 스타일 설정"""
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # 파스텔 핑크 색상 정의
        pastel_pink = "#FFD1DC"        # 메인 파스텔 핑크
        light_pink = "#FFF0F5"         # 밝은 핑크 (배경)
        dark_pink = "#FFAFBE"          # 진한 핑크 (강조)
        accent_pink = "#FF85A2"        # 액센트 핑크 (버튼 호버)
        
        # 폰트 설정
        font_family = "온글잎 박다현체" if hasattr(self, 'custom_font_loaded') and self.custom_font_loaded else '맑은 고딕'
        
        # TFrame 설정
        self.style.configure("TFrame", background=light_pink)
        self.style.configure("TLabelframe", background=light_pink)
        self.style.configure("TLabelframe.Label", background=light_pink, foreground="#333333", font=(font_family, 9, 'bold'))
        
        # TButton 설정
        self.style.configure("TButton", background=pastel_pink, foreground="#333333", font=(font_family, 9))
        self.style.map("TButton",
                      foreground=[('pressed', '#333333'), ('active', '#333333')],
                      background=[('pressed', accent_pink), ('active', dark_pink)])
        
        # TLabel 설정
        self.style.configure("TLabel", background=light_pink, foreground="#333333", font=(font_family, 9))
        
        # TEntry 설정
        self.style.configure("TEntry", fieldbackground="white", background="white", foreground="#333333", font=(font_family, 9))
        
        # TCheckbutton 설정
        self.style.configure("TCheckbutton", background=light_pink, foreground="#333333", font=(font_family, 9))
        
        # TNotebook 설정
        self.style.configure("TNotebook", background=light_pink, tabposition='n')
        self.style.configure("TNotebook.Tab", background=light_pink, foreground="#333333", padding=[10, 2], font=(font_family, 9))
        self.style.map("TNotebook.Tab",
                      foreground=[('selected', '#333333')],
                      background=[('selected', pastel_pink), ('active', dark_pink)])
        
        # TProgressbar 설정
        self.style.configure("Horizontal.TProgressbar", background=accent_pink, troughcolor=light_pink)
        
        # 애플리케이션 배경색 설정
        self.configure(background=light_pink)
        
        # 텍스트 위젯 폰트 설정
        self.option_add("*Text.font", (font_family, 9))
        self.option_add("*ScrolledText.font", (font_family, 9))
    
    def setup_processing_tab(self):
        """파일 처리 탭 설정 - 개선된 레이아웃"""
        # 메인 컨테이너 - 좌우 분할
        main_container = ttk.Frame(self.tab1)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 왼쪽 프레임 (파일 선택 및 옵션)
        left_frame = ttk.Frame(main_container)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 오른쪽 프레임 (진행상황 및 로그)
        right_frame = ttk.Frame(main_container)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # === 왼쪽 프레임 내용 (파일 선택 및 옵션) ===
        # 파일 선택 프레임
        file_frame = ttk.LabelFrame(left_frame, text="파일 선택")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 재고 파일 선택
        ttk.Label(file_frame, text="재고 파일:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.inventory_file_var = tk.StringVar()
        inventory_entry = ttk.Entry(file_frame, textvariable=self.inventory_file_var, width=35)
        inventory_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="찾아보기", command=lambda: self.browse_file(self.inventory_file_var)).grid(row=0, column=2, padx=5, pady=5)
        
        # 드래그 앤 드롭 기능 추가 (재고 파일)
        try:
            inventory_entry.drop_target_register(DND_FILES)
            inventory_entry.dnd_bind('<<Drop>>', lambda e: self.drop_file(e, self.inventory_file_var))
        except Exception as e:
            self.logger.error(f"드래그 앤 드롭 등록 오류: {e}")
        
        # 판매 데이터 파일 선택
        ttk.Label(file_frame, text="판매 데이터 파일:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.sales_file_var = tk.StringVar()
        sales_entry = ttk.Entry(file_frame, textvariable=self.sales_file_var, width=35)
        sales_entry.grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="찾아보기", command=lambda: self.browse_file(self.sales_file_var)).grid(row=1, column=2, padx=5, pady=5)
        
        # 드래그 앤 드롭 기능 추가 (판매 데이터 파일)
        try:
            sales_entry.drop_target_register(DND_FILES)
            sales_entry.dnd_bind('<<Drop>>', lambda e: self.drop_file(e, self.sales_file_var))
        except Exception as e:
            self.logger.error(f"드래그 앤 드롭 등록 오류: {e}")
        
        # 출력 디렉토리 선택
        ttk.Label(file_frame, text="결과 저장 폴더:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.output_dir_var = tk.StringVar()
        self.output_dir_var.set("results")
        output_entry = ttk.Entry(file_frame, textvariable=self.output_dir_var, width=35)
        output_entry.grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="찾아보기", command=self.browse_directory).grid(row=2, column=2, padx=5, pady=5)
        
        # 드래그 앤 드롭 기능 추가 (출력 디렉토리)
        try:
            output_entry.drop_target_register(DND_FILES)
            output_entry.dnd_bind('<<Drop>>', lambda e: self.drop_directory(e))
        except Exception as e:
            self.logger.error(f"드래그 앤 드롭 등록 오류: {e}")
        
        # 옵션 프레임
        option_frame = ttk.LabelFrame(left_frame, text="처리 옵션")
        option_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 체크박스들을 가로로 한 줄에 배치
        # 시각화 옵션
        self.visualization_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(option_frame, text="데이터 시각화 생성", variable=self.visualization_var).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        # 병렬 처리 옵션
        self.parallel_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(option_frame, text="병렬 처리 사용", variable=self.parallel_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # AI 분석 옵션
        self.ai_analysis_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(option_frame, text="AI 분석 수행", variable=self.ai_analysis_var).grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        
        # 실행 버튼
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="재고 처리 시작", command=self.process_inventory, width=20).pack(side=tk.RIGHT, padx=5, pady=5)
        
        # 진행 상황 표시
        progress_frame = ttk.LabelFrame(right_frame, text="진행 상황")
        progress_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        self.progress_text = scrolledtext.ScrolledText(progress_frame, height=10)
        self.progress_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.progress_text.config(state=tk.DISABLED)
    
    def setup_settings_tab(self):
        """설정 탭 설정"""
        frame = ttk.Frame(self.tab2)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # API 키 설정 프레임
        api_frame = ttk.LabelFrame(frame, text="API 키 설정")
        api_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # API 키 입력
        ttk.Label(api_frame, text="GEMINI API 키:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.api_key_var = tk.StringVar()
        api_entry = ttk.Entry(api_frame, textvariable=self.api_key_var, width=50)
        api_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # API 키 저장 버튼
        ttk.Button(api_frame, text="저장", command=self.save_api_key).grid(row=0, column=2, padx=5, pady=5)
        
        # 저장된 API 키 로드
        self.load_api_key()
        
        # 기타 설정 프레임
        other_frame = ttk.LabelFrame(frame, text="기타 설정")
        other_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 업데이트 확인 옵션
        self.check_update_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(other_frame, text="시작 시 업데이트 확인", variable=self.check_update_var).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        # 폰트 설정
        ttk.Label(other_frame, text="폰트 크기:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        # 폰트 크기 선택 콤보박스
        self.font_size_var = tk.StringVar(value="10")
        font_sizes = ["8", "9", "10", "11", "12", "14", "16"]
        font_combo = ttk.Combobox(other_frame, textvariable=self.font_size_var, values=font_sizes, width=5, state="readonly")
        font_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 설정 저장 버튼
        ttk.Button(frame, text="설정 저장", command=self.save_settings).pack(anchor=tk.E, padx=5, pady=10)
    
    def save_api_key(self):
        """API 키 저장"""
        api_key = self.api_key_var.get().strip()
        
        # API 키 저장 경로
        api_key_path = os.path.join(self.config_dir, "api_key.txt")
        
        # API 키 저장
        try:
            with open(api_key_path, 'w', encoding='utf-8') as f:
                f.write(api_key)
            
            # 환경 변수에도 설정
            os.environ["GEMINI_API_KEY"] = api_key
            
            self.log("API 키가 저장되었습니다.")
            messagebox.showinfo("성공", "API 키가 저장되었습니다.")
        except Exception as e:
            self.log(f"API 키 저장 중 오류 발생: {e}")
            messagebox.showerror("오류", f"API 키 저장 중 오류가 발생했습니다: {e}")

    def load_api_key(self):
        """저장된 API 키 불러오기"""
        api_key_path = os.path.join(self.config_dir, "api_key.txt")
        
        if os.path.exists(api_key_path):
            try:
                with open(api_key_path, 'r', encoding='utf-8') as f:
                    api_key = f.read().strip()
                    self.api_key_var.set(api_key)
                    
                    # 환경 변수에도 설정
                    os.environ["GEMINI_API_KEY"] = api_key
            except Exception as e:
                self.logger.error(f"API 키 로드 중 오류: {e}")

    def save_settings(self):
        """기타 설정 저장"""
        settings = {
            "check_update": self.check_update_var.get(),
            "font_size": self.font_size_var.get()
        }
        
        settings_path = os.path.join(self.config_dir, "settings.json")
        
        try:
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            
            self.log("설정이 저장되었습니다.")
            messagebox.showinfo("성공", "설정이 저장되었습니다.")
        except Exception as e:
            self.log(f"설정 저장 중 오류 발생: {e}")
            messagebox.showerror("오류", f"설정 저장 중 오류가 발생했습니다: {e}")
    
    def setup_prompt_tab(self):
        """AI 프롬프트 탭 설정"""
        frame = ttk.Frame(self.tab3)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 안내 레이블
        ttk.Label(frame, text="GEMINI AI 분석을 위한 프롬프트 템플릿을 수정하세요:", 
                  font=('Noto Sans KR', 10, 'bold')).pack(anchor=tk.W, padx=5, pady=5)
        
        # 설명 텍스트
        description = """사용 가능한 변수:
- {total_items} - 총 항목 수
- {reorder_needed} - 재주문 필요 항목 수
- {zero_inventory} - 재고 없는 항목 수
- {duplicates} - 중복 항목 수
- {zero_stock_with_sales} - 재고 없지만 판매된 항목 수

프롬프트는 GEMINI AI에게 전달되어 분석 보고서를 생성합니다."""
        
        ttk.Label(frame, text=description, wraplength=800, justify='left').pack(anchor=tk.W, padx=5, pady=5)
        
        # 프롬프트 편집 영역
        prompt_frame = ttk.LabelFrame(frame, text="프롬프트 템플릿")
        prompt_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 스크롤 텍스트 위젯
        self.prompt_text = scrolledtext.ScrolledText(prompt_frame, wrap=tk.WORD, height=20)
        self.prompt_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 버튼 프레임
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 기본값 복원 버튼
        ttk.Button(button_frame, text="기본값 복원", command=self.reset_prompt_template, width=15).pack(side=tk.LEFT, padx=5, pady=5)
        
        # 저장 버튼
        ttk.Button(button_frame, text="템플릿 저장", command=self.save_prompt_template, width=15).pack(side=tk.RIGHT, padx=5, pady=5)
        
    def setup_log_tab(self):
        """로그 및 결과 탭 설정"""
        frame = ttk.Frame(self.tab4)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 로그 표시 프레임
        log_frame = ttk.LabelFrame(frame, text="처리 로그")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 로그 텍스트 위젯 (전역 변수 사용)
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=20)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text.config(state=tk.DISABLED)
        
        # 버튼 프레임
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 로그 지우기 버튼
        ttk.Button(button_frame, text="로그 지우기", command=self.clear_log, width=15).pack(side=tk.LEFT, padx=5, pady=5)
        
        # 결과 폴더 열기 버튼
        ttk.Button(button_frame, text="결과 폴더 열기", command=self.open_results_folder, width=15).pack(side=tk.RIGHT, padx=5, pady=5)
    
    def browse_directory(self):
        """출력 디렉토리 선택"""
        directory = filedialog.askdirectory(title="결과 저장 폴더 선택")
        if directory:
            self.output_dir_var.set(directory)
            
    def process_inventory(self):
        """재고 처리 시작"""
        # 입력 파일 확인
        inventory_file = self.inventory_file_var.get().strip()
        if not inventory_file:
            # 오늘 날짜로 기본 파일명 생성
            today = datetime.datetime.now().strftime('%Y%m%d')
            inventory_file = f"{today}_재고파일.xlsx"
            self.inventory_file_var.set(inventory_file)
            
            if not os.path.exists(inventory_file):
                messagebox.showwarning("경고", f"재고 파일이 지정되지 않았습니다. 기본 파일({inventory_file})이 존재하지 않습니다.")
                return

    def clear_log(self):
        """로그 텍스트 지우기"""
        if self.log_text:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete(1.0, tk.END)
            self.log_text.config(state=tk.DISABLED)

    def open_results_folder(self):
        """결과 폴더 열기"""
        output_dir = self.output_dir_var.get().strip()
        if not output_dir:
            output_dir = "results"
        if os.path.exists(output_dir):
            os.startfile(output_dir)
        else:
            messagebox.showwarning("경고", "결과 폴더가 존재하지 않습니다.")
        
    def load_prompt_template(self):
        """프롬프트 템플릿 로드"""
        template_path = os.path.join(self.config_dir, "prompt_template.txt")
        
        default_template = """재고 데이터 분석 보고서를 작성해주세요.

    ## 재고 현황 요약
    - 총 항목 수: {total_items}개
    - 재주문 필요 항목: {reorder_needed}개
    - 재고 없는 항목: {zero_inventory}개
    - 중복 항목: {duplicates}개
    - 재고 없지만 판매된 항목: {zero_stock_with_sales}개

    ## 분석 요청 사항
    1. 재고 현황에 대한 전반적인 평가
    2. 재고 관리 효율성 분석
    3. 재주문이 필요한 상품에 대한 제안
    4. 재고 관리 개선을 위한 제안

    보고서는 마크다운 형식으로 작성해주세요."""
            
        try:
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    template = f.read()
            else:
                template = default_template
                # 기본 템플릿 저장
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(template)
        except Exception as e:
            print(f"프롬프트 템플릿 로드 중 오류: {e}")
            template = default_template
        
        # 템플릿 설정
        if hasattr(self, 'prompt_text'):
            self.prompt_text.delete(1.0, tk.END)
            self.prompt_text.insert(tk.END, template)
    
    def save_prompt_template(self):
        """프롬프트 템플릿 저장"""
        template_path = os.path.join(self.config_dir, "prompt_template.txt")
        
        try:
            template = self.prompt_text.get(1.0, tk.END).strip()
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(template)
            messagebox.showinfo("성공", "프롬프트 템플릿이 저장되었습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"프롬프트 템플릿 저장 중 오류가 발생했습니다: {e}")
    
    def reset_prompt_template(self):
        """프롬프트 템플릿 기본값으로 복원"""
        default_template = """재고 데이터 분석 보고서를 작성해주세요.

## 재고 현황 요약
- 총 항목 수: {total_items}개
- 재주문 필요 항목: {reorder_needed}개
- 재고 없는 항목: {zero_inventory}개
- 중복 항목: {duplicates}개
- 재고 없지만 판매된 항목: {zero_stock_with_sales}개

## 분석 요청 사항
1. 재고 현황에 대한 전반적인 평가
2. 재고 관리 효율성 분석
3. 재주문이 필요한 상품에 대한 제안
4. 재고 관리 개선을 위한 제안

보고서는 마크다운 형식으로 작성해주세요."""
        
        if messagebox.askyesno("확인", "프롬프트 템플릿을 기본값으로 복원하시겠습니까?"):
            self.prompt_text.delete(1.0, tk.END)
            self.prompt_text.insert(tk.END, default_template)
            self.save_prompt_template()
    
    def process_inventory(self):
        """재고 처리 시작"""
        # 입력 파일 확인
        inventory_file = self.inventory_file_var.get().strip()
        if not inventory_file:
            # 오늘 날짜로 기본 파일명 생성
            today = datetime.datetime.now().strftime('%Y%m%d')
            inventory_file = f"{today}_재고파일.xlsx"
            self.inventory_file_var.set(inventory_file)
            
            if not os.path.exists(inventory_file):
                messagebox.showwarning("경고", f"재고 파일이 지정되지 않았습니다. 기본 파일({inventory_file})이 존재하지 않습니다.")
                return
        
        # 판매 데이터 파일 확인
        sales_file = self.sales_file_var.get().strip()
        if not sales_file:
            # 오늘 날짜로 기본 파일명 생성
            today = datetime.datetime.now().strftime('%Y%m%d')
            sales_file = f"{today}_61sec.csv"
            self.sales_file_var.set(sales_file)
        
        # 출력 디렉토리 확인
        output_dir = self.output_dir_var.get().strip()
        if not output_dir:
            output_dir = "results"
            self.output_dir_var.set(output_dir)
        
        # 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        
        # 옵션 설정
        visualization = self.visualization_var.get()
        parallel = self.parallel_var.get()
        ai_analysis = self.ai_analysis_var.get()
        
        # 프롬프트 템플릿 저장
        self.save_prompt_template()
        
        # 상태 업데이트
        self.status_var.set("처리 중...")
        self.progress_var.set(0)
        
        # 로그 초기화
        self.log("재고 처리 시작")
        self.log(f"재고 파일: {inventory_file}")
        self.log(f"판매 데이터 파일: {sales_file}")
        self.log(f"결과 저장 폴더: {output_dir}")
        self.log(f"옵션: 시각화={visualization}, 병렬처리={parallel}, AI분석={ai_analysis}")
        
        # 별도 스레드에서 처리
        threading.Thread(target=self.run_processing, args=(
            inventory_file, sales_file, output_dir, visualization, parallel, ai_analysis
        )).start()
    
    def run_processing(self, inventory_file, sales_file, output_dir, visualization, parallel, ai_analysis):
        """별도 스레드에서 재고 처리 실행"""
        try:
            # 진행 상황 업데이트
            self.progress_var.set(5)
            self.log("처리 준비 중...")
            
            # 출력 디렉토리 생성
            os.makedirs(output_dir, exist_ok=True)
            
            # 현재 날짜 설정
            today_date = datetime.datetime.now().strftime('%Y%m%d')
            
            # 출력 파일 경로 설정
            output_file = os.path.join(output_dir, f"{today_date}_podong_automation.xlsx")
            match_file = os.path.join(output_dir, f"{today_date}_stock_match.xlsx")
            
            # 에러 로그 파일 경로 설정
            error_path = os.path.join(output_dir, "error.txt")
            
            # 에러 로그 초기화
            with open(error_path, 'w', encoding='utf-8') as f:
                f.write(f"재고 처리 에러 로그 - {datetime.datetime.now()}\n\n")
            self.log(f"에러 로그 파일이 생성되었습니다: {error_path}")
            
            # API 키 설정 (AI 분석용)
            if ai_analysis:
                api_key = os.environ.get("GEMINI_API_KEY", "")
                if api_key:
                    genai.configure(api_key=api_key)
            
            self.progress_var.set(10)
            self.log("재고 처리기 초기화 중...")
            
            # 설정 파일 경로
            config_path = os.path.join(self.config_dir, "config.json")
            
            # 기본 설정 생성
            default_config = {
                "results_directory": output_dir,
                "parallel_processing": parallel,
                "visualization": visualization
            }
            
            # 설정 파일 저장
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            
            self.progress_var.set(15)
            self.log("InventoryProcessor 인스턴스 생성 중...")
            
            # InventoryProcessor 인스턴스 생성
            processor = InventoryProcessor(config_path)
            
            self.progress_var.set(20)
            self.log("데이터 로드 및 처리 중...")
            
            try:
                # 재고 데이터 처리
                normalized_df, matched_df, validation_results = processor.process_inventory_data(
                    input_file=inventory_file,
                    sales_file=sales_file,
                    output_file=output_file,
                    intermediate_file=match_file
                )
            except Exception as proc_error:
                # 처리 중 에러 발생 시 에러 로그에 기록
                self.log(f"데이터 처리 중 오류 발생: {proc_error}")
                
                with open(error_path, 'a', encoding='utf-8') as f:
                    f.write(f"데이터 처리 중 오류 발생: {proc_error}\n")
                    f.write(f"상세 오류 정보:\n{traceback.format_exc()}\n\n")
                
                raise  # 에러 다시 발생시켜 상위 except로 전달
            
            self.progress_var.set(70)
            self.log("데이터 처리 완료")
            
            # 결과 요약 로깅
            self.log(f"총 항목 수: {validation_results.get('total_items', 0)}개")
            self.log(f"재주문 필요 항목: {validation_results.get('reorder_needed', 0)}개")
            
            # 재주문 필요 항목 목록 변수 초기화
            reorder_items_list = []
            
            # 재주문이 필요한 항목 이름 추출 (matched_df에서)
            if 'reorder_needed' in matched_df.columns and 'item_names' in matched_df.columns:
                reorder_items = matched_df[matched_df['reorder_needed'] == True]
                if not reorder_items.empty:
                    # 재주문 필요 항목 이름 목록 생성
                    reorder_items_list = reorder_items['item_names'].tolist()
                    
                    # 로그에 재주문 필요 항목 이름 기록
                    self.log("재주문이 필요한 항목 목록:")
                    for item in reorder_items_list[:10]:  # 상위 10개만 로그에 표시
                        self.log(f"- {item}")
                    if len(reorder_items_list) > 10:
                        self.log(f"... 외 {len(reorder_items_list)-10}개 항목")
                    
                    # 에러 로그 파일에도 재주문 필요 항목 기록
                    with open(error_path, 'a', encoding='utf-8') as f:
                        f.write("\n재주문이 필요한 항목 목록:\n")
                        for i, item in enumerate(reorder_items_list, 1):
                            f.write(f"{i}. {item}\n")
            
            self.log(f"재고 없는 항목: {validation_results.get('zero_inventory', 0)}개")
            
            # AI 분석 수행 (선택적)
            if ai_analysis:
                self.progress_var.set(80)
                self.log("AI 분석 수행 중...")
                
                try:
                    # 보고서 경로 설정 - txt 확장자로 변경
                    report_path = os.path.join(output_dir, f"{today_date}_analysis_report.txt")
                    
                    # Gemini 모델 설정
                    model = genai.GenerativeModel('gemini-2.0-flash')
                    
                    # 프롬프트 템플릿 가져오기
                    template_path = os.path.join(self.config_dir, "prompt_template.txt")
                    
                    if os.path.exists(template_path):
                        with open(template_path, 'r', encoding='utf-8') as f:
                            prompt_template = f.read()
                    else:
                        # 기본 프롬프트 사용
                        prompt_template = """재고 데이터 분석 보고서를 작성해주세요.
                        
## 재고 현황 요약
- 총 항목 수: {total_items}개
- 재주문 필요 항목: {reorder_needed}개
- 재고 없는 항목: {zero_inventory}개
- 중복 항목: {duplicates}개
- 재고 없지만 판매된 항목: {zero_stock_with_sales}개

## 재주문이 필요한 항목 목록
{reorder_items}

## 분석 요청 사항
1. 재고 현황에 대한 전반적인 평가
2. 재고 관리 효율성 분석
3. 재주문이 필요한 상품에 대한 제안 (위 목록의 상품들을 재주문해야 함)
4. 재고 관리 개선을 위한 제안

보고서는 일반 텍스트 형식으로 작성해주세요."""
                    
                    # 재주문 필요 항목 목록 문자열 생성
                    reorder_items_str = "재주문이 필요한 항목이 없습니다."
                    if reorder_items_list:
                        reorder_items_str = "\n".join([f"{i}. {item}" for i, item in enumerate(reorder_items_list, 1)])
                    
                    # 변수 값 채우기
                    prompt = prompt_template.format(
                        total_items=validation_results.get('total_items', 0),
                        reorder_needed=validation_results.get('reorder_needed', 0),
                        zero_inventory=validation_results.get('zero_inventory', 0),
                        duplicates=validation_results.get('duplicates', 0),
                        zero_stock_with_sales=validation_results.get('zero_stock_with_sales', 0),
                        reorder_items=reorder_items_str
                    )
                    
                    # 에러 로그 파일 내용 읽기
                    error_content = ""
                    try:
                        with open(error_path, 'r', encoding='utf-8') as f:
                            error_content = f.read()
                            self.log(f"에러 로그 파일을 읽었습니다. 길이: {len(error_content)} 글자")
                    except Exception as e:
                        self.log(f"에러 로그 파일 읽기 실패: {e}")
                    
                    # 프롬프트에 에러 로그 내용 추가
                    if error_content:
                        prompt += f"\n\n## 에러 로그 및 주의사항\n다음은 처리 중 발생한 오류 및 주의사항입니다. 이를 분석에 포함해주세요:\n\n{error_content}"
                    
                    # AI 분석 직접 수행 
                    try:
                        response = model.generate_content(prompt)
                        analysis_report = response.text
                        
                        # 보고서 저장 - txt 파일로 저장
                        with open(report_path, 'w', encoding='utf-8') as f:
                            # 제목 및 재고 상태 요약 추가
                            f.write(f"재고 분석 보고서 - {datetime.datetime.now().strftime('%Y-%m-%d')}\n\n")
                            f.write(f"재고 현황 요약\n")
                            f.write(f"- 총 항목 수: {validation_results.get('total_items', 0)}개\n")
                            f.write(f"- 재주문 필요 항목: {validation_results.get('reorder_needed', 0)}개\n")
                            f.write(f"- 재고 없는 항목: {validation_results.get('zero_inventory', 0)}개\n")
                            f.write(f"- 중복 항목: {validation_results.get('duplicates', 0)}개\n")
                            f.write(f"- 재고 없지만 판매된 항목: {validation_results.get('zero_stock_with_sales', 0)}개\n\n")
                            
                            # AI 분석 결과 추가
                            f.write("AI 분석 결과:\n")
                            f.write(analysis_report)
                        
                        self.log("AI 분석 완료")
                        self.log(f"분석 보고서가 저장되었습니다: {report_path}")
                    except Exception as ai_error:
                        self.log(f"AI 분석 중 오류 발생: {ai_error}")
                        
                        # 간단한 보고서라도 생성 - txt 파일로 저장
                        report_path = os.path.join(output_dir, f"{today_date}_analysis_report.txt")
                        with open(report_path, 'w', encoding='utf-8') as f:
                            f.write(f"재고 분석 보고서 - {datetime.datetime.now().strftime('%Y-%m-%d')}\n\n")
                            f.write(f"재고 현황 요약\n")
                            f.write(f"- 총 항목 수: {validation_results.get('total_items', 0)}개\n")
                            f.write(f"- 재주문 필요 항목: {validation_results.get('reorder_needed', 0)}개\n")
                            f.write(f"- 재고 없는 항목: {validation_results.get('zero_inventory', 0)}개\n")
                            f.write(f"- 중복 항목: {validation_results.get('duplicates', 0)}개\n")
                            f.write(f"- 재고 없지만 판매된 항목: {validation_results.get('zero_stock_with_sales', 0)}개\n\n")
                            
                            f.write("상세 분석:\n")
                            f.write("재고 분석이 완료되었습니다. 자세한 내용은 생성된 엑셀 파일을 참고하세요.")
                        
                        self.log("AI 분석 완료")
                        self.log(f"분석 보고서가 저장되었습니다: {report_path}")
                
                except Exception as e:
                    self.log(f"AI 분석 중 오류 발생: {e}")
                    
                    # 간단한 보고서라도 생성 - txt 파일로 저장
                    report_path = os.path.join(output_dir, f"{today_date}_analysis_report.txt")
                    with open(report_path, 'w', encoding='utf-8') as f:
                        f.write(f"재고 분석 보고서 - {datetime.datetime.now().strftime('%Y-%m-%d')}\n\n")
                        f.write(f"재고 현황 요약\n")
                        f.write(f"- 총 항목 수: {validation_results.get('total_items', 0)}개\n")
                        f.write(f"- 재주문 필요 항목: {validation_results.get('reorder_needed', 0)}개\n")
                        f.write(f"- 재고 없는 항목: {validation_results.get('zero_inventory', 0)}개\n")
                        f.write(f"- 중복 항목: {validation_results.get('duplicates', 0)}개\n")
                        f.write(f"- 재고 없지만 판매된 항목: {validation_results.get('zero_stock_with_sales', 0)}개\n\n")
                        
                        f.write("상세 분석:\n")
                        f.write("재고 분석이 완료되었습니다. 자세한 내용은 생성된 엑셀 파일을 참고하세요.")
                    
                    self.log("AI 분석 완료")
                    self.log(f"분석 보고서가 저장되었습니다: {report_path}")
            
            self.progress_var.set(100)
            self.log("모든 처리 완료")
            self.status_var.set("완료")
            
            # 결과 폴더 열기
            if os.path.exists(output_dir):
                os.startfile(output_dir)
            
            messagebox.showinfo("완료", "재고 처리가 완료되었습니다.")
            
        except Exception as e:
            self.log(f"오류 발생: {e}")
            self.status_var.set("오류")
            
            # 상세 오류 정보 로깅
            error_details = traceback.format_exc()
            self.log(f"상세 오류 정보:\n{error_details}")
            
            # 에러 파일에 기록
            try:
                with open(error_path, 'a', encoding='utf-8') as f:
                    f.write(f"치명적 오류 발생: {e}\n")
                    f.write(f"상세 오류 정보:\n{error_details}\n")
            except:
                pass  # 에러 로그 파일 쓰기 실패 시 무시
            
            messagebox.showerror("오류", f"처리 중 오류가 발생했습니다:\n{e}")

    def browse_directory(self):
        """출력 디렉토리 선택"""
        directory = filedialog.askdirectory(title="결과 저장 폴더 선택")
        if directory:
            self.output_dir_var.set(directory)

    def browse_file(self, var):
        """파일 선택"""
        filename = filedialog.askopenfilename(
            title="파일 선택",
            filetypes=[
                ("Excel 파일", "*.xlsx *.xls"),
                ("CSV 파일", "*.csv"),
                ("모든 파일", "*.*")
            ]
        )
        if filename:
            var.set(filename)

    def drop_file(self, event, var):
        """드래그 앤 드롭 이벤트 핸들러"""
        # event.accept() 제거 - TkinterDnD2에서는 필요 없음
        # 파일 경로는 문자열로 직접 전달됨
        file_path = event.data.strip('{}')  # 중괄호 제거
        if file_path:
            var.set(file_path)

    def drop_directory(self, event):
        """드래그 앤 드롭 이벤트 핸들러"""
        # event.accept() 제거 - TkinterDnD2에서는 필요 없음
        directory = event.data.strip('{}')  # 중괄호 제거
        if directory:
            self.output_dir_var.set(directory)

    def log(self, message):
        """애플리케이션 로그에 메시지 추가"""
        # 로그 텍스트 위젯에 메시지 추가
        if self.progress_text:
            self.progress_text.config(state=tk.NORMAL)
            self.progress_text.insert(tk.END, f"{datetime.datetime.now().strftime('%H:%M:%S')} - {message}\n")
            self.progress_text.see(tk.END)
            self.progress_text.config(state=tk.DISABLED)
        
        # 로그 탭의 텍스트 위젯에도 추가
        if self.log_text:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, f"{datetime.datetime.now().strftime('%H:%M:%S')} - {message}\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        
        # 로거에도 기록
        if hasattr(self, 'logger'):
            self.logger.info(message)
        else:
            print(message)

if __name__ == "__main__":
    app = InventoryApp()
    app.mainloop() 