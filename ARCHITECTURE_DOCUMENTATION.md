# CaddyMate GUI - 아키텍처 및 코드베이스 상세 문서

> 7인치 터치 디스플레이용 노인 친화적 슈퍼마켓 내비게이션 GUI

---

## 1. 전체 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CaddyMate 시스템 구조                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────────────┐   │
│  │   HTML/JS   │────▶│ Flask Server │────▶│  SQLite DB (caddymate_store) │   │
│  │  (프론트엔드) │     │  (백엔드 API) │     │  + store_layout.json       │   │
│  └─────────────┘     └─────────────┘     └─────────────────────────────┘   │
│         │                     │                          │                  │
│         │                     │                          │                  │
│         ▼                     ▼                          ▼                  │
│  • home.html            • /api/categories           categories 테이블       │
│  • browse-categories    • /api/items/<id>            items 테이블            │
│  • items.html           • /api/path (POST)          shelves (폴리곤)        │
│  • map.html             • 정적 파일 서빙               aisles (라벨)          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 기술 스택
| 계층 | 기술 |
|------|------|
| 프론트엔드 | HTML5, Vanilla JavaScript, CSS3, Konva.js (캔버스) |
| 백엔드 | Python Flask 3.0, flask-cors |
| 데이터베이스 | SQLite 3 |
| 빌드/배포 | 없음 (정적 파일 + Flask 직접 서빙) |

---

## 2. 파일 구조 및 역할

### 2.1 프로젝트 디렉터리 구조

```
HTML-CaddyMate-GUI-main/
├── home.html              # 메인 메뉴 페이지
├── browse-categories.html  # 카테고리 목록 페이지
├── items.html             # 카테고리별 상품 목록 페이지
├── map.html               # 매장 지도 + 경로 안내 페이지
├── search.html            # (미구현) 검색 페이지
├── styles.css             # 공통 전역 스타일
├── categories.css         # browse-categories 전용 스타일
├── items.css              # items 전용 스타일
├── server.py              # Flask 백엔드 + 경로 탐색 로직
├── data/
│   ├── Database_Creator.py # DB 스키마 생성 + 시드 데이터
│   └── caddymate_store.db  # SQLite DB (생성됨)
├── layout_generator.py    # store_layout.json 생성 스크립트
├── store_layout.json      # 매장 레이아웃 (선반/통로 좌표)
├── inspect_db.py          # DB 구조 검사 유틸리티
├── start.bat              # Windows 실행 배치 파일
├── requirements.txt       # Python 의존성
└── README.md              # 기본 사용법
```

---

## 3. 백엔드 상세 분석

### 3.1 `server.py` - Flask 서버 및 경로 탐색

**역할**: HTTP API 제공, 정적 파일 서빙, A* 기반 경로 탐색

#### 주요 상수
| 이름 | 값 | 설명 |
|------|-----|------|
| `DB_PATH` | `data/caddymate_store.db` | SQLite DB 경로 |
| `LAYOUT_PATH` | `store_layout.json` | 매장 레이아웃 JSON 경로 |

#### 함수별 상세

##### 1) `parse_point(raw_value)` (라인 27–37)
- **목적**: API 요청에서 `{x, y}` 좌표 객체 파싱
- **입력**: `dict` 또는 비정상 값
- **출력**: `{'x': float, 'y': float}` 또는 `None`
- **동작**: `x`, `y`를 float으로 변환, 실패 시 `None` 반환

##### 2) `point_in_polygon(point_x, point_y, polygon)` (라인 40–57)
- **목적**: 점이 다각형 내부에 있는지 판별 (Ray casting 알고리즘)
- **입력**: 좌표 `(point_x, point_y)`, 꼭짓점 리스트 `polygon`
- **출력**: `True` / `False`
- **용도**: 그리드 셀 중심이 선반(폴리곤) 안에 있으면 장애물로 표시

##### 3) `load_normalized_layout(padding=1.0)` (라인 60–99)
- **목적**: `store_layout.json` 로드 후 정규화
- **동작**:
  - 모든 선반 폴리곤의 min/max x, y 계산
  - padding을 고려해 월드 너비/높이 계산
  - offset_x, offset_y로 좌표 변환해 (0,0) 기준으로 정규화
- **출력**: `{world_width, world_height, shelves}`

##### 4) `point_to_cell(point, grid_resolution)` (라인 102–106)
- **목적**: 월드 좌표 → 그리드 셀 인덱스 변환
- **출력**: `(cell_x, cell_y)` 튜플

##### 5) `cell_center(cell_x, cell_y, grid_resolution)` (라인 109–114)
- **목적**: 셀 인덱스 → 셀 중심 월드 좌표
- **출력**: `{'x': float, 'y': float}`

