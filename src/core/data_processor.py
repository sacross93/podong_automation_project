"""
데이터 처리 핵심 로직을 담당하는 모듈
"""
import pandas as pd
import numpy as np
import re
import datetime
import os
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class DataProcessor:
    """재고 데이터와 판매 데이터를 처리하는 클래스"""
    
    def __init__(self, date: Optional[str] = None):
        self.date = date or str(datetime.datetime.now().date()).replace('-', '')
        self.stock_data = None
        self.sale_data = None
        self.processed_data = None
        self.errors = []
        
    def process_stock_file(self, file_path: str) -> pd.DataFrame:
        """재고 엑셀 파일을 처리합니다."""
        try:
            logger.info(f"재고 파일 처리 시작: {file_path}")
            
            df = pd.read_excel(file_path)
            df.columns = df.iloc[2]
            df.drop([0, 1, 2], axis=0, inplace=True)
            df = df[pd.isna(df['품명']) == False]
            df = df.reset_index(drop=True)
            
            # 컬럼명 정리
            new_column = []
            count = 0
            for idx, key in enumerate(df.keys()):
                if pd.isna(key):
                    count += 1
                    new_column.append(f"temp_{count}")
                else:
                    new_column.append(key)
            df.columns = new_column
            categories = len(new_column) - 7 + 1
            
            # 데이터 파싱
            append_list = {
                'category': [], 'item_names': [], 'item_colors': [], 
                'wian': [], 'won': [], 'item_counts': []
            }
            
            status = 0
            temp_category = ""
            
            for idx, data in enumerate(df.iloc):
                if data['품명'] == '중국이름' or data['품명'] == 'package':
                    continue
                    
                # 카테고리 감지
                if re.findall(r'^[0-9]\.[가-힝]+', str(data['품명'])):
                    temp_category = data['품명']
                    continue
                    
                if data['품명'] != '재고량':
                    if status != 0:
                        error_msg = f"데이터 구조 오류: 예상치 못한 품명 상태 {status}"
                        self.errors.append(error_msg)
                        logger.error(error_msg)
                        break
                        
                    status = 1
                    temp_item_name = data['품명']
                    
                    for i in range(1, categories):
                        if pd.isna(data[f'temp_{i}']):
                            break
                        append_list['item_colors'].append(data[f'temp_{i}'])
                        append_list['item_names'].append(temp_item_name)
                        append_list['wian'].append(data['위안'])
                        append_list['won'].append(data['원화'])
                        append_list['category'].append(temp_category)
                else:
                    if status != 1:
                        error_msg = f"데이터 구조 오류: 예상치 못한 재고량 상태 {status}"
                        self.errors.append(error_msg)
                        logger.error(error_msg)
                        break
                        
                    status = 0
                    for i in range(1, categories):
                        if pd.isna(data[f'temp_{i}']):
                            break
                        append_list['item_counts'].append(int(data[f"temp_{i}"]))
                        
                    if len(append_list['item_counts']) != len(append_list['item_names']):
                        error_msg = "품목 수와 재고 수량이 맞지 않습니다"
                        self.errors.append(error_msg)
                        logger.error(error_msg)
                        break
            
            self.stock_data = pd.DataFrame(append_list)
            logger.info(f"재고 파일 처리 완료: {len(self.stock_data)} 개 품목")
            return self.stock_data
            
        except Exception as e:
            error_msg = f"재고 파일 처리 오류: {str(e)}"
            self.errors.append(error_msg)
            logger.error(error_msg)
            raise
    
    def process_sale_data(self, sale_data: pd.DataFrame, exception_list: Dict) -> pd.DataFrame:
        """판매 데이터와 재고 데이터를 매칭합니다."""
        try:
            logger.info("판매 데이터 매칭 시작")
            
            if self.stock_data is None:
                raise ValueError("재고 데이터가 먼저 로드되어야 합니다")
            
            new_stock = self.stock_data.copy()
            stock_61sec = np.zeros(shape=(len(new_stock),), dtype=int)
            
            for idx, sec61_data in sale_data.iterrows():
                try:
                    self._process_single_sale_item(sec61_data, exception_list, stock_61sec)
                except Exception as e:
                    error_msg = f"판매 데이터 처리 오류 (행 {idx}): {str(e)}"
                    self.errors.append(error_msg)
                    logger.error(error_msg)
            
            # 결과 계산
            new_stock['sale_61sec'] = stock_61sec
            new_stock['sale_61sec*2'] = stock_61sec * 2
            
            # 3주 예상 재고 계산 (원본 스크립트와 동일한 동작: 0으로 나눌 때 inf 유지)
            temp_order = (new_stock['item_counts'] / new_stock['sale_61sec*2']).round(2)
            new_stock['exp_3_weeks_stock'] = temp_order
            
            # 주문 필요 여부 (원본 스크립트 로직 준수: temp_order > 1.5 → 1)
            order_now = np.zeros(shape=(len(new_stock),), dtype=int)
            order_now[temp_order > 1.5] = 1
            new_stock['order_now'] = order_now
            
            # 불필요한 컬럼 제거
            if 'wian' in new_stock.columns:
                del new_stock['wian']
            if 'won' in new_stock.columns:
                del new_stock['won']
            
            self.processed_data = new_stock
            logger.info(f"판매 데이터 매칭 완료: {len(self.errors)} 개 오류 발생")
            return new_stock
            
        except Exception as e:
            error_msg = f"판매 데이터 매칭 오류: {str(e)}"
            self.errors.append(error_msg)
            logger.error(error_msg)
            raise
    
    def _process_single_sale_item(self, sec61_data: pd.Series, exception_list: Dict, stock_61sec: np.ndarray):
        """단일 판매 항목을 처리합니다."""
        product_name = sec61_data['상품명']
        option = sec61_data['옵션']
        quantity = sec61_data['판매수량']
        
        # 제외 항목
        if product_name == 'No.500':
            return
        
        # 특별 처리: 더블스퀘어링
        if product_name == '더블스퀘어링':
            self._process_double_square_ring(sec61_data, exception_list, stock_61sec)
            return
        
        # 특별 처리: 사각 집게핀
        if product_name == '사각 집게핀' and '스타일' in option:
            product_name, option = self._process_square_clip(sec61_data)
        
        # 특별 처리: No.13 하프
        if product_name == 'No.13' and '하프' in option:
            product_name = 'No.13 하프'
            option = option.replace('하프', '').replace('  ', ' ').strip()
        
        # 예외 목록 처리
        if product_name in exception_list:
            if self._process_exception_item(product_name, option, quantity, exception_list, stock_61sec):
                return
        
        # 일반 매칭
        self._process_normal_matching(product_name, option, quantity, stock_61sec)
    
    def _process_double_square_ring(self, sec61_data: pd.Series, exception_list: Dict, stock_61sec: np.ndarray):
        """더블스퀘어링 특별 처리"""
        if '더블스퀘어링' not in exception_list:
            error_msg = "더블스퀘어링 예외 목록이 없습니다"
            self.errors.append(error_msg)
            return
        
        # 공통 옵션 처리
        common_option = exception_list['더블스퀘어링']['공통옵션']
        match_data = self.stock_data[
            (self.stock_data['item_names'] == '더블스퀘어링') & 
            (self.stock_data['item_colors'] == common_option)
        ]
        
        if len(match_data) > 0:
            stock_idx = match_data.index[0]
            stock_61sec[stock_idx] += sec61_data['판매수량']
        else:
            error_msg = f"더블스퀘어링 공통옵션 '{common_option}'을 재고목록에서 찾을 수 없습니다"
            self.errors.append(error_msg)
        
        # 추가 옵션 처리
        if "추가옵션" in sec61_data['옵션']:
            try:
                except_data = exception_list['더블스퀘어링'][sec61_data['옵션']]
                match_data = self.stock_data[
                    (self.stock_data['item_names'] == except_data[0]) & 
                    (self.stock_data['item_colors'] == except_data[1])
                ]
                
                if len(match_data) > 0:
                    stock_idx = match_data.index[0]
                    stock_61sec[stock_idx] += sec61_data['판매수량']
                else:
                    error_msg = f"더블스퀘어링 추가옵션 '{sec61_data['옵션']}' -> '{except_data}'를 재고목록에서 찾을 수 없습니다"
                    self.errors.append(error_msg)
            except KeyError:
                error_msg = f"더블스퀘어링 추가옵션 '{sec61_data['옵션']}'이 예외 목록에 없습니다"
                self.errors.append(error_msg)
    
    def _process_square_clip(self, sec61_data: pd.Series) -> Tuple[str, str]:
        """사각 집게핀 특별 처리"""
        extra_option = sec61_data['옵션'].split('\n')
        option = extra_option[1]
        
        if 'L size' in extra_option[0]:
            product_name = '사각 집게핀 (L size)'
        else:
            product_name = '사각 집게핀 (S size)'
        
        return product_name, option
    
    def _process_exception_item(self, product_name: str, option: str, quantity: int, 
                               exception_list: Dict, stock_61sec: np.ndarray) -> bool:
        """예외 항목 처리"""
        if option in exception_list[product_name]:
            for except_data in exception_list[product_name][option]:
                match_data = self.stock_data[
                    (self.stock_data['item_names'] == product_name) & 
                    (self.stock_data['item_colors'] == except_data)
                ]
                
                if len(match_data) > 0:
                    stock_idx = match_data.index[0]
                    stock_61sec[stock_idx] += quantity
                else:
                    error_msg = f"예외처리 실패: 상품명 '{product_name}', 옵션 '{option}'에 해당하는 재고 '{except_data}'를 찾을 수 없습니다"
                    self.errors.append(error_msg)
            return True
        return False
    
    def _process_normal_matching(self, product_name: str, option: str, quantity: int, stock_61sec: np.ndarray):
        """일반 매칭 처리"""
        match_data = self.stock_data[
            (self.stock_data['item_names'] == product_name) & 
            (self.stock_data['item_colors'] == option)
        ]
        
        if len(match_data) == 0:
            name_match = self.stock_data[self.stock_data['item_names'] == product_name]
            if len(name_match) == 0:
                reason = "[재고파일에 상품명 없음]"
            else:
                available = name_match['item_colors'].tolist()
                reason = f"[옵션 불일치] 가능한 옵션: {available}"
            error_msg = f"{product_name} / {option} → 추가 안됨 {reason}"
            self.errors.append(error_msg)
        else:
            stock_idx = match_data.index[0]
            stock_61sec[stock_idx] += quantity
    
    def get_errors(self) -> List[str]:
        """발생한 오류 목록을 반환합니다."""
        return self.errors.copy()
    
    def clear_errors(self):
        """오류 목록을 초기화합니다."""
        self.errors.clear()

    def save_error_log(self, log_dir: str = "./logs"):
        """에러 로그를 파일로 저장합니다."""
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "error.txt")
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f"처리 일자: {self.date}\n")
            f.write(f"총 오류: {len(self.errors)}건\n")
            f.write("=" * 60 + "\n\n")
            for i, error in enumerate(self.errors, 1):
                f.write(f"[{i:03d}] {error}\n")
        logger.info(f"에러 로그 저장: {log_path}")
        return os.path.abspath(log_path)

