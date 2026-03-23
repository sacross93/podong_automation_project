"""
예외 처리 목록 관리를 담당하는 모듈
"""
import json
import os
from typing import Dict, List, Any
import copy
import logging

logger = logging.getLogger(__name__)


class ExceptionManager:
    """예외 처리 목록을 관리하는 클래스"""
    
    def __init__(self, file_path: str = None):
        self.file_path = file_path or "exception_list.json"
        self.exception_data = {}
        self._load_exceptions()
    
    def _load_exceptions(self):
        """예외 처리 목록을 파일에서 로드합니다."""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='UTF-8-sig') as file:
                    self.exception_data = json.load(file)
                logger.info(f"예외 처리 목록 로드 완료: {len(self.exception_data)} 개 항목")
            else:
                logger.warning(f"예외 처리 파일을 찾을 수 없습니다: {self.file_path}")
                self.exception_data = {}
        except Exception as e:
            logger.error(f"예외 처리 목록 로드 오류: {str(e)}")
            self.exception_data = {}
    
    def save_exceptions(self):
        """예외 처리 목록을 파일에 저장합니다."""
        try:
            with open(self.file_path, 'w', encoding='UTF-8-sig') as file:
                json.dump(self.exception_data, file, ensure_ascii=False, indent=2)
            logger.info(f"예외 처리 목록 저장 완료: {self.file_path}")
        except Exception as e:
            logger.error(f"예외 처리 목록 저장 오류: {str(e)}")
            raise

    def set_file_path_and_reload(self, file_path: str):
        """예외 처리 파일 경로를 변경하고 다시 로드합니다."""
        self.file_path = file_path
        self._load_exceptions()
    
    def get_exception_data(self) -> Dict:
        """예외 처리 데이터를 반환합니다."""
        return copy.deepcopy(self.exception_data)
    
    def add_product_exception(self, product_name: str, option: str, stock_items: List[str]):
        """새로운 제품 예외 처리를 추가합니다."""
        if product_name not in self.exception_data:
            self.exception_data[product_name] = {}
        
        self.exception_data[product_name][option] = stock_items
        logger.info(f"예외 처리 추가: {product_name} - {option}")
    
    def remove_product_exception(self, product_name: str, option: str = None):
        """제품 예외 처리를 제거합니다."""
        if product_name in self.exception_data:
            if option is None:
                # 제품 전체 삭제
                del self.exception_data[product_name]
                logger.info(f"예외 처리 제품 삭제: {product_name}")
            elif option in self.exception_data[product_name]:
                # 특정 옵션만 삭제
                del self.exception_data[product_name][option]
                logger.info(f"예외 처리 옵션 삭제: {product_name} - {option}")
                
                # 제품의 모든 옵션이 삭제되면 제품도 삭제
                if not self.exception_data[product_name]:
                    del self.exception_data[product_name]
    
    def get_product_exceptions(self, product_name: str) -> Dict[str, List[str]]:
        """특정 제품의 예외 처리 목록을 반환합니다."""
        return self.exception_data.get(product_name, {}).copy()
    
    def get_all_products(self) -> List[str]:
        """모든 예외 처리 제품 목록을 반환합니다."""
        return list(self.exception_data.keys())
    
    def update_exception_data(self, new_data: Dict):
        """예외 처리 데이터를 전체 업데이트합니다."""
        self.exception_data = copy.deepcopy(new_data)
        logger.info("예외 처리 데이터 전체 업데이트 완료")

    def save_as(self, file_path: str):
        """다른 경로로 저장하고 현재 경로도 해당 파일로 설정합니다."""
        self.file_path = file_path
        self.save_exceptions()
        logger.info(f"예외 처리 목록을 다른 이름으로 저장: {self.file_path}")
    
    def validate_exception_data(self) -> List[str]:
        """예외 처리 데이터의 유효성을 검사합니다."""
        errors = []
        
        for product_name, options in self.exception_data.items():
            if not isinstance(options, dict):
                errors.append(f"제품 '{product_name}': 옵션 데이터가 딕셔너리가 아닙니다")
                continue
            
            for option, stock_items in options.items():
                if not isinstance(stock_items, list):
                    errors.append(f"제품 '{product_name}', 옵션 '{option}': 재고 항목이 리스트가 아닙니다")
                elif not stock_items:
                    errors.append(f"제품 '{product_name}', 옵션 '{option}': 재고 항목이 비어있습니다")
        
        return errors
    
    def search_exceptions(self, search_term: str) -> Dict[str, Dict]:
        """검색어로 예외 처리 항목을 찾습니다."""
        results = {}
        search_term = search_term.lower()
        
        for product_name, options in self.exception_data.items():
            if search_term in product_name.lower():
                results[product_name] = options
            else:
                # 옵션에서 검색
                matching_options = {}
                for option, stock_items in options.items():
                    if (search_term in option.lower() or 
                        any(search_term in item.lower() for item in stock_items)):
                        matching_options[option] = stock_items
                
                if matching_options:
                    results[product_name] = matching_options
        
        return results
