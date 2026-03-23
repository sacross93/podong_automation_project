# 포동 재고관리 자동화

61초 쇼핑몰의 재고 파일과 판매 데이터를 자동으로 매칭하여 주문 필요 품목을 분석하는 데스크탑 앱입니다.

---

## 주요 기능

- **재고 × 판매 자동 매칭** — 재고 Excel 파일과 61초 판매 CSV를 읽어 옵션 단위로 매칭
- **3주치 예상 재고 계산** — 현재 재고 / (판매량 × 2) 기준으로 주문 필요 여부 자동 판단
- **예외 처리 관리** — `exception_list.json` 기반으로 복잡한 옵션(묶음 판매, 다중 옵션 등)을 별도 매핑
- **매칭 실패 이유 제공** — `[재고파일에 상품명 없음]` / `[옵션 불일치] 가능한 옵션: [...]` 형태로 구체적 원인 출력
- **에러 로그 자동 저장** — 처리 후 `logs/error.txt` 에 전체 오류 목록 기록
- **결과 파일 자동 저장** — `YYYYMMDD_stock_match.xlsx` / `.csv` 자동 생성

---

## 화면 구성

| 화면 | 설명 |
|------|------|
| **홈** | 파일 업로드 → 처리 시작 → 대시보드 결과 카드 + 에러 목록 |
| **예외 관리** | exception_list.json 편집 (GUI 편집기 / RAW JSON / 외부 에디터) |

---

## 설치 및 실행

### 요구사항

- Python 3.8.1 이상
- [uv](https://github.com/astral-sh/uv) 패키지 매니저

### 의존성 설치

```bash
uv sync
```

### 앱 실행

```bash
uv run python main.py
```

---

## 사용 방법

1. **재고 파일 선택** — 재고 Excel 파일 (`.xlsx`) 을 클릭하여 선택
2. **판매 데이터 선택** — 61초 판매 CSV (`.csv`) 또는 Excel 파일 선택
3. **처리 시작** 버튼 클릭
4. 처리 완료 후:
   - 결과 요약 카드 (총 품목 / 주문 필요 / 판매 없음 / 오류) 확인
   - 오류 목록에서 매칭 실패 항목과 이유 확인
   - Excel / CSV 다운로드 또는 자동 저장 경로 확인
   - `logs/error.txt` 에서 전체 오류 내용 확인

### 파일 형식

**재고 파일 (Excel)**
- 3번째 행이 헤더 (`품명`, `위안`, `원화` 컬럼 필수)
- 품명 행 → 옵션 색상 행 → 재고량 행 구조

**판매 데이터 (CSV / Excel)**
- `상품명`, `옵션`, `판매수량` 컬럼 필수

---

## 예외 처리 (exception_list.json)

61초 판매 데이터의 옵션명이 재고 파일과 다른 경우 매핑 규칙을 등록합니다.

```json
{
  "상품명": {
    "판매 옵션 텍스트": ["재고 옵션1", "재고 옵션2"]
  }
}
```

앱 내 **예외 관리** 탭에서 GUI로 추가/수정하거나, RAW JSON 편집기를 통해 직접 수정할 수 있습니다.

---

## 프로젝트 구조

```
podong_automation_project/
├── main.py                          # 앱 진입점
├── exception_list.json              # 예외 처리 매핑 규칙
├── pyproject.toml                   # 프로젝트 의존성 정의
│
├── src/
│   ├── core/
│   │   ├── data_processor.py        # 재고 × 판매 매칭 핵심 로직
│   │   ├── file_manager.py          # Excel / CSV 읽기·쓰기
│   │   └── exception_manager.py     # exception_list.json 관리
│   ├── ui/
│   │   ├── main_window.py           # 메인 윈도우 (NavigationRail 기반)
│   │   └── components/
│   │       ├── error_handler.py     # 에러 목록 UI (ExpansionTile)
│   │       └── exception_editor.py  # 예외 처리 편집 다이얼로그
│   └── config/
│       └── settings.py              # 앱 설정
│
├── stock_data_preprocessing/
│   ├── main_match_preprocessing.py  # 스크립트 단독 실행 버전
│   └── stock_control.py
│
├── resources/                       # 폰트 등 정적 리소스
├── tools/                           # 빌드 스크립트 (build_exe.ps1)
└── logs/                            # 런타임 에러 로그 (gitignore 대상)
```

---

## EXE 빌드

```powershell
uv run pyinstaller --onefile --windowed --name PodongApp `
  --add-data "exception_list.json;." `
  --add-data "src;src" `
  --collect-all flet --collect-all flet_desktop `
  --noconfirm main.py
```

빌드 결과물: `dist/PodongApp.exe`

---

## 출력 파일

| 파일 | 설명 |
|------|------|
| `YYYYMMDD_stock_match.xlsx` | 포맷팅 적용된 결과 Excel |
| `YYYYMMDD_stock_match.csv` | CP949 인코딩 결과 CSV |
| `logs/error.txt` | 매칭 실패 항목 및 이유 전체 목록 |

결과 컬럼: `category`, `item_names`, `item_colors`, `item_counts`, `sale_61sec`, `sale_61sec*2`, `exp_3_weeks_stock`, `order_now`

`order_now` 값: `1` = 주문 필요, `0` = 충분, `-1` = 판매 데이터 없음