##### 6) `find_nearest_free_cell(start_cell, blocked_cells, columns, rows)` (라인 116–145)
- **목적**: 시작/목표 셀이 장애물 셀일 경우 가장 가까운 통행 가능 셀 탐색
- **알고리즘**: BFS (Breadth-First Search)
- **반환**: 통행 가능 셀 또는 `None`

##### 7) `reconstruct_cell_path(came_from, end_cell)` (라인 148–157)
- **목적**: A*의 `came_from` 맵으로 끝 셀부터 역순 경로 생성
- **출력**: 셀 좌표 리스트 `[(x,y), ...]`

##### 8) `simplify_points(points)` (라인 160–179)
- **목적**: 같은 축상의 중간 점 제거해 경로 단순화
- **규칙**: 이전–현재–다음 점이 같은 x 또는 같은 y면 현재 점 제거

##### 9) `initialize_grid_cache(grid_resolution=1.0)` (라인 182–210)
- **목적**: 경로 탐색용 그리드 사전 계산 및 캐시
- **캐시 내용**:
  - `blocked_cells`: 선반 폴리곤 내부 셀 집합
  - `columns`, `rows`: 그리드 크기
  - `world_width`, `world_height`, `grid_resolution`, `shelves`
- **호출 시점**: 서버 기동 시, `grid_resolution` 변경 시

##### 10) `find_path(start, end, grid_resolution=1.0)` (라인 213–311)
- **목적**: A* 경로 탐색 (회전 페널티 적용)
- **입력**: `start`, `end` = `{'x': float, 'y': float}` (미터 단위)
- **알고리즘**:
  - 상태: `(cell, direction)` – direction은 `(dx, dy)` 또는 None
  - TURN_PENALTY = 0.5 (방향 전환 시 추가 비용)
  - 휴리스틱: 맨하탄 거리
- **출력**: `{points, grid_resolution, world_width, world_height}` 또는 `None`

##### 11) `get_db_connection()` (라인 312–315)
- **목적**: SQLite 연결 생성, `row_factory`로 딕셔너리 형태 반환

#### API 라우트

| 메서드 | 경로 | 설명 | 요청/응답 |
|--------|------|------|-----------|
| GET | `/` | home.html 제공 | - |
| GET | `/<path>` | 정적 파일 제공 | - |
| GET | `/api/categories` | 전체 카테고리 목록 | JSON 배열 |
| GET | `/api/items/<category_id>` | 카테고리별 상품 목록 | JSON 배열 |
| POST | `/api/path` | 두 점 사이 경로 계산 | Body: `{start:{x,y}, end:{x,y}}` → `{points, meta}` |

---

### 3.2 `data/Database_Creator.py` - DB 생성 스크립트

**역할**: SQLite 스키마 생성 및 시드 데이터 삽입

#### 스키마
```sql
-- categories: 카테고리
id INTEGER PRIMARY KEY AUTOINCREMENT
name TEXT NOT NULL

-- items: 상품
id INTEGER PRIMARY KEY AUTOINCREMENT
name TEXT NOT NULL
category_id INTEGER (FK → categories.id)
aisle TEXT           -- 통로 번호 (예: "1", "7")
aisle_position REAL  -- 통로 내 위치 비율 (0~1)
```

#### 데이터 구조
- **categories**: 15개 카테고리 (Fruit & Vegetables, Bakery, Dairy & Eggs 등)
- **items**: 각 카테고리별 상품 리스트, `(이름, aisle)` 또는 `(이름, aisle, aisle_position)`

#### 주요 로직

##### `parse_aisle_position(raw_value)` (라인 406–415)
- 0~1 범위로 aisle_position 정규화

##### 시드 데이터 삽입 (라인 417–428)
- `aisle_totals`: aisle별 상품 수
- `aisle_seen`: aisle별 이미 넣은 상품 수
- `aisle_position` 미지정 시: `aisle_seen / (total_in_aisle + 1)`로 균등 분배

**주의**: 매 실행 시 `DROP TABLE items`, `DROP TABLE categories` 후 재생성

---

### 3.3 `layout_generator.py` - 매장 레이아웃 생성

**역할**: `store_layout.json` 생성

#### 설정 (라인 4–17)
| 변수 | 값 | 설명 |
|------|-----|------|
| world_width | 60 | 월드 너비 |
| world_height | 50 | 월드 높이 |
| rows | 2 | 통로 행 수 |
| aisles_per_row | 8 | 행당 통로 수 |
| aisle_width | 2.5 | 통로 폭 |
| shelf_depth | 1.2 | 선반 깊이 |
| shelf_length | 16.75 | 선반 길이 |
| row_gap | 4 | 행 간격 |

#### 생성 규칙
- 각 통로마다 좌측/우측 선반 2개 (폴리곤 4점)
- `aisles`: `{label: "A1"~"A16", x: 통로 중심 x, row: 0|1}`

