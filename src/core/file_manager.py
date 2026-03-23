"""
파일 관리를 담당하는 모듈
"""
import pandas as pd
import xlsxwriter
import os
import string
import re
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class FileManager:
    """파일 읽기/쓰기를 관리하는 클래스"""
    
    @staticmethod
    def read_excel_file(file_path: str) -> pd.DataFrame:
        """엑셀 파일을 읽습니다."""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
            
            df = pd.read_excel(file_path)
            logger.info(f"엑셀 파일 읽기 완료: {file_path} ({len(df)} 행)")
            return df
        except Exception as e:
            logger.error(f"엑셀 파일 읽기 오류: {str(e)}")
            raise
    
    @staticmethod
    def read_csv_file(file_path: str, encoding: str = 'utf-8') -> pd.DataFrame:
        """CSV 파일을 읽습니다."""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
            
            # 인코딩 자동 감지 시도
            encodings = [encoding, 'utf-8', 'cp949', 'euc-kr']
            df = None
            
            for enc in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=enc)
                    logger.info(f"CSV 파일 읽기 완료: {file_path} ({len(df)} 행, 인코딩: {enc})")
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                raise ValueError(f"지원하는 인코딩으로 파일을 읽을 수 없습니다: {file_path}")
            
            return df
        except Exception as e:
            logger.error(f"CSV 파일 읽기 오류: {str(e)}")
            raise
    
    @staticmethod
    def save_excel_with_formatting(df: pd.DataFrame, file_path: str):
        """포맷팅을 적용하여 엑셀 파일을 저장합니다."""
        try:
            def get_column_width(column_name: str) -> float:
                """컬럼별 최적 너비를 반환합니다."""
                width_map = {
                    'category': 12.75,
                    'item_names': 30.13,
                    'item_colors': 48.75,
                    'item_counts': 16,
                    'sale_61sec': 14.25,
                    'sale_61sec*2': 16.5,
                    'exp_3_weeks_stock': 22.5,
                    'order_now': 14.5
                }
                return width_map.get(column_name, 15.0)
            
            with pd.ExcelWriter(file_path, engine='xlsxwriter', engine_kwargs={'options': {'nan_inf_to_errors': True}}) as writer:
                df.to_excel(writer, index=False, sheet_name='Sheet1')
                
                workbook = writer.book
                worksheet = writer.sheets['Sheet1']
                
                # 헤더 포맷
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#D7E4BC',
                    'border': 1
                })
                
                # 데이터 포맷
                data_format = workbook.add_format({
                    'text_wrap': True,
                    'valign': 'top',
                    'border': 1
                })
                
                # 숫자 포맷
                number_format = workbook.add_format({
                    'num_format': '#,##0',
                    'valign': 'top',
                    'border': 1
                })
                
                # 컬럼별 포맷 및 너비 설정
                for i, column_name in enumerate(df.columns):
                    width = get_column_width(column_name)
                    worksheet.set_column(i, i, width)
                    
                    # 헤더 포맷 적용
                    worksheet.write(0, i, column_name, header_format)
                    
                    # 데이터 포맷 적용
                    if column_name in ['item_counts', 'sale_61sec', 'sale_61sec*2', 'order_now']:
                        for row in range(1, len(df) + 1):
                            worksheet.write(row, i, df.iloc[row-1, i], number_format)
                    else:
                        for row in range(1, len(df) + 1):
                            worksheet.write(row, i, df.iloc[row-1, i], data_format)
                
                # 자동 필터 추가
                worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)
                
                # 첫 행 고정
                worksheet.freeze_panes(1, 0)
            
            logger.info(f"포맷팅된 엑셀 파일 저장 완료: {file_path}")
            
        except Exception as e:
            logger.error(f"엑셀 파일 저장 오류: {str(e)}")
            raise
    
    @staticmethod
    def save_csv_file(df: pd.DataFrame, file_path: str, encoding: str = 'cp949'):
        """CSV 파일을 저장합니다."""
        try:
            df.to_csv(file_path, encoding=encoding, index=False)
            logger.info(f"CSV 파일 저장 완료: {file_path}")
        except Exception as e:
            logger.error(f"CSV 파일 저장 오류: {str(e)}")
            raise
    
    @staticmethod
    def validate_file_structure(file_path: str, file_type: str) -> Tuple[bool, str]:
        """파일 구조의 유효성을 검사합니다."""
        try:
            if file_type == 'stock':
                return FileManager._validate_stock_file(file_path)
            elif file_type == 'sale':
                return FileManager._validate_sale_file(file_path)
            else:
                return False, f"지원하지 않는 파일 타입: {file_type}"
                
        except Exception as e:
            return False, f"파일 검증 오류: {str(e)}"
    
    @staticmethod
    def _validate_stock_file(file_path: str) -> Tuple[bool, str]:
        """재고 파일 구조를 검증합니다."""
        try:
            df = pd.read_excel(file_path)
            
            if len(df) < 3:
                return False, "재고 파일의 데이터가 충분하지 않습니다 (최소 3행 필요)"
            
            # 3행째가 헤더인지 확인
            header_row = df.iloc[2]
            required_columns = ['품명', '위안', '원화']
            
            missing_columns = [col for col in required_columns if col not in header_row.values]
            if missing_columns:
                return False, f"필수 컬럼이 없습니다: {', '.join(missing_columns)}"
            
            return True, "재고 파일 구조가 올바릅니다"
            
        except Exception as e:
            return False, f"재고 파일 검증 오류: {str(e)}"
    
    @staticmethod
    def _validate_sale_file(file_path: str) -> Tuple[bool, str]:
        """판매 파일 구조를 검증합니다. (CSV/엑셀 모두 지원)"""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in [".xlsx", ".xls"]:
                df = pd.read_excel(file_path)
            else:
                df = pd.read_csv(file_path, encoding='cp949')

            required_columns = ['상품명', '옵션', '판매수량']
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                return False, f"필수 컬럼이 없습니다: {', '.join(missing_columns)}"

            # 데이터 타입 검증
            if not pd.api.types.is_numeric_dtype(df['판매수량']):
                return False, "'판매수량' 컬럼이 숫자 형식이 아닙니다"

            return True, "판매 파일 구조가 올바릅니다"

        except Exception as e:
            return False, f"판매 파일 검증 오류: {str(e)}"
    
    @staticmethod
    def get_file_info(file_path: str) -> dict:
        """파일 정보를 반환합니다."""
        try:
            if not os.path.exists(file_path):
                return {"error": "파일을 찾을 수 없습니다"}
            
            stat = os.stat(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()
            
            info = {
                "name": os.path.basename(file_path),
                "size": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified": stat.st_mtime,
                "extension": file_ext
            }
            
            # 파일 내용 미리보기
            if file_ext in ['.xlsx', '.xls']:
                try:
                    df = pd.read_excel(file_path)
                    info["rows"] = len(df)
                    info["columns"] = len(df.columns)
                except:
                    info["preview_error"] = "엑셀 파일을 읽을 수 없습니다"
                    
            elif file_ext == '.csv':
                try:
                    df = FileManager.read_csv_file(file_path)
                    info["rows"] = len(df)
                    info["columns"] = len(df.columns)
                except:
                    info["preview_error"] = "CSV 파일을 읽을 수 없습니다"
            
            return info
            
        except Exception as e:
            return {"error": f"파일 정보 조회 오류: {str(e)}"}
