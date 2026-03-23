import pandas as pd
import numpy as np
import re
import datetime
import os
import logging
import json
import concurrent.futures
from typing import Dict, List, Optional, Tuple, Union, Any
import matplotlib.pyplot as plt
import seaborn as sns
import google.generativeai as genai
import os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv('./.env')
genai.configure(api_key=os.getenv('GEMINI_API_KEY_JY'))
model = genai.GenerativeModel('gemini-2.0-flash')

# 로깅 설정
def setup_logger(log_file: str = "inventory_processing.log") -> logging.Logger:
    """로깅 설정을 초기화하고 로거를 반환합니다."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_path = log_dir / log_file
    
    logger = logging.getLogger("inventory_processor")
    logger.setLevel(logging.INFO)
    
    # 핸들러가 이미 있으면 제거
    if logger.handlers:
        logger.handlers.clear()
    
    # 파일 핸들러
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.INFO)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 포맷터
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 로거 초기화
logger = setup_logger()

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
        
        # 열 이름 매핑 설정
        self.column_mapping = self.config.get("column_mapping", {
            "product_name": "품명",
            "price_yuan": "위안",
            "price_won": "원화",
            "quantity": "수량",
            "amount": "금액",
            "total": "총액",
            "note": "비고"
        })
        
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        설정 파일 로드
        
        Args:
            config_path: 설정 파일 경로
            
        Returns:
            설정 정보를 담은 딕셔너리
        """
        default_config = {
            "category_pattern": r'^[0-9]+\.[가-힣]+',
            "inventory_keyword": "재고량",
            "skip_keywords": ["중국이름", "package"],
            "input_file_template": "./{date}_재고파일.xlsx",
            "output_file_template": "./{date}_podong_automation.xlsx",
            "sales_file_template": "./{date}_61sec.csv",
            "match_file_template": "./{date}_stock_match.xlsx",
            "exception_file": "./test/exception_list.json",
            "results_directory": "results",
            "column_widths": {
                "category": 12.75,
                "item_names": 30.13,
                "item_colors": 48.75,
                "item_counts": 16,
                "sale_61sec": 14.25,
                "sale_61sec*2": 16.5,
                "exp_3_weeks_stock": 22.5,
                "order_now": 14.5
            },
            "column_mapping": {
                "product_name": "품명",
                "price_yuan": "위안",
                "price_won": "원화",
                "quantity": "수량",
                "amount": "금액",
                "total": "총액",
                "note": "비고"
            },
            "color_pattern": r'색상\s*:\s*([0-9]+)\.(.+)',
            "parallel_processing": True,
            "max_workers": 4,
            "visualization": True
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='UTF-8-sig') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
                    logger.info(f"설정 파일 로드 완료: {config_path}")
            except Exception as e:
                logger.error(f"설정 파일 로드 실패: {e}")
        
        return default_config
    
    def load_and_preprocess_data(self, file_path: Optional[str] = None) -> pd.DataFrame:
        """
        엑셀 파일을 로드하고 기본 전처리를 수행
        
        Args:
            file_path: 입력 파일 경로 (없으면 기본 템플릿 사용)
            
        Returns:
            전처리된 데이터프레임
        """
        if file_path is None:
            file_path = self.config["input_file_template"].format(date=self.current_date)
        
        logger.info(f"파일 로드 시작: {file_path}")
        
        try:
            # 파일 존재 여부 확인
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
            
            df = pd.read_excel(file_path)
            logger.info(f"파일 로드 완료: {file_path}, 크기: {df.shape}")
            
            # 데이터프레임이 비어있는지 확인
            if df.empty:
                raise ValueError("로드된 데이터프레임이 비어 있습니다.")
            
        except Exception as e:
            logger.error(f"파일 로드 실패: {e}")
            raise
        
        # 헤더 처리
        try:
            product_name_col = self.column_mapping["product_name"]
            
            # 품명 열이 있는 행 찾기
            header_rows = df[df.iloc[:, 6] == product_name_col].index
            if len(header_rows) == 0:
                # 품명 열이 없으면 3번째 행을 헤더로 사용 (기존 코드 호환성)
                if df.shape[0] <= 2:
                    raise ValueError("데이터프레임의 행 수가 충분하지 않습니다.")
                
                df.columns = df.iloc[2]
                df.drop([0, 1, 2], axis=0, inplace=True)
            else:
                header_row = header_rows[0]
                df.columns = df.iloc[header_row]
                df.drop(range(header_row + 1), axis=0, inplace=True)
            
            # NaN 품명 행 제거
            df = df[pd.notna(df[product_name_col])].reset_index(drop=True)
            
            # 열 이름 정리 (NaN 열 이름 처리)
            new_column = []
            count = 0
            for idx, key in enumerate(df.keys()):
                if pd.isna(key):
                    count += 1
                    new_column.append(f"temp_{count}")
                else:
                    new_column.append(key)
            df.columns = new_column
            
            # 데이터 타입 변환 및 정리
            # 숫자 열 변환
            numeric_cols = [self.column_mapping["price_yuan"], self.column_mapping["price_won"]]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            logger.info(f"기본 전처리 완료, 처리 후 크기: {df.shape}")
            return df
            
        except Exception as e:
            logger.error(f"전처리 중 오류 발생: {e}")
            raise
    
    def identify_data_structure(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        데이터 구조를 식별하고 행 유형을 마킹
        
        Args:
            df: 전처리된 데이터프레임
            
        Returns:
            행 유형이 마킹된 데이터프레임
        """
        logger.info("데이터 구조 식별 시작")
        
        try:
            # 행 유형 초기화
            df['row_type'] = 'unknown'
            
            # 카테고리 패턴
            category_pattern = self.config["category_pattern"]
            
            # 재고량 행 식별
            inventory_keyword = self.config["inventory_keyword"]
            product_name_col = self.column_mapping["product_name"]
            
            # 문자열 변환 후 비교
            df.loc[df[product_name_col].astype(str) == inventory_keyword, 'row_type'] = 'inventory'
            
            # 카테고리 행 식별 - 문자열 변환 후 정규식 매칭
            df.loc[df[product_name_col].astype(str).str.match(category_pattern), 'row_type'] = 'category'
            
            # 제품 행 식별 (카테고리도 아니고 재고량도 아닌 행)
            df.loc[(df['row_type'] == 'unknown') & (df[product_name_col].astype(str) != inventory_keyword), 'row_type'] = 'product'
            
            # 건너뛸 키워드가 있는 행 식별
            for keyword in self.config["skip_keywords"]:
                df.loc[df[product_name_col].astype(str) == keyword, 'row_type'] = 'skip'
            
            category_count = df[df['row_type'] == 'category'].shape[0]
            product_count = df[df['row_type'] == 'product'].shape[0]
            inventory_count = df[df['row_type'] == 'inventory'].shape[0]
            
            logger.info(f"데이터 구조 식별 완료: 카테고리 {category_count}개, 제품 {product_count}개, 재고 행 {inventory_count}개")
            
            # 데이터 일관성 검사
            if product_count != inventory_count:
                logger.warning(f"제품 행과 재고 행의 수가 일치하지 않습니다: 제품 {product_count}개, 재고 {inventory_count}개")
            
            return df
            
        except Exception as e:
            logger.error(f"데이터 구조 식별 중 오류 발생: {e}")
            raise
    
    def extract_color_name(self, color_option: Any) -> str:
        """
        색상 옵션에서 색상 이름 추출
        
        Args:
            color_option: 색상 옵션 문자열
            
        Returns:
            추출된 색상 이름
        """
        if not isinstance(color_option, str):
            return str(color_option)
        
        # 색상 패턴 (예: "색상 : 1.타로퍼플")
        color_pattern = self.config.get("color_pattern", r'색상\s*:\s*([0-9]+)\.(.+)')
        match = re.search(color_pattern, color_option)
        
        if match:
            # 색상 이름만 추출 (예: "타로퍼플")
            return match.group(2).strip()
        
        return color_option
    
    def transform_to_normalized_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        계층적 데이터를 정규화된 형식으로 변환
        
        Args:
            df: 행 유형이 마킹된 데이터프레임
            
        Returns:
            정규화된 데이터프레임
        """
        logger.info("데이터 정규화 시작")
        
        try:
            # 임시 열 개수 계산 (temp_1, temp_2, ...)
            temp_columns = [col for col in df.columns if col.startswith('temp_')]
            categories = len(temp_columns) + 1
            
            # 결과 데이터 초기화
            result_data = {
                'category': [], 
                'item_names': [], 
                'item_colors': [], 
                'wian': [], 
                'won': [], 
                'item_counts': []
            }
            
            # 열 이름 매핑
            product_name_col = self.column_mapping["product_name"]
            price_yuan_col = self.column_mapping["price_yuan"]
            price_won_col = self.column_mapping["price_won"]
            
            current_category = None
            current_product = None
            product_colors = []
            
            # 데이터 처리
            for idx in range(len(df)):
                row = df.iloc[idx]
                row_type = row['row_type']
                
                # 건너뛸 행 처리
                if row_type == 'skip':
                    continue
                
                # 카테고리 행 처리
                if row_type == 'category':
                    current_category = row[product_name_col]
                    continue
                
                # 제품 행 처리
                if row_type == 'product':
                    current_product = row[product_name_col]
                    product_colors = []
                    
                    # 색상 옵션 처리
                    for i in range(1, categories):
                        col_name = f'temp_{i}'
                        if col_name not in df.columns or pd.isna(row[col_name]):
                            continue
                        
                        # 색상 이름 추출
                        color_name = self.extract_color_name(row[col_name])
                        product_colors.append((col_name, color_name))
                        
                        # 가격 정보 안전하게 추출
                        try:
                            yuan_price = float(row[price_yuan_col]) if pd.notna(row[price_yuan_col]) else 0.0
                            won_price = float(row[price_won_col]) if pd.notna(row[price_won_col]) else 0.0
                        except (ValueError, TypeError):
                            logger.warning(f"가격 변환 오류 (행 {idx}): {row[price_yuan_col]}, {row[price_won_col]}")
                            yuan_price = 0.0
                            won_price = 0.0
                        
                        result_data['item_colors'].append(color_name)
                        result_data['item_names'].append(current_product)
                        result_data['wian'].append(yuan_price)
                        result_data['won'].append(won_price)
                        result_data['category'].append(current_category)
                
                # 재고 행 처리
                if row_type == 'inventory':
                    # 이전 행이 제품 행인지 확인
                    if idx == 0 or df.iloc[idx-1]['row_type'] != 'product':
                        logger.warning(f"재고 행 앞에 제품 행이 없습니다 (행 {idx})")
                        continue
                    
                    # 재고량 처리
                    for col_name, color_name in product_colors:
                        # 재고량을 정수로 변환 (오류 시 0으로 처리)
                        try:
                            count = int(row[col_name]) if pd.notna(row[col_name]) else 0
                            # 음수 재고 검사
                            if count < 0:
                                logger.warning(f"음수 재고량 발견 (행 {idx}, 열 {col_name}): {count}")
                                count = 0
                        except (ValueError, TypeError):
                            logger.warning(f"재고량 변환 오류 (행 {idx}, 열 {col_name}): {row[col_name]}")
                            count = 0
                        
                        result_data['item_counts'].append(count)
            
            # 데이터 일관성 검사
            for key, values in result_data.items():
                if len(values) != len(result_data['item_names']):
                    logger.error(f"데이터 불일치: {key} {len(values)}개, item_names {len(result_data['item_names'])}개")
                    raise ValueError(f"데이터 불일치: {key}와 item_names의 개수가 일치하지 않습니다.")
            
            # 데이터프레임 생성
            result_df = pd.DataFrame(result_data)
            logger.info(f"데이터 정규화 완료: {result_df.shape[0]}개 항목")
            return result_df
            
        except Exception as e:
            logger.error(f"데이터 정규화 중 오류 발생: {e}")
            raise
    
    def process_sales_item(self, args: Tuple[int, pd.Series, pd.DataFrame, Dict, np.ndarray]) -> Tuple[int, List[str]]:
        """
        판매 항목 처리 (병렬 처리용)
        
        Args:
            args: (인덱스, 판매 데이터 행, 재고 데이터, 예외 목록, 판매량 배열) 튜플
            
        Returns:
            (인덱스, 오류 메시지 목록) 튜플
        """
        idx, sec61_data, stock_data, exception_list, stock_61sec = args
        error_messages = []
        
        try:
            # 특수 케이스 처리
            if sec61_data['상품명'] == 'No.500':
                return idx, error_messages
            
            status = 0  # 0: 일반 매칭, 1: 특수 처리됨
            
            # 더블스퀘어링 특수 처리
            if sec61_data['상품명'] == '더블스퀘어링' and '더블스퀘어링' in exception_list:
                status = 1
                # 공통옵션에 대한 재고 감소
                common_option = exception_list['더블스퀘어링'].get('공통옵션')
                if common_option:
                    common_option_stock = stock_data[(stock_data['item_names'] == '더블스퀘어링') & 
                                                    (stock_data['item_colors'] == common_option)]
                    if not common_option_stock.empty:
                        common_option_stock_idx = common_option_stock.index[0]
                        stock_61sec[common_option_stock_idx] += sec61_data['판매수량']
                
                # 추가옵션 처리
                if "추가옵션" in sec61_data['옵션'] and sec61_data['옵션'] in exception_list['더블스퀘어링']:
                    except_data = exception_list['더블스퀘어링'][sec61_data['옵션']]
                    if isinstance(except_data, list) and len(except_data) >= 2:
                        stock_match = stock_data[(stock_data['item_names'] == except_data[0]) & 
                                               (stock_data['item_colors'] == except_data[1])]
                        if not stock_match.empty:
                            stock_idx = stock_match.index[0]
                            stock_61sec[stock_idx] += sec61_data['판매수량']
            
            # 사각 집게핀 특수 처리
            if sec61_data['상품명'] == '사각 집게핀' and '스타일' in sec61_data['옵션']:
                extra_option = sec61_data['옵션'].split('\n')
                if len(extra_option) > 1:
                    sec61_data = sec61_data.copy()  # 원본 데이터 변경 방지
                    sec61_data['옵션'] = extra_option[1]
                    if 'L size' in extra_option[0]:
                        sec61_data['상품명'] = '사각 집게핀 (L size)'
                    else:
                        sec61_data['상품명'] = '사각 집게핀 (S size)'
            
            # No.13 하프 특수 처리
            if sec61_data['상품명'] == 'No.13' and '하프' in sec61_data['옵션']:
                sec61_data = sec61_data.copy()  # 원본 데이터 변경 방지
                sec61_data['상품명'] = 'No.13 하프'
                sec61_data['옵션'] = sec61_data['옵션'].replace('하프', '').replace('  ', ' ')
            
            if status == 1:
                return idx, error_messages
            
            # 예외 목록 처리
            if sec61_data['상품명'] in exception_list:
                for except_option, except_data in exception_list[sec61_data['상품명']].items():
                    if sec61_data['옵션'] == except_option:
                        status = 1
                        if isinstance(except_data, list):
                            for item in except_data:
                                if isinstance(item, list) and len(item) >= 2:
                                    stock_match = stock_data[(stock_data['item_names'] == item[0]) & 
                                                   (stock_data['item_colors'] == item[1])]
                                    if not stock_match.empty:
                                        stock_idx = stock_match.index[0]
                                        stock_61sec[stock_idx] += sec61_data['판매수량']
            
            if status == 1:
                return idx, error_messages
            
            # 일반 매칭
            match_data = stock_data[(stock_data['item_names'] == sec61_data['상품명']) & 
                                   (stock_data['item_colors'] == sec61_data['옵션'])]
            
            if match_data.empty:
                error_msg = f"{sec61_data['상품명']} {sec61_data['옵션']} `추가 안됨`"
                error_messages.append(error_msg)
            else:
                stock_idx = match_data.index[0]
                stock_61sec[stock_idx] += sec61_data['판매수량']
        
        except Exception as e:
            error_msg = f"판매 데이터 매칭 오류 (행 {idx}): {e}"
            error_messages.append(error_msg)
            logger.error(error_msg, exc_info=True)
        
        return idx, error_messages
    
    def match_with_sales_data(self, stock_data: pd.DataFrame, sales_file: Optional[str] = None) -> pd.DataFrame:
        """
        재고 데이터와 판매 데이터를 매칭
        
        Args:
            stock_data: 정규화된 재고 데이터
            sales_file: 판매 데이터 파일 경로 (없으면 기본 템플릿 사용)
            
        Returns:
            판매 데이터가 매칭된 데이터프레임
        """
        logger.info("판매 데이터 매칭 시작")
        
        try:
            # 판매 데이터 파일 경로
            if sales_file is None:
                sales_file = self.config["sales_file_template"].format(date=self.current_date)
            
            # 파일 존재 여부 확인
            if not os.path.exists(sales_file):
                logger.warning(f"판매 데이터 파일이 존재하지 않습니다: {sales_file}")
                # 판매 데이터 없이 진행
                new_stock = stock_data.copy()
                new_stock['sale_61sec'] = 0
                new_stock['sale_61sec*2'] = 0
                new_stock['exp_3_weeks_stock'] = np.inf
                new_stock['order_now'] = 0
                return new_stock
            
            # 예외 목록 로드
            exception_file = self.config["exception_file"]
            try:
                if os.path.exists(exception_file):
                    with open(exception_file, 'r', encoding='UTF-8-sig') as file:
                        exception_list = json.load(file)
                    logger.info(f"예외 목록 로드 완료: {exception_file}")
                else:
                    logger.warning(f"예외 목록 파일이 존재하지 않습니다: {exception_file}")
                    exception_list = {}
            except Exception as e:
                logger.error(f"예외 목록 로드 실패: {e}")
                exception_list = {}
            
            # 판매 데이터 로드
            try:
                sale_61sec = pd.read_csv(sales_file)
                logger.info(f"판매 데이터 로드 완료: {sales_file}, 크기: {sale_61sec.shape}")
            except Exception as e:
                logger.error(f"판매 데이터 로드 실패: {e}")
                raise
            
            # 재고 데이터 복사
            new_stock = stock_data.copy()
            stock_61sec = np.zeros(shape=(len(new_stock),), dtype=int)
            
            # 오류 로그 초기화
            error_log = []
            
            # 병렬 처리 여부 확인
            use_parallel = self.config.get("parallel_processing", False)
            max_workers = self.config.get("max_workers", 4)
            
            if use_parallel and len(sale_61sec) > 100:  # 데이터가 충분히 많을 때만 병렬 처리
                logger.info(f"병렬 처리 시작 (최대 작업자: {max_workers})")
                
                # 작업 준비
                tasks = [(idx, row, new_stock, exception_list, stock_61sec) 
                         for idx, row in sale_61sec.iterrows()]
                
                # 병렬 처리 실행
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    results = list(executor.map(self.process_sales_item, tasks))
                
                # 결과 처리
                for _, messages in results:
                    error_log.extend(messages)
            else:
                # 순차 처리
                for idx, sec61_data in sale_61sec.iterrows():
                    _, messages = self.process_sales_item((idx, sec61_data, new_stock, exception_list, stock_61sec))
                    error_log.extend(messages)
            
            # 오류 로그 저장
            if error_log:
                error_log_path = self.results_dir / "error.txt"
                with open(error_log_path, "w+", encoding='utf-8') as f:
                    f.write("\n".join(error_log))
                logger.info(f"오류 로그 저장 완료: {error_log_path}")
            
            # 판매 데이터 추가
            new_stock['sale_61sec'] = stock_61sec
            new_stock['sale_61sec*2'] = stock_61sec * 2
            
            # 재주문 필요 여부 계산
            with np.errstate(divide='ignore', invalid='ignore'):
                temp_order = np.where(new_stock['sale_61sec*2'] > 0, 
                                     np.round(new_stock['item_counts'] / new_stock['sale_61sec*2'], 2),
                                     np.inf)
            
            new_stock['exp_3_weeks_stock'] = temp_order
            order_now = np.zeros(shape=(len(new_stock),), dtype=int)
            order_now[np.where(temp_order <= 1.5)] = 1
            new_stock['order_now'] = order_now
            
            # 불필요한 열 제거
            if 'wian' in new_stock.columns:
                del new_stock['wian']
            if 'won' in new_stock.columns:
                del new_stock['won']
            
            logger.info(f"판매 데이터 매칭 완료: {sum(stock_61sec)}개 판매 항목 매칭됨")
            
            # 데이터 시각화 (선택적)
            if self.config.get("visualization", False):
                self.visualize_data(new_stock)
            
            return new_stock
            
        except Exception as e:
            logger.error(f"판매 데이터 매칭 중 오류 발생: {e}", exc_info=True)
            raise
    
    def visualize_data(self, data: pd.DataFrame) -> None:
        """
        데이터 시각화 함수
        
        Args:
            data: 시각화할 데이터프레임
        """
        try:
            logger.info("데이터 시각화 시작")
            
            # 한글 폰트 설정
            plt.rcParams['font.family'] = 'Malgun Gothic'  # 윈도우의 경우
            plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지
            
            # 결과 디렉토리 생성
            viz_dir = self.results_dir / "visualizations"
            viz_dir.mkdir(exist_ok=True)
            
            # 1. 카테고리별 항목 수 시각화
            plt.figure(figsize=(12, 6))
            category_counts = data['category'].value_counts()
            sns.barplot(x=category_counts.index, y=category_counts.values)
            plt.title('카테고리별 항목 수')
            plt.xlabel('카테고리')
            plt.ylabel('항목 수')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(viz_dir / "category_counts.png")
            plt.close()
            
            # 2. 재고량 분포 시각화
            plt.figure(figsize=(10, 6))
            sns.histplot(data['item_counts'], bins=20, kde=True)
            plt.title('재고량 분포')
            plt.xlabel('재고량')
            plt.ylabel('빈도')
            plt.tight_layout()
            plt.savefig(viz_dir / "inventory_distribution.png")
            plt.close()
            
            # 3. 판매량 vs 재고량 산점도
            if 'sale_61sec' in data.columns:
                plt.figure(figsize=(10, 6))
                sns.scatterplot(x='sale_61sec', y='item_counts', data=data)
                plt.title('판매량 vs 재고량')
                plt.xlabel('판매량')
                plt.ylabel('재고량')
                plt.tight_layout()
                plt.savefig(viz_dir / "sales_vs_inventory.png")
                plt.close()
            
            # 4. 재주문 필요 항목 비율 파이 차트
            if 'order_now' in data.columns:
                plt.figure(figsize=(8, 8))
                order_counts = data['order_now'].value_counts()
                labels = ['재주문 불필요', '재주문 필요']
                plt.pie(order_counts, labels=labels, autopct='%1.1f%%', startangle=90)
                plt.title('재주문 필요 항목 비율')
                plt.axis('equal')
                plt.tight_layout()
                plt.savefig(viz_dir / "reorder_ratio.png")
                plt.close()
            
            logger.info(f"데이터 시각화 완료: {viz_dir}")
            
        except Exception as e:
            logger.error(f"데이터 시각화 중 오류 발생: {e}", exc_info=True)
    
    def save_to_excel(self, df: pd.DataFrame, output_file: Optional[str] = None) -> str:
        """
        데이터프레임을 엑셀 파일로 저장
        
        Args:
            df: 저장할 데이터프레임
            output_file: 출력 파일 경로 (없으면 기본 템플릿 사용)
            
        Returns:
            저장된 파일 경로
        """
        logger.info("엑셀 파일 저장 시작")
        
        try:
            # 출력 파일 경로
            if output_file is None:
                output_file = self.config["match_file_template"].format(date=self.current_date)
            
            # 출력 디렉토리 확인 및 생성
            output_path = Path(output_file)
            output_path.parent.mkdir(exist_ok=True, parents=True)
            
            # 엑셀 작성기 생성
            with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
                # 데이터 저장
                df.to_excel(writer, index=False)
                ws = writer.sheets['Sheet1']
                
                # 열 너비 설정
                for i, col in enumerate(df.columns):
                    width = self.config["column_widths"].get(col, 15)  # 기본값 15
                    ws.set_column(i, i, width)
                
                # 필터 및 고정 행 설정
                ws.autofilter(0, 0, df.shape[0] - 1, df.shape[1] - 1)
                ws.freeze_panes(1, 0)
                
                # 조건부 서식 추가 (재주문 필요 항목 강조)
                order_now_col = df.columns.get_loc('order_now')
                if order_now_col >= 0:
                    format_reorder = writer.book.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
                    ws.conditional_format(1, order_now_col, df.shape[0], order_now_col, {
                        'type': 'cell',
                        'criteria': 'equal to',
                        'value': 1,
                        'format': format_reorder
                    })
            
            logger.info(f"엑셀 파일 저장 완료: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"엑셀 파일 저장 중 오류 발생: {e}", exc_info=True)
            raise
    
    def validate_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        데이터 유효성 검증
        
        Args:
            df: 검증할 데이터프레임
            
        Returns:
            검증 결과를 담은 딕셔너리
        """
        logger.info("데이터 유효성 검증 시작")
        
        validation_results = {
            'total_items': len(df),
            'missing_categories': df[df['category'].isna()].shape[0],
            'missing_product_names': df[df['item_names'].isna()].shape[0],
            'missing_colors': df[df['item_colors'].isna()].shape[0],
            'negative_inventory': df[df['item_counts'] < 0].shape[0],
            'zero_inventory': df[df['item_counts'] == 0].shape[0],
            'reorder_needed': df[df['order_now'] == 1].shape[0],
            'duplicates': df.duplicated(['item_names', 'item_colors']).sum()
        }
        
        # 중복 항목 확인
        if validation_results['duplicates'] > 0:
            duplicates = df[df.duplicated(['item_names', 'item_colors'], keep=False)]
            logger.warning(f"중복 항목 발견: {validation_results['duplicates']}개")
            logger.debug(f"중복 항목:\n{duplicates[['item_names', 'item_colors']]}")
        
        # 재고가 0이지만 판매량이 있는 항목 확인
        zero_stock_with_sales = df[(df['item_counts'] == 0) & (df['sale_61sec'] > 0)]
        validation_results['zero_stock_with_sales'] = len(zero_stock_with_sales)
        
        if validation_results['zero_stock_with_sales'] > 0:
            logger.warning(f"재고가 0이지만 판매량이 있는 항목: {validation_results['zero_stock_with_sales']}개")
        
        logger.info(f"데이터 유효성 검증 완료: {validation_results}")
        return validation_results
    
    def process_inventory_data(self, 
                              input_file: Optional[str] = None, 
                              sales_file: Optional[str] = None,
                              output_file: Optional[str] = None,
                              intermediate_file: Optional[str] = None) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        재고 데이터 처리 파이프라인
        
        Args:
            input_file: 입력 재고 파일 경로
            sales_file: 판매 데이터 파일 경로
            output_file: 최종 출력 파일 경로
            intermediate_file: 중간 결과 파일 경로
            
        Returns:
            (정규화된 재고 데이터, 판매 데이터가 매칭된 재고 데이터, 검증 결과) 튜플
        """
        logger.info("재고 데이터 처리 파이프라인 시작")
        
        try:
            # 1. 데이터 로드 및 기본 전처리
            df = self.load_and_preprocess_data(input_file)
            
            # 2. 데이터 구조 식별
            df = self.identify_data_structure(df)
            
            # 3. 정규화된 형식으로 변환
            normalized_df = self.transform_to_normalized_format(df)
            
            # 중간 결과 저장 (선택적)
            if intermediate_file:
                intermediate_path = Path(intermediate_file)
                intermediate_path.parent.mkdir(exist_ok=True, parents=True)
                normalized_df.to_excel(intermediate_file, index=False)
                logger.info(f"중간 결과 저장 완료: {intermediate_file}")
            
            # 4. 판매 데이터 매칭
            matched_df = self.match_with_sales_data(normalized_df, sales_file)
            
            # 5. 데이터 유효성 검증
            validation_results = self.validate_data(matched_df)
            
            # 6. 결과 저장
            if output_file is not None:
                self.save_to_excel(matched_df, output_file)
            
            logger.info("재고 데이터 처리 파이프라인 완료")
            return normalized_df, matched_df, validation_results
            
        except Exception as e:
            logger.error(f"재고 데이터 처리 중 오류 발생: {e}", exc_info=True)
            raise

def analyze_inventory_with_ai(log_path: str, stock_match_path: str, output_path: Optional[str] = None, error_path: Optional[str] = None) -> str:
    """
    AI를 사용하여 로그 파일과 재고 매칭 파일을 분석하고 상품에 대한 인사이트를 제공하는 보고서를 생성합니다.
    
    Args:
        log_path: 분석할 로그 파일 경로
        stock_match_path: 분석할 재고 매칭 파일 경로
        output_path: 분석 보고서 저장 경로 (없으면 저장하지 않음)
        error_path: 에러 로그 파일 경로 (없으면 분석하지 않음)
        
    Returns:
        분석 보고서 내용
    """
    try:
        # 로그 파일 읽기 - 다양한 인코딩 시도
        logger.info(f"로그 파일 분석 시작: {log_path}")
        log_content = ""
        encodings = ['utf-8', 'cp949', 'euc-kr', 'latin1']
        
        for encoding in encodings:
            try:
                with open(log_path, 'r', encoding=encoding) as f:
                    log_content = f.read()
                logger.info(f"로그 파일을 {encoding} 인코딩으로 성공적으로 읽었습니다.")
                break
            except UnicodeDecodeError:
                logger.warning(f"{encoding} 인코딩으로 읽기 실패, 다음 인코딩 시도 중...")
                continue
        
        if not log_content:
            error_msg = "모든 인코딩 시도가 실패했습니다. 로그 파일을 읽을 수 없습니다."
            logger.error(error_msg)
            return error_msg
            
        # 재고 매칭 파일 읽기
        logger.info(f"재고 매칭 파일 분석 시작: {stock_match_path}")
        try:
            stock_df = pd.read_excel(stock_match_path)
            
            # 재주문 필요 상품 계산 (재고량이 2주 예상 판매량보다 적은 경우)
            reorder_item_names = []
            if 'item_counts' in stock_df.columns and 'sale_61sec' in stock_df.columns:
                # 2주 예상 판매량 계산
                stock_df['expected_sales_2weeks'] = stock_df['sale_61sec'] * 2
                
                # 재주문 필요 여부 계산 (재고량이 2주 예상 판매량보다 적은 경우)
                stock_df['reorder_needed'] = stock_df['item_counts'] < stock_df['expected_sales_2weeks']
                
                # 재주문 필요 상품 목록
                reorder_products = stock_df[stock_df['reorder_needed'] == True]
                
                # 재주문 우선순위 계산 (재고 부족 정도에 따라)
                if not reorder_products.empty:
                    reorder_products['shortage'] = reorder_products['expected_sales_2weeks'] - reorder_products['item_counts']
                    reorder_products['shortage_percentage'] = (reorder_products['shortage'] / reorder_products['expected_sales_2weeks']) * 100
                    reorder_products = reorder_products.sort_values(by='shortage_percentage', ascending=False)
                    
                    # 재주문이 필요한 상품 이름 추출
                    reorder_item_names = reorder_products[['item_names', 'item_colors', 'shortage_percentage']].values.tolist()
            
            # 데이터프레임 정보 추출
            stock_info = {
                "total_items": len(stock_df),
                "categories": stock_df['category'].nunique() if 'category' in stock_df.columns else 0,
                "zero_inventory": len(stock_df[stock_df['item_counts'] == 0]) if 'item_counts' in stock_df.columns else 0,
                "columns": list(stock_df.columns),
                "sample_data": stock_df.head(5).to_dict(orient='records') if not stock_df.empty else []
            }
            
            # 카테고리별 상품 수
            if 'category' in stock_df.columns:
                category_counts = stock_df['category'].value_counts().to_dict()
                stock_info["category_counts"] = category_counts
            
            # 재고량 통계
            if 'item_counts' in stock_df.columns:
                stock_info["inventory_stats"] = {
                    "mean": float(stock_df['item_counts'].mean()),
                    "median": float(stock_df['item_counts'].median()),
                    "min": int(stock_df['item_counts'].min()),
                    "max": int(stock_df['item_counts'].max())
                }
            
            # 판매량 통계
            if 'sale_61sec' in stock_df.columns:
                stock_info["sales_stats"] = {
                    "mean": float(stock_df['sale_61sec'].mean()),
                    "median": float(stock_df['sale_61sec'].median()),
                    "min": int(stock_df['sale_61sec'].min()),
                    "max": int(stock_df['sale_61sec'].max()),
                    "total_sales": int(stock_df['sale_61sec'].sum())
                }
            
            # 재주문 필요 항목 (새로운 기준 적용)
            if 'reorder_needed' in stock_df.columns:
                reorder_count = int(stock_df['reorder_needed'].sum())
                stock_info["reorder_needed"] = reorder_count
                
                # 재주문 필요 상품 상위 10개
                if reorder_count > 0:
                    top_reorder = reorder_products.head(10).to_dict(orient='records')
                    stock_info["top_reorder_products"] = top_reorder
                    
                    # 재주문이 필요한 상품 이름 정보 추가
                    stock_info["reorder_item_details"] = reorder_item_names
            
            # 재고 정보를 JSON 문자열로 변환
            stock_json = json.dumps(stock_info, ensure_ascii=False, indent=2, default=str)
            logger.info("재고 매칭 파일 분석 완료")
            
        except Exception as e:
            logger.error(f"재고 매칭 파일 분석 실패: {e}")
            stock_json = f"재고 매칭 파일 분석 실패: {e}"
        
        # 에러 파일 읽기 - 있는 경우에만
        error_content = ""
        if error_path and os.path.exists(error_path):
            logger.info(f"에러 파일 분석 시작: {error_path}")
            encodings = ['utf-8', 'cp949', 'euc-kr', 'latin1']
            
            for encoding in encodings:
                try:
                    with open(error_path, 'r', encoding=encoding) as f:
                        error_content = f.read()
                    logger.info(f"에러 파일을 {encoding} 인코딩으로 성공적으로 읽었습니다.")
                    break
                except UnicodeDecodeError:
                    logger.warning(f"{encoding} 인코딩으로 읽기 실패, 다음 인코딩 시도 중...")
                    continue
            
            if not error_content:
                logger.warning("모든 인코딩 시도가 실패했습니다. 에러 파일을 읽을 수 없습니다.")
        
        # AI 분석 수행
        prompt = f"""
당신은 재고 관리 전문가입니다. 다음 정보를 분석하여 상품 재고와 판매에 대한 인사이트를 제공하는 보고서를 작성해주세요.

1. 로그 파일 내용:
{log_content}

2. 재고 매칭 파일 분석 결과:
{stock_json}

3. 에러 로그 내용:
{error_content}

재주문 필요 기준: 현재 재고량(item_counts)이 2주 예상 판매량(sale_61sec*2)보다 적은 경우 재주문이 필요합니다.

다음 내용을 포함한 종합 분석 보고서를 작성해주세요:

1. 재고 현황 요약 (총 항목 수, 카테고리별 분포, 재고 없는 항목 등)
2. 판매 현황 분석 (판매량 통계, 인기 상품, 판매 부진 상품 등)
3. 재고와 판매량의 상관관계 분석
4. 재주문이 필요한 상품 분석 (우선순위가 높은 상품 강조 - 상품명과 색상 구체적으로 나열)
5. 카테고리별 성과 분석
6. 문제점 및 이상 징후 (재고 없는데 판매된 항목, 중복 항목 등)
7. 에러 로그 분석 및 주의해야할 사항 요약
8. 개선 권장사항 및 비즈니스 인사이트

보고서는 경영진이 이해하기 쉽도록 명확하고 간결하게 작성해주세요.
"""
        
        logger.info("AI 분석 시작")
        
        # 새로운 모델 인스턴스 생성 (올바른 모델 이름 사용)
        try:
            # 최신 모델 이름 사용
            analysis_model = genai.GenerativeModel('gemini-1.5-pro')
            response = analysis_model.generate_content(prompt)
            analysis_report = response.text
        except Exception as model_error:
            logger.warning(f"gemini-1.5-pro 모델 사용 실패: {model_error}, 다른 모델 시도 중...")
            try:
                # 대체 모델 시도
                analysis_model = genai.GenerativeModel('gemini-pro')
                response = analysis_model.generate_content(prompt)
                analysis_report = response.text
            except Exception as fallback_error:
                logger.error(f"대체 모델도 실패: {fallback_error}")
                return f"AI 모델 오류: {fallback_error}"
        
        logger.info("AI 분석 완료")
        
        # 분석 보고서 저장 (선택적)
        if output_path:
            # 경로에 디렉토리가 포함되어 있으면 디렉토리 생성
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(analysis_report)
                logger.info(f"분석 보고서 저장 완료: {output_path}")
            except Exception as e:
                logger.error(f"분석 보고서 저장 실패: {e}")
                # 현재 디렉토리에 저장 시도
                try:
                    current_path = Path(f"{Path(output_path).name}")
                    with open(current_path, 'w', encoding='utf-8') as f:
                        f.write(analysis_report)
                    logger.info(f"분석 보고서를 현재 디렉토리에 저장했습니다: {current_path}")
                except Exception as e2:
                    logger.error(f"현재 디렉토리에도 저장 실패: {e2}")
        
        return analysis_report
        
    except Exception as e:
        logger.error(f"분석 중 오류 발생: {e}", exc_info=True)
        return f"분석 중 오류가 발생했습니다: {e}"

def main():
    """메인 함수"""
    try:
        # 명령줄 인수 처리
        import argparse
        parser = argparse.ArgumentParser(description='재고 데이터 처리 프로그램')
        parser.add_argument('--config', help='설정 파일 경로')
        parser.add_argument('--input', help='입력 재고 파일 경로 (기본값: 오늘날짜_재고파일.xlsx)')
        parser.add_argument('--sales', help='판매 데이터 파일 경로')
        parser.add_argument('--output', help='출력 파일 경로')
        parser.add_argument('--intermediate', help='중간 결과 파일 경로')
        parser.add_argument('--no-viz', action='store_true', help='시각화 비활성화')
        parser.add_argument('--no-parallel', action='store_true', help='병렬 처리 비활성화')
        parser.add_argument('--analyze-log', action='store_true', help='처리 완료 후 로그 분석 수행')
        args = parser.parse_args()
        
        # 오늘 날짜 형식 설정
        today_date = datetime.datetime.now().strftime('%Y%m%d')
        
        # 설정 파일 로드
        config_path = args.config
        
        # 프로세서 초기화
        processor = InventoryProcessor(config_path)
        
        # 병렬 처리 및 시각화 설정 업데이트
        if args.no_viz:
            processor.config["visualization"] = False
        if args.no_parallel:
            processor.config["parallel_processing"] = False
        
        # 입력 파일 경로 설정 (지정되지 않은 경우 오늘 날짜 기본값 사용)
        input_file = args.input
        if input_file is None:
            input_file = f"{today_date}_재고파일.xlsx"
            print(f"입력 파일이 지정되지 않아 기본값을 사용합니다: {input_file}")
        
        # 데이터 처리 실행
        normalized_df, matched_df, validation_results = processor.process_inventory_data(
            input_file=input_file,
            sales_file=args.sales,
            output_file=args.output,
            intermediate_file=args.intermediate
        )
        
        # 결과 요약 출력
        print("\n===== 처리 결과 요약 =====")
        print(f"총 항목 수: {validation_results['total_items']}개")
        print(f"재주문 필요 항목: {validation_results['reorder_needed']}개")
        print(f"재고 없는 항목: {validation_results['zero_inventory']}개")
        if validation_results.get('duplicates', 0) > 0:
            print(f"중복 항목: {validation_results['duplicates']}개 (주의 필요)")
        if validation_results.get('zero_stock_with_sales', 0) > 0:
            print(f"재고 없지만 판매된 항목: {validation_results['zero_stock_with_sales']}개 (확인 필요)")
        print("==========================\n")
        
        # 로그 분석 (선택적)
        if args.analyze_log:
            log_path = "logs/inventory_processing.log"
            stock_match_path = f"{today_date}_stock_match.xlsx"
            report_path = f"{today_date}_analysis_report.md"
            
            print("\n로그 파일 및 재고 매칭 파일 분석 중...")
            analysis_report = analyze_inventory_with_ai(log_path, stock_match_path, report_path)
            
            print(f"\n===== 분석 보고서 요약 =====")
            # 보고서의 처음 몇 줄만 출력
            summary_lines = analysis_report.split('\n')[:10]
            print('\n'.join(summary_lines))
            print("...")
            print(f"전체 분석 보고서는 {report_path}에 저장되었습니다.")
            print("==========================\n")
        
        return 0
        
    except Exception as e:
        logger.critical(f"프로그램 실행 중 치명적 오류 발생: {e}", exc_info=True)
        print(f"오류 발생: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