**실행**: `python layout_generator.py` → `store_layout.json` 생성

---

### 3.4 `inspect_db.py` - DB 검사 유틸리티

**역할**: DB 테이블 목록 확인, categories 샘플/컬럼 정보 출력

- `SELECT name FROM sqlite_master WHERE type='table'`
- `PRAGMA table_info(categories)`

---

## 4. 프론트엔드 상세 분석

### 4.1 `home.html` - 메인 메뉴

**역할**: 앱 진입점, 두 가지 주요 기능으로 이동

| 버튼 | 이동 경로 |
|------|-----------|
| Browse Categories | `browse-categories.html` |
| Search Items | `search.html` (미구현) |

- `styles.css` 사용
- `resources/logo.png` 로고 표시

---

### 4.2 `browse-categories.html` - 카테고리 목록

**역할**: API로 카테고리 로드 후 그리드 표시, 클릭 시 해당 카테고리 상품 페이지로 이동

#### JavaScript 핵심

| 함수/상수 | 설명 |
|----------|------|
| `API_URL` | `http://localhost:5000/api` |
| `CATEGORY_CACHE_KEY` | sessionStorage 캐시 키 |
| `CATEGORY_CACHE_TTL_MS` | 5분 (300,000ms) |
| `readCache(key)` | sessionStorage에서 JSON 파싱 |
| `writeCache(key, value)` | `{savedAt, value}` 형태로 저장 |
| `getCategoryIcon(name)` | 카테고리별 이모지 매핑 |
| `renderCategories(container, categories)` | 카테고리 버튼 렌더링 |
| `loadCategories()` | fetch + 캐시 처리 |
| `selectCategory(id, name)` | `items.html?category={id}&name={name}` 로 이동 |

#### 이벤트
- `DOMContentLoaded` → `loadCategories()`
- `categoriesContainer` 클릭 → `.category-button` 클릭 시 `selectCategory()` 호출

---

### 4.3 `items.html` - 카테고리별 상품 목록

**역할**: URL 쿼리로 받은 category 기준 상품 로드, 상품 클릭 시 지도로 이동

#### URL 파라미터
- `category`: 카테고리 ID
- `name`: 카테고리 이름 (제목 표시용)

#### JavaScript 핵심

| 함수/상수 | 설명 |
|----------|------|
| `ITEMS_CACHE_PREFIX` | `items-cache-v1-{categoryId}` |
| `renderItems(container, items)` | 상품 카드 렌더링 (이름, aisle) |
| `loadItems()` | fetch + 캐시 |
| `openItemOnMap(itemName, aisle, aislePosition)` | sessionStorage에 `mapTarget` 저장 후 `map.html`로 이동 |

#### 상품 카드 data 속성
- `data-item-name`, `data-item-aisle`, `data-item-aisle-position`

---

### 4.4 `map.html` - 매장 지도 및 경로 안내

**역할**: Konva.js로 매장 레이아웃 렌더링, 사용자 위치 추적, 목표 지점까지 A* 경로 표시

#### 의존성
- Konva.js (CDN: `https://unpkg.com/konva@9/konva.min.js`)

#### 주요 상수
| 이름 | 값 | 설명 |
|------|-----|------|
| PIXELS_PER_METER | 60 | 1m당 픽셀 |
| ROUTE_UPDATE_INTERVAL_MS | 33 | 경로 재요청 간격 |
| ROUTE_RECALCULATE_DISTANCE_METERS | 0.8 | 이 거리 이상 이동 시 경로 재계산 |
| ARRIVAL_THRESHOLD_METERS | 1.2 | 도착 판정 거리 |
| EXIT_MAP_DELAY_MS | 2200 | 도착 후 이전 화면 복귀 지연 |
| FOLLOW_ZOOM_FACTOR | 3.0 | 카메라 줌 배율 |
| ROTATION_SPEED | 3 | 키보드 회전 속도 (도/프레임) |
| MOVE_SPEED | 0.2 | 키보드 이동 속도 (%/프레임) |

#### 목표 지점 결정
1. URL 쿼리: `item`, `aisle`, `aisle_position`
2. sessionStorage `mapTarget` (items.html에서 설정)

#### 핵심 함수

