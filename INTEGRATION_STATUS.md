# CaddyMate GUI × TurtleBot Nav2 통합 현황

## 프로젝트 개요

- 7인치 터치 디스플레이용 노인 친화적 슈퍼마켓 내비게이션 앱
- TurtleBot3 Waffle Pi + ROS2 Jazzy + Nav2로 실제 로봇 이동 구현
- 기반 코드: 팀원 기존 구현 (HTML/Flask 쇼핑 UI)
- 추가 구현: TurtleBot 연동, SLAM 맵 표시, 네비게이션 트리거

---

## 기기 및 네트워크 구성

| 기기 | 호스트명 | IP | 네트워크 | 역할 |
|------|---------|-----|----------|------|
| Dice Machine | aquilablaze | `129.215.3.31` | 대학 유선망 (eno1) | ROS2 Jazzy, Nav2, Cartographer, **rosbridge :9090** |
| TurtleBot | crobat | `192.168.105.74` | SDProbots WiFi (wlan0) | 센서/액추에이터, ROS2 DDS |
| Raspberry Pi | fearow | `192.168.105.222` | SDProbots WiFi (wlan0) | Flask :5000, UI 서빙 |

### 통신 구조

```
[Raspberry Pi (fearow) 192.168.105.222]
  Flask :5000 → UI 서빙
  Browser → ws://129.215.3.31:9090
                        │
       [Dice Machine (aquilablaze) 129.215.3.31]
         rosbridge_websocket :9090
         Nav2 / /goal_pose / /amcl_pose / /plan
                        │
               ROS2 DDS 유니캐스트 (~/DICE.peer)
                        │
           [TurtleBot (crobat) 192.168.105.74]
             LiDAR, 모터
```

- Raspberry Pi → Dice Machine: ping 통신 확인 완료 (avg 22ms)
- rosbridge는 **Dice Machine에 설치 완료**

---

## SLAM 맵 정보

| 항목 | 값 |
|------|-----|
| 파일 | `lobby_final.pgm` + `lobby_final.yaml` |
| 해상도 | 0.05 m/px |
| 크기 | 372 × 278 px = 18.6m × 13.9m |
| 원점 | x: -7.75m, y: -6.35m |
| 유효 좌표 범위 | X: -7.75 ~ +10.85m, Y: -6.35 ~ +7.55m |
| 좌표 변환 | `col = (x_ros + 7.75) / 0.05` / `row = 277 - (y_ros + 6.35) / 0.05` |

---

## 구현 완료 항목

### 신규/수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `ros_config.json` (신규) | `rosbridge_host: 129.215.3.31`, `port: 9090` |
| `requirements.txt` | Pillow 추가 |
| `data/Database_Creator.py` | `x_ros`, `y_ros`, `yaw_ros` 컬럼 추가, 16개 상품에 샘플 좌표 |
| `server.py` | PGM→PNG 변환(`lobby_map.png`), `GET /api/map_info`, `GET /api/ros_config` |
| `items.html` | ROS 좌표 data 속성 전달, `openItemOnMap`에 좌표 포함 |
| `map.html` | SLAM 맵 배경, roslibjs, `/amcl_pose`, `/plan`, `/navigate_to_pose/_action/status` 구독, Navigate 버튼 |

---

## map.html 동작 흐름

```
1. GET /api/map_info → SLAM 모드 활성화
2. lobby_map.png → Konva 배경으로 전체 맵 표시 (전체 fit, 카메라 고정)
3. GET /api/ros_config → ws://129.215.3.31:9090 연결
4. /amcl_pose 구독 → 빨간 원(로봇 현재 위치) 실시간 표시
5. /plan 구독 → 파란 선(Nav2 예상 경로) 실시간 표시
6. 초록 원 = 목표 상품 위치 (ROS 좌표가 있는 상품만 표시)
7. [Navigate] 버튼 클릭
   → /goal_pose PoseStamped 발행
   → /navigate_to_pose/_action/status 구독 시작
8. 도착 판정: status == 4 (SUCCEEDED) 수신 시 도착 오버레이 표시
9. 2.2초 후 이전 화면으로 자동 이동
```

### Nav2 GoalStatus 값

| 값 | 의미 |
|----|------|
| 1 | ACCEPTED |
| 2 | EXECUTING |
| 3 | CANCELING |
| **4** | **SUCCEEDED** ← 도착 판정 기준 |
| 5 | CANCELED |
| 6 | ABORTED |

---

## ROS 좌표가 부여된 데모 상품 (16개)

> 좌표는 3층 로비 SLAM 맵 기준 임의 배치값. 실제 데모 전 측정 후 `Database_Creator.py`의 `item_ros_coords`에서 수정 필요.

| 상품 | x (m) | y (m) | yaw (rad) |
|------|-------|-------|-----------|
| Apples | -4.0 | 2.0 | 0.0 |
| White bread | -1.5 | 4.5 | 0.0 |
| Whole milk | 1.0 | 5.5 | 1.57 |
| Chicken breast | 3.5 | 4.0 | 3.14 |
| Frozen pizza | 5.0 | 2.5 | 0.0 |
| White rice | 6.5 | 0.5 | 1.57 |
| Crisps | 5.0 | -1.5 | 3.14 |
| Still water | 3.0 | -3.0 | 0.0 |
| Red wine | 1.0 | -2.5 | 0.0 |
| Ale | 1.5 | -2.0 | 0.0 |
| Toilet paper | -1.5 | -2.0 | 1.57 |
| Paracetamol | -3.5 | -1.0 | 0.0 |
| Shampoo | -5.0 | 1.0 | 1.57 |
| Nappies | -3.0 | 4.0 | 0.0 |
| Dog food | 7.5 | 3.5 | 3.14 |
| Hummus | 0.0 | 0.5 | 0.0 |

---

## 실행 방법

### Raspberry Pi (매번)

```bash
cd ~/HTML-CaddyMate-GUI-main
python server.py
```

브라우저: `http://localhost:5000`

### Dice Machine (매번, Nav2 launch 이후 별도 터미널)

```bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml port:=9090
```

### DB 갱신 시 (상품 좌표 변경 후)

```bash
python data/Database_Creator.py
```

### 최초 환경 구성 시

```bash
pip install -r requirements.txt
python data/Database_Creator.py
```

---

## 미구현 / 추후 작업

| 항목 | 설명 |
|------|------|
| `search.html` | 원래 팀원도 미구현 상태 |
| 실제 상품 좌표 측정 | 현재 임의 배치 → RViz 등으로 실제 좌표 측정 후 `item_ros_coords` 업데이트 필요 |
| Step 3 (LiDAR 최적화) | 프레임 기둥 masking (`laser_filters`) |
| Step 4 (코너링 최적화) | 90도 이상 회전 구간 파라미터 튜닝 |
| Step 5 | 실제 데모 환경 네비게이션 테스트 |

---

*최종 업데이트: 2026-03-10*
