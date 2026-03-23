"""
애플리케이션 설정을 관리하는 모듈
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class AppSettings:
    """애플리케이션 설정 관리 클래스"""
    
    DEFAULT_SETTINGS = {
        "app": {
            "window_width": 1200,
            "window_height": 800,
            "theme_mode": "light",
            "language": "ko"
        },
        "files": {
            "default_output_dir": "./output",
            "exception_list_path": "./config/exception_list.json",
            "auto_backup": True,
            "backup_count": 5
        },
        "processing": {
            "auto_validate_files": True,
            "show_progress": True,
            "max_errors_display": 50
        },
        "logging": {
            "level": "INFO",
            "file_logging": True,
            "log_file": "./logs/app.log"
        }
    }
    
    def __init__(self, config_path: str = "./config/app_settings.json"):
        self.config_path = Path(config_path)
        self.settings = self.DEFAULT_SETTINGS.copy()
        self._load_settings()
        self._ensure_directories()
    
    def _load_settings(self):
        """설정 파일에서 설정을 로드합니다."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    self._merge_settings(self.settings, loaded_settings)
                logger.info(f"설정 파일 로드 완료: {self.config_path}")
            else:
                logger.info("설정 파일이 없어서 기본 설정을 사용합니다.")
                self.save_settings()  # 기본 설정으로 파일 생성
        except Exception as e:
            logger.error(f"설정 파일 로드 오류: {str(e)}")
            logger.info("기본 설정을 사용합니다.")
    
    def _merge_settings(self, default: Dict[str, Any], loaded: Dict[str, Any]):
        """기본 설정과 로드된 설정을 병합합니다."""
        for key, value in loaded.items():
            if key in default:
                if isinstance(value, dict) and isinstance(default[key], dict):
                    self._merge_settings(default[key], value)
                else:
                    default[key] = value
    
    def _ensure_directories(self):
        """필요한 디렉토리들을 생성합니다."""
        try:
            # 설정 디렉토리
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 출력 디렉토리
            output_dir = Path(self.get("files.default_output_dir"))
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 로그 디렉토리
            if self.get("logging.file_logging"):
                log_file = Path(self.get("logging.log_file"))
                log_file.parent.mkdir(parents=True, exist_ok=True)
            
        except Exception as e:
            logger.error(f"디렉토리 생성 오류: {str(e)}")
    
    def get(self, key: str, default=None):
        """설정 값을 가져옵니다. (점 표기법 지원)"""
        keys = key.split('.')
        value = self.settings
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value):
        """설정 값을 저장합니다. (점 표기법 지원)"""
        keys = key.split('.')
        target = self.settings
        
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        
        target[keys[-1]] = value
    
    def save_settings(self):
        """설정을 파일에 저장합니다."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            logger.info(f"설정 저장 완료: {self.config_path}")
        except Exception as e:
            logger.error(f"설정 저장 오류: {str(e)}")
            raise
    
    def reset_to_default(self):
        """설정을 기본값으로 초기화합니다."""
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.save_settings()
        logger.info("설정이 기본값으로 초기화되었습니다.")
    
    def get_all_settings(self) -> Dict[str, Any]:
        """모든 설정을 반환합니다."""
        return self.settings.copy()
    
    def update_settings(self, new_settings: Dict[str, Any]):
        """설정을 일괄 업데이트합니다."""
        self._merge_settings(self.settings, new_settings)
        self.save_settings()


def setup_logging(settings: AppSettings):
    """로깅을 설정합니다."""
    log_level = getattr(logging, settings.get("logging.level", "INFO"))
    
    # 로그 포매터
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 파일 핸들러
    if settings.get("logging.file_logging"):
        try:
            log_file = Path(settings.get("logging.log_file"))
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            logger.error(f"파일 로깅 설정 오류: {str(e)}")


# 전역 설정 인스턴스
app_settings = AppSettings()