| 함수 | 역할 |
|------|------|
| `normalizeAisleLabel(value)` | aisle 문자열 정규화 (예: "1" → "A1") |
| `formatAisleDisplay(value)` | 표시용 문자열 (예: "Aisle 1") |
| `parseAislePosition(value)` | 0~1 범위 aisle_position 파싱 |
| `getStoredMapTarget()` | sessionStorage에서 mapTarget 읽기 |
| `updateTargetBanner()` | 상단 배너에 선택된 목표 표시 |
| `worldToScreen(x, y)` | 월드 좌표 → 화면 좌표 |
| `getUserWorldPosition()` | pose 기반 사용자 월드 좌표 |
| `shouldRecalculateRoute()` | 재계산 여부 (0.8m 이상 이동 시) |
| `checkTargetArrival()` | 도착 여부 (1.2m 이내) |
| `centerCameraOn(x, y)` | 카메라 중심 이동 |
| `updateFollowCamera()` | 사용자 위치 따라가기 |
| `syncUser()` | 사용자 마커/화살표 위치 동기화 |
| `upsertTargetMarker()` | 목표 마커/라벨 생성/갱신 |
| `drawRouteLine(routePoints)` | 경로선 그리기 |
| `requestAndRenderPath()` | POST `/api/path` 호출 후 경로 렌더링 |
| `loadLayout()` | store_layout.json 로드 (캐시 사용) |
| `drawLayout(layout)` | 바닥/선반/통로 라벨 그리기, 목표 위치 계산 |

#### 키보드 조작
- W: 전진
- A/D: 좌/우 회전

#### 게임 루프
- `setInterval(..., 1000/60)` → 60 FPS
- 이동/회전 시 카메라 갱신, 도착 검사, 경로 재요청

---

## 5. 스타일시트 분석

### 5.1 `styles.css` - 공통 스타일

| 선택자 | 역할 |
|--------|------|
| `*` | margin/padding 초기화, box-sizing |
| `body` | 전체 레이아웃, 배경색 (#e9eef5) |
| `.container` | 800×455px 카드형 컨테이너 |
| `.logo-area` | 로고 + 타이틀 배치 |
| `h1` | 제목 스타일 |
| `.button-container` | 버튼 세로 배치 |
| `button` | 기본 버튼 (파란 계열, 큰 폰트) |
| `.back-button` | 회색 뒤로가기 버튼 |

### 5.2 `categories.css`

- `.header`: 상단 헤더 레이아웃
- `.categories-grid`: 2열 그리드, 스크롤
- `.category-button`: 카테고리 카드
- `.category-icon`, `.category-text`
- `.loading`, `.error`, `.no-data`
- 커스텀 스크롤바

### 5.3 `items.css`

- `.header`: browse와 유사
- `.items-grid`: 2열 그리드
- `.item-card`: 상품 카드
- `.item-name`, `.item-aisle`

---

## 6. 데이터 흐름 요약

### 6.1 카테고리/상품 조회

```
Browser → GET /api/categories
       → server.py get_categories()
       → SQLite SELECT * FROM categories
       → JSON 응답 → browse-categories.html 렌더링

Browser → GET /api/items/<id>
       → server.py get_items_by_category()
       → SQLite SELECT * FROM items WHERE category_id=?
       → JSON 응답 → items.html 렌더링
```

### 6.2 경로 탐색

```
map.html (사용자 위치 + 목표)
  → POST /api/path { start: {x,y}, end: {x,y} }
  → server.py find_path()
    → load_normalized_layout()
    → initialize_grid_cache() (필요 시)
    → A* 탐색 (그리드, 선반 장애물 회피)
  → { points: [...], meta: {...} }
  → Konva.Line으로 경로선 그리기
```

### 6.3 매장 레이아웃

```
layout_generator.py
  → store_layout.json 생성

map.html / server.py
  → store_layout.json 로드
  → shelves: 선반 폴리곤
  → aisles: 통로 라벨 및 좌표
```

---

## 7. 실행 순서

1. **DB 생성**: `python data/Database_Creator.py` (필요 시)
2. **레이아웃 생성**: `python layout_generator.py` (필요 시)
3. **서버 실행**: `python server.py` 또는 `start.bat`
4. 브라우저에서 `http://localhost:5000` 접속

---

## 8. 미구현 / 개선 포인트

| 항목 | 상태 |
|------|------|
| `search.html` | 미구현 (home에서 링크만 존재) |
| 실기기 위치 추적 | 없음 (키보드 시뮬레이션만) |
| `resources/logo.png` | README에 미언급, 실제 파일 여부 확인 필요 |
| server.py 310–311행 | `return None` 중복 (데드 코드) |

---

## 9. 클래스/모듈 요약 (Python)

이 프로젝트에는 **클래스가 없고** 모두 함수 기반으로 구성되어 있습니다.

| 파일 | 모듈 역할 |
|------|-----------|
| `server.py` | Flask 앱, 경로 탐색 유틸, API 핸들러 |
| `Database_Creator.py` | DB 생성 스크립트 (실행 시 한 번) |
| `layout_generator.py` | JSON 레이아웃 생성 스크립트 |
| `inspect_db.py` | DB 검사 스크립트 |

---

*문서 작성일: 2025-03-10*
