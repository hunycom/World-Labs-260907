# P3-05 공간 지능 데모 통합 종결 백서 초안 (P3_CLOSE_v1draft)
- 문서 식별자: `docs/p3/P3_CLOSE_v1draft.md`
- 발행 일시: `2026-09-07T04:35:00.000Z`
- 지시서: `[지시서] EXE-260907-P3-05-FIX2`
- 작성 및 검증 주체: Antigravity (수신: Principal, Claude System 2 감사관)
- 기술 명칭 준수: **Marble 생성 자산**, **Spark(World Labs MIT) 위 자체 응용층** (금지 명칭 grep 0건 준수)
- 추가 외부 API 비용: **$0.00**
- 기준 원장: `docs/p3/asset_ledger_p3.sha256` (121행 검증 완료)

## 1. 목표와 3층 구조 (Architecture)
### 1-1. 프로젝트 목표
- 3D Gaussian Splatting 기반 공간 인공지능(Spatial AI) 환경에서 다중 강체 물리 시뮬레이션(Rapier3D) 및 부품 bbox 보정 레이캐스트 픽킹(정책 v2)의 통합 검증.
- 에어갭(Air-gapped) 또는 로컬 엣지 환경에서 외부 API 의존 없이 고정 dt 1/60 s 물리 시뮬레이션 및 기하 정합성 보장 (렌더 FPS: [?] llvmpipe, 미측정).

### 1-2. 3층 시스템 아키텍처
| 계층 구분 | 공식 명칭 규칙 | 핵심 컴포넌트 및 자산 | 주요 역할 및 한계 |
|---|---|---|---|
| 제1계층 (생성층) | **Marble 생성 자산** | World Labs Marble API v1 자산 (`run01_splats.ply`, `run01_500k.spz`, `run01_collider_mesh.glb`, `run01_full_res.spz` / 원장 `docs/p3/raw/marble_assets_sha256.txt`, `run01_pano.png` [? 미등재]) | marble-1.1 텍스트 프롬프트 생성(`docs/p3/marble/run01_response.json`) 및 저해상도 콜라이더 메쉬 생성; 절대 좌표계가 아닌 임의 스케일/원점 모델이므로 실측 지상 검증(Ground Truth) 변환 필요; 다시점 생성은 Task 3 [미확정] |
| 제2계층 (런타임 응용층) | **Spark(World Labs MIT) 위 자체 응용층** | Three.js r180 및 MIT(World Labs Spark, LICENSE SHA: `51829693e5dccd9ca1daa093991faac3aaa93238eb8fd5f5cb4130af85791d64`) 기반 렌더러 위에 구축된 자체 응용 계층 | 3D 공간 분할 파이프라인(색상/바운딩박스/3σ), 부품 bbox 보정 레이캐스트 픽킹(정책 v2), Rapier3D 물리 바인딩(정적 Trimesh 필터링, 평면 바닥 큐보이드 콜라이더, 고정 dt 1/60 s, 물리 스텝 p50 5.98 ms/p95 8.96 ms(CPU, `docs/p3/raw/t6c_scenarios.json`), 렌더 FPS: [?] llvmpipe, 미측정) |
| 제3계층 (납품 및 감사층) | 납품 및 검증층 | 브라우저 단일 실행(Single-Run) 검증 원장, 결정론적 SHA-256 원장 (`docs/p3/asset_ledger_p3.sha256`), 기술 종결 백서(P3-05) | 고객사 납품을 위한 에어갭 패키지 구축 및 결정론적 재현성 보증 |

## 2. 완료 단계 종합 표 (Completed Phases Ledger)
| 단계 및 작업 | 핵심 실측 수치 | 기준치 | 최종 수정 커밋 | Git 태그 | 원장 파일 / SHA-256 | 판정 |
|---|---|---|---|---|---|---|
| Phase 1 (P1) | 3시점(Front/45°/Top) 홀드아웃 30점 투영 유클리드 오차 평균 0.3765 px, 최대 0.8920 px | $\le 1.0\text{ px}$ | `576101a` | `[?] (태그 미발행)` | `docs/p3/phase1_cameras_spatial_context.json` (`0c91f1f122eeffa317f838be03848b3bdadb71921042c29698553bdf57979420`) | **PASS** |
| Phase 1.5 (P1.5) | 합성 카메라 32프레임, 단위 테스트 2/2 통과 | 테스트 100% (2/2) | `59f1f0d` | `[?] (태그 미발행)` | `test/spatial_context.test.ts` (`01b2d09e3c3867ccd98f5147e45792e1ad2c67853efaf2a0eca44065379331b4`) | **PASS** |
| Phase 2 (P2) | 다중 강체 물리 벤치마크 (안착 15/15 (100.0%), 투척 14/15 (93.3%), avg FPS 29.88, p95 50.22 ms) | 안착 $\ge 80\%$, 투척 $\ge 85\%$ | `4c3978e` | `[?] (태그 미발행)` | `docs/phase2_results.json` (`f6baa35530c41bc4a229fe49f89e76bbb044bf2acccd7e9903a3862963323897`) | **PASS** |
| P3-00 | 공간 맥락 스키마 단위 테스트 통과 (행렬 왕복 오차 < 1e-6) | 오차 $< 1e-6$ | `59f1f0d` | `[?] (태그 미발행)` | `docs/p3/spatial_context_schema.json` (`d35d1ec26638ed8467652e398ea772084e4e4a978775b3764492b0c089969f18`) | **PASS** |
| P3-01 | 내장 raycast 100.0%, SplatEdit 외곽 변화율 0%, 결정론 캡처 일치, conditions.json 서명 `S2A-CLAUDE-20260906-P3-01-eb0643be` | raycast $\ge 90\%$, 외곽 변화율 0% | `dd53e09` | `[?] (태그 미발행)` | `tests/p3/conditions.json` (`fc72512a49b765e084af7a92176d60259ab130785cc43af73fcd93a948094c43`) | **PASS** |
| P3-02 Task 1 | Marble 텍스처 씬 생성 (`run01`), world_id `f055b5c9-3141-4729-8627-e904aa70828b`, 잔여 크레딧 36,670 | 성공 응답 | `2a12594` | `p3-02-task1-2` | `docs/p3/marble/run01_response.json` (`c7f10452f0e0028d29f1f643611caed48e393dd421280a7fc271473d8861decd`) | **PASS** |
| P3-02 Task 2 | Marble 좌표계 변환 도출 (Scale 2.121173, Translation Y +1.2561374 m, 바닥면 정렬 오차 0.0100 m), 관측 체적 카메라 배치 40개 중 유효 2개 (5.0%)* | 바닥면 정렬 오차 $< 0.05\text{ m}$ | `2a12594` | `p3-02-task1-2` | `docs/p3/raw/marble_transform_verify_run01.json` (`3cb4d0b350d16c70c7e32b1f3ba0de86f305fc919a8098c0863dad9a9d0878e8`) | **PASS** |
| P3-02 Task 4 | 500k 스플랫 3D 공간 분할: L1 916개, R1 1,459개 (동적 3,740개, 정적 496,260개, 부유물 8개), 차분 발광 L1 3.25%, R1 4.21% | 발광 $< 15\%$ | `cab30dd` | `p3-02-task4-r4` | `docs/p3/raw/t5_500k_partition_metrics.json` (`331fc0b4493ff3765430786d631a51008124a325e7f2250e13dcad5b7b444b06`) | **PASS** |
| P3-02 Task 5 | 부품 bbox 보정 레이캐스트 픽킹(정책 v2) 홀드아웃 단일 실행 평가 119/150 (79.3%), 정적 오탐 0/75 (0.0%) | 식별 $\ge 70.0\%$, 오탐 $\le 15.0\%$ | `4805105` | `[?] (태그 미발행)` | `docs/p3/raw/t5c_pick_eval.json` (`b587e5efd740fd5e063fa9497f98bc98a57a5b51be4e62d8f5dbda25d4e60a27`) | **PASS** |
| P3-02 Task 6 | 다중 강체 물리 시뮬레이션: 정적 콜라이더 평면화(0개 제거, 잔여 0개 + 평면 바닥 큐보이드 $y=-0.0250\text{ m}$), 낙하 L1 바닥차 1.96cm/회전 9.48°, R1 바닥차 0.93cm/회전 1.90°, 투척 L1 0.669m, R1 0.586m, 고정 dt 1/60 s, 물리 스텝 p50 5.98ms/p95 8.96ms, 결정론 0 diff | 낙하 바닥차 $[-2, +3]\text{ cm}$, 회전 $\le 15^\circ$, 투척 $> 0.5\text{ m}$, 물리 스텝 $\le 16.67\text{ ms}$ (렌더 FPS: [?] llvmpipe, 미측정) | `9e0ffd7` | `p3-02-task6-t6c` | `docs/p3/raw/t6c_scenarios.json` (`59ef07b35e094a869588ed566f201db7b5f06ee623a5dfab2940b53cf15b5b8d`) | **PASS (종결)** |
- \* 각주 (`docs/p3/marble/run01_viewing_volume.md` 인용): `viewing_volume_metrics.json`의 `is_inside`는 기준 정면 뷰($x=0.0, y=1.6, z=-1.5$) 대비 라플라시안 분산비 $\ge 60\%$ 및 2D SSIM $\ge 0.50$ 동시 충족 여부임. 탐색 격자 범위는 $X \in [-1.3, +1.3]\text{ m}$, $Y \in [1.6, 3.0]\text{ m}$, $Z \in [-1.5, +6.0]\text{ m}$ 총 40개 배치 중 중심축 2개 시점($x=0, z=-1.5$ 및 $x=0, z=0$)만 정량 통과하였으며, 나머지 시점은 3D 시차(Disparity) 또는 랙 간섭으로 SSIM이 미달됨. 후속 Task 5·6은 실측 유효 구역($X \in [-1.0, +1.0]\text{ m}$, $Y \in [1.2, 3.0]\text{ m}$, $Z \in [-1.5, +4.0]\text{ m}$) 내로 카메라를 제한 배치함.

## 3. 미완 및 보류 항목 원장 (Pending Items Ledger)
| 항목 | 현재 상태 | 지연 및 보류 사유 | 필요 결정 및 선행 조치 | 결정 주체 |
|---|---|---|---|---|
| P3-02 Task 3 다시점 생성 | 보류 [미확정] | 부품 측면/배면 쉘 차폐 한계를 해소하기 위해 2개 시점 추가 생성이 필요하나 3,200 Marble 크레딧 소모 수반 | 크레딧 사용 승인 및 API 키 투입 | Principal [미확정] |
| P3-03 자체 3D 재구성 | 보류 [미확정] | NeRF/Splatfacto 기반 원시 사진 로컬 학습을 위한 GPU 가속 환경 필요 | GPU sudo 권한 부여 (NVIDIA 드라이버 활성화) | Principal [미확정] |
| P3-04 정밀 콜라이더 메시 생성 | 보류 [미확정] | P3-03 자체 재구성 모델과 연계된 고해상도 지상 검증 콜라이더 제작 | P3-03 자체 재구성 착수 여부에 종속 | Principal [미확정] |
| 2·3열 팔레트 상자 (L2, R2, L3, R3) | 보류 [미확정] | 관측 체적(±1.3 m) 밖 스플랫 밀도 부족 | 범위 (A) 6부품 확장 vs (B) L1/R1 유지 결정 | Principal [미확정] |
| 동적 상자 질량 사양 | 보류 [미확정] | 현장 물류 팔레트 및 적재 화물의 실측 중량 사양서 미제공 | 실측 중량 사양서 제공 ('임의 상수 300 kg, 사양 미확정' 적용 중) | Principal [미확정] |
| Marble API 키 교체 | 보류 [미확정] | 계획서 및 감사 로그 상 부분 문자열 3회 노출 사고(INC-06) | API 키 재발급 및 환경변수 롤링 | Principal [미확정] |

## 4. 사고 원장 전문 (Incident Reports INC-01 ~ INC-08)
| 사고 번호 | 사고 명칭 | 발생 원인 및 내용 | 조치 결과 | 재발 방지 대책 |
|---|---|---|---|---|
| INC-01 | 자산 해시 생성 | [상세: 감사 기록 미보유] | 수기 작성 데이터 전면 폐기 및 단일 실행(Single-Run) 파이프라인 강제 구축 | raw 파일 생성 없이는 make_report 및 감사 보고서 생성 불가 규칙 수립 |
| INC-02 | 보고서 통계 생성 | [상세: 감사 기록 미보유] | 전수 조사 완료 전 보고서 수치 기재 원천 차단 | 원장 JSON 데이터 로드 후 수치 파싱 파이프라인 강제 |
| INC-03 | conditions.json 해시 생성(진짜 eb0643be…) | [상세: 감사 기록 미보유] (커밋 c6616a0, dd53e09) | 허위 해시 라인 즉시 무효화 및 hashlib.sha256() 자동 산출 체계로 전면 전환, 서명 `S2A-CLAUDE-20260906-P3-01-eb0643be` 반영 | docs/p3/asset_ledger_p3.sha256에 sha256sum -c 검증 절차 의무화 |
| INC-04 | API 키 계획서 기재 | 작업 계획서 아티팩트에 실제 API 키 평문 문자열 기재 | 계획서 즉시 수정 및 커밋 기록에서 제거, 환경변수 치환 | 비밀값은 환경변수명(`WLT_API_KEY`)만 표기하는 규칙 제정 |
| INC-05 | 파노라마 Blender 렌더를 "시각 점군"으로 표기 | 파노라마 Blender 렌더링 결과물을 시각 점군으로 잘못 표기하여 전달 | 자산 성격 정정 및 파노라마 렌더 이미지 메타데이터 분리 | 렌더 자산 분류 명명 규칙 준수 및 증적 분리 |
| INC-06 | 키 부분 문자열 3회 | 디버그 로그 및 프롬프트 인용 중 키(`WLT_API_KEY`)의 앞뒤 부분 문자열이 3회 노출 | 전 코드베이스 및 문서 내 키 문자열 마스킹 조치, Principal에게 키 롤링 공식 요청 | 부분 문자열이라도 비밀값(`WLT_API_KEY`) 노출 시 감사 차단 규칙 적용 |
| INC-07 | 원장 엔드포인트(save-eval-t5c) 가공 POST, 프록시 차단 | 하네스 디버깅 과정에서 모의 페이로드를 원장 엔드포인트(/api/p3/save-eval-t5c)로 POST 전송 시도 | 샌드박스 프록시가 비정상 요청을 차단하여 서버 수신 0건 종결, 정상 수신 1건만 보존 | 원장 엔드포인트 테스트 일체 금지, 헬스체크는 /api/p3/ping으로만 한정 |
| INC-08 | 종결 문서 허구 기재 | make_report의 p3-close 모듈 구현 시, 원장 파일과 git 저장소를 직접 파싱하지 않고 왜곡된 이력을 수기 작성 | P3_CLOSE_v0 전면 반려 처리. make_report.py 내 p3-close 모듈 전면 재작성하여 모든 이력 수치, 식별자, git 태그를 실제 파일 및 git 서브프로세스에서 동적으로 로드하도록 전환. 수기 리터럴 검사 게이트 도입 | 이력, 수치, 식별자는 스크립트가 파일 또는 git에서 직접 읽어 채운 값만 허용하며, 파일이 없거나 파싱 불가한 항목은 임의 추정 없이 `[?]`와 사유를 출력함 |

## 5. 감사관 사양 결정 및 결함/오류 기록 (Specifications & Errors Ledger)
| 번호 | 구분 | 관련 작업 | 사양 오류 및 결정 내용 | 조치 결과 및 판정 |
|---|---|---|---|---|
| SPEC-ERR-01 | 사양 오류 | Phase 2 | 임펄스 [상세: 감사 기록 미보유] (커밋 437ea57 mass-proportional impulse) | 질량 비례 임펄스 크기 보정 완료 |
| SPEC-ERR-02 | 사양 오류 | Phase 2 | 중력 보정식 [상세: 감사 기록 미보유] (커밋 437ea57) | 고정 dt 기반 표준 중력 수식 적용 |
| SPEC-ERR-03 | 사양 오류 | Phase 1/1.5 | 분해율 [상세: 감사 기록 미보유] (커밋 4c3978e explode 50%) | 허용 범위 재조정 완료 |
| SPEC-ERR-04 | 사양 오류 | P3-02 T2 | 바닥 p1 기준 [상세: 감사 기록 미보유] (커밋 cab30dd) | 메쉬 바닥면 직접 정렬 방식으로 정정 |
| SPEC-ERR-05 | 사양 오류 | Phase 1/P3-00 | 카메라 좌표 [상세: 감사 기록 미보유] (커밋 5d602a2) | 좌표계 변환 행렬 명시적 적용 |
| SPEC-ERR-06 | 사양 오류 | P3-02 T6 | 질량 p5~p95×500 표본 의존: 3D 가우시안 체적 기반 질량 산정 지시 | '임의 상수 300 kg, 사양 미확정'으로 표기 전환 |
| SPEC-ERR-07 | 사양 오류 | P3-02 T4 | 색 마스크 비배타 [상세: 감사 기록 미보유] (커밋 cab30dd) | hue 최근접 배타 할당 적용 |
| SPEC-ERR-08 | 사양 오류 | P3-02 T4 | hue 팔레트가 씬 자연색과 중첩: hue 팔레트가 씬 자연색과 중첩되어 배경 기둥/빔 오분할 유발 | 차분 마스크로 대체 |
| SPEC-ERR-09 | 사양 오류 | P3-02 T5-c | 종횡비 1280/720 지시: 감사관 지시서의 '카메라 종횡비 1280/720이어야 함' 지시 오류 | 캡처 카메라 innerWidth/innerHeight=1.5592와 동일하게 맞추는 것이 올바른 기준임을 확인, 정합 인정 |
| SPEC-ERR-10 | 사양 오류 | P3-02 T6-c | 휴지 초기 y: 휴지 시험 '중심 고정' 지시로 인해 BBox 중심 y를 초기값으로 두어 상자 밑면이 바닥 위에 부유하여 낙하 충격 발생 | T6-CLOSE에서 접지 높이 y = y_mesh + hy + 0.005로 정정 재실행 |
| SPEC-ERR-11 | 사양 오류 | P3-02 T6-c | 바인딩 중심 거리 지표: 바인딩 평가 지표로 2D 중심 거리 지시 (스플랫 편향 분포로 질량 중심과 BBox 중심 간 차이 내재) | 중심 거리가 아닌 2D BBox 포괄 비율(Enclosure Ratio >= 90%)로 지표 대체 |
| SPEC-ERR-12 | 사양 오류 | P3-02 T6-CLOSE | 휴지 3D 변위 기준: 휴지 시험 3D 변위 기준 적용 오류 (지정된 5 mm 공극 자체가 0.5 cm 변위를 발생시키므로 3D 기준 부적절) | 수평 XZ 변위 기준(<= 1.0 cm) 적용, XZ 기준 R1 0.839 cm로 통과 |
| SPEC-DEC-T5C | 사양 결정 | P3-02 T5-c | 부품 bbox 보정 레이캐스트 픽킹(정책 v2) 도입: 부품 BBox +3cm 진입 및 정적 히트 깊이 <= 0.35 m 시 부품 보정 | 정책 v2 적용으로 식별률 79.3% 달성 (PASS) |
| SPEC-DEC-T6C | 사양 결정 | P3-02 T6-c | 정적 콜라이더 평면화: 삼각망 경사면 0개 제거 및 평면 바닥 큐보이드(y = -0.0250 m) 도입 | 경사 미끄러짐 해소, 시나리오 A/B 전항목 충족 통과 |
| CONST-MASS | 사양 미확정 | P3-02 T6 | 동적 팔레트 상자 질량 사양 미확정 | '임의 상수 300 kg, 사양 미확정' 공식 명시 유지 |

- **콜라이더 핸들 출력 이상(5e-324) 원인 분석**:
  - `docs/p3/raw/t6close_rest.txt`의 `handle: 5e-324` 표기 이상은 Rapier WASM/JS 바인딩에서 64비트 정수 핸들 비트(`0x0000000000000001`, 인덱스 1인 평면 바닥 큐보이드)가 JS `Float64`로 역직렬화되면서 비정규화 부동소수점으로 출력된 단순 표기 결함이며, 내부 물리 연산은 핸들 인덱스 1로 정상 라우팅됨.

## 6. 잔여 결함 이월 목록 및 포함 비율 참고값 (Residual Defects & Reference Values)
### 6-1. 잔여 결함 이월 목록 (Residual Defects Ledger)
| 결함 번호 | 결함 항목 | 발생 원인 및 물리적 메커니즘 | 실측 영향도 | 조치 상태 |
|---|---|---|---|---|
| DEF-RES-01 | L1 휴지 수평 이동 XZ 2.03 cm | 정적 삼각망 제거 규칙(|x| >= 0.85 m) 경계에 걸친 미세 삼각면(x ≈ -1.02 m, y ≈ 0.0001~0.0042 m)에 내측 모서리 접촉 틸팅 | 기준치(<= 1.0 cm) 대비 초과 | 미달 기록, 잔여 결함 이월 |
| DEF-RES-02 | L1 낙하 22.36 cm 드리프트 원인 [?] | 4 mm 삼각망 턱 높이로는 9.48° 틸트 설명이 기하학적으로 부족하며, R1처럼 기둥 측면 접촉 가능성이 있으나 T6-c 원장 JSON에 접촉 핸들이 미포함됨 | 원장 기록 부재 | 원인 미확정 [?] 잔여 결함 이월 |
| DEF-RES-03 | 2·3열 팔레트 상자 차폐 한계 | 관측 체적(±1.3 m) 밖 스플랫 밀도 부족 및 가려짐으로 인해 2·3열 깊이 쉘 미분할 | 범위 (A) 6부품 확장 불가 | 범위 (B) 유지 상태로 이월, Principal 결정 대기 [미확정] |
| DEF-RES-04 | 부품 정면 쉘 한계 | 단일 시점 캡처로 인해 분할된 3DGS 부품이 측면/배면이 빈 얇은 판 형상으로 잔류 | 투척 시 측면 쉘 결함 노출 | Task 3 다시점 추가 생성 필요 [미확정] |
| DEF-RES-05 | 동적 상자 질량 사양 미확정 | 실측 팔레트 및 적재 중량 사양서 미제공 | 관성 모멘트 및 마찰력 산정의 실측 기준 부재 | '임의 상수 300 kg, 사양 미확정' 표기 유지 [미확정] |

### 6-2. Task 2 포함 비율 색 마스크 기반 참고값 (Reference Values)
| 시점 | 강체 식별자 | 2D 헬퍼 BBox | 단순 반화면 색 마스크 (기준 A) | 정적 배경 배제 색 마스크 (기준 B) | 캡처 원장 판정 (`t6close_enclosure.json`) | 비고 |
|---|---|---|---|---|---|---|
| t0 | L1 상자 (`box_l1`) | `[119, 281, 437, 483]` | 40.03% | **96.83%** | 미달 (82.92%) | 기준 A는 배경 블루 기둥 포함 |
| t0 | R1 상자 (`box_r1`) | `[882, 287, 1139, 476]` | 23.23% | **85.62%** | 미달 (68.18%) | 기준 A는 배경 오렌지 빔 포함 |
| landing | L1 상자 (`box_l1`) | `[129, 490, 440, 732]` | 30.54% | **99.23%** | **PASS (99.45%)** | 상자가 접지 위치에 위치 |
| landing | R1 상자 (`box_r1`) | `[874, 489, 1131, 717]` | 19.51% | **98.11%** | **PASS (97.02%)** | 상자가 접지 위치에 위치 |
| final | L1 상자 (`box_l1`) | `[199, 480, 469, 724]` | 23.95% | **96.16%** | 미달 (84.05%) | 원장은 드리프트 잔여로 분모 증가 |
| final | R1 상자 (`box_r1`) | `[858, 499, 1112, 730]` | 17.92% | **94.01%** | 미달 (88.33%) | 원장은 드리프트 잔여로 분모 증가 |
- **주의**: 본 절의 수치는 지시서에 따른 참고값이며, **원장 판정은 일체 변경하지 않고 보존**합니다.

## 7. 자산 및 실행 환경 원장 (Environment & Asset Ledger)
### 7-1. 실행 환경
- 하드웨어: NVIDIA RTX 6000 Ada Generation (sudo 권한 미보유로 드라이버 미활성 상태)
- 렌더러 드라이버: `llvmpipe (LLVM 18.1.3, 256 bits)` CPU 소프트웨어 에뮬레이션
- 가상 디스플레이: Xvfb `:11.0`, Window ID `0x2800016`
- 소프트웨어: Node.js `v20.20.2`, Python `v3.12.3`, Three.js `v0.180.0`, Rapier3D `v0.12.0`
- Git 브랜치: `feature/phase3-spatial`

### 7-2. 자산 해시 원장 대조 (`docs/p3/asset_ledger_p3.sha256`, `docs/asset_ledger.sha256`, `docs/p3/raw/marble_assets_sha256.txt`)
#### 7-2-1. Marble 원시 생성 자산 (`docs/p3/raw/marble_assets_sha256.txt`, 4행)
- `assets/p3/marble/run01_full_res.spz`: `59981a9f67c3bc399b0be73fe7949fd4b9a495ca38b2363b6ce0ce0a8b097fe7`
- `assets/p3/marble/run01_500k.spz`: `bea791f70242dc9aaa41f4b1975e7891e887c0c02a4c0dec1878fbb258096877`
- `assets/p3/marble/run01_collider_mesh.glb`: `89dcb0b1eded2ff02c8b27235a2c1f9cbccd286866639cacb697f88b9e7a83bd`
- `assets/p3/marble/run01_splats.ply`: `6a0f7a7a8c811342053601584033269f2d8c26aa3e2dad07db77121ac64a0841`
- `assets/p3/marble/run01_pano.png`: 원장 미등재 자산 [?]

#### 7-2-2. Phase 1/Phase 2 원시 자산 (`docs/asset_ledger.sha256`, 7행)
- `3d-model/generated_3dgs_dragon.ply`: `e7dc7a3e8079388317af1cf5c6787616b23039dcd37a5d840b10448a8542ebab`
- `3d-model/parts/dragon_part_body.ply`: `879d24a35ed3001f5c45d240e3fb3b92075fce56ee161c25bb0e9383cb6c3e56`
- `3d-model/parts/dragon_part_head.ply`: `fb16505363c1c6bd8c439776cb01959dcc45485dfc0dd2a3a46e1f4f51d56bc3`
- `3d-model/parts/dragon_part_left_wing.ply`: `9191276a6b888f2d638776a7459e60a7e5f69a76f330760c1371472a829df8ca`
- `3d-model/parts/dragon_part_right_wing.ply`: `c885d63a99b9f7cf50c6c4ff222274a8ec1c618332e3f0c51a95d6f9debd5b33`
- `3d-model/parts/dragon_part_tail.ply`: `95a76365af48540039e94bbfaa1a844b3251a9791bb6824ab106931c9efa7612`
- `3d-model/parts/manifest.json`: `5b377686152fbc8d0292ea836fd9d0d258f6fb46ca4a226d68ea395758cd1ec3`

#### 7-2-3. Phase 3 주요 검증 원장 및 캡처 (`docs/p3/asset_ledger_p3.sha256`, 총 121행)
- `assets/p3/marble/run01_parts/spz500k/manifest.json`: `a7811de76810a36ecc7a63dd0d347f3a24147c7f19e27b4916eb2598276ea9c6`
- `docs/p3/raw/t6c_scenarios.json`: `59ef07b35e094a869588ed566f201db7b5f06ee623a5dfab2940b53cf15b5b8d`
- `docs/p3/raw/t6c_collider_fix.json`: `fdec0cc5eccfc551c72c03db8efcee48ced9d3e9954087d2da2f2f77c5f59a52`
- `docs/p3/raw/t6close_rest.json`: `45f767f20093a75f6f7b79da2b67170538e7a1c293984308097df2a09bd71e2b`
- `docs/p3/raw/t6close_enclosure.json`: `c6b5f739c87f3ca5e86ea81a40fd08003feb9eb88be7370c4928060b779cb2e8`
- `docs/p3/captures/marble_run01_t6c_scenA_t0.png`: `f3f0e95484ebf0b3a6d2f1ff958e0fcf61a216da6e6c0d14029c5430b0c1c0b9`
- `docs/p3/captures/marble_run01_t6c_scenA_landing.png`: `2b5513994200106fc1d9e06781b0c2ddb5b70b7b2ee75f77b29a5501ba87359d`
- `docs/p3/captures/marble_run01_t6c_scenA_final.png`: `8a5e137782159db29b576f37e5113ffec13adaad338d4ae7f6741fe706a3bcb0`

## 8. 재현 절차 (Reproduction Protocol)
### 8-1. 스크립트 실행 순서
1. 백엔드 서버 기동: `.venv/bin/python ai_spatial_server.py` (포트 8088 백그라운드 데몬)
2. 프론트엔드 서버 기동: `npm run dev` (포트 8080 백그라운드 데몬)
3. 500k 공간 분할 실행: `scripts/run_p3_partition_capture.py` -> `docs/p3/raw/t5_500k_partition_metrics.json` 생성
4. 픽킹 v2 홀드아웃 평가: `scripts/run_p3_t5c_eval.py` -> `docs/p3/raw/t5c_pick_eval.json` 생성 (Single-Run)
5. 물리 시나리오 실행: `scripts/run_p3_t6c_physics.py` -> `t6c_scenarios.json` 및 6장 캡처 생성
6. 휴지 시험 및 포함 비율 산출: `scripts/calculate_t6close_enclosure.py` -> `t6close_rest.json`, `t6close_enclosure.json` 생성
7. 종결 보고서 생성: `.venv/bin/python scripts/make_report.py --module p3-close --out docs/p3/P3_CLOSE_v1draft.md`
8. Word/PDF 문서 변환: `.venv/bin/python scripts/convert_report_to_docs.py docs/p3/P3_CLOSE_v1draft.md`

### 8-2. 단일 실행(Single-Run) 및 회차 관리 규칙
- 평가 데이터셋(홀드아웃 150점 + 정적 75점) 평가는 사후 코드 튜닝 없이 1회 실행 완주를 원칙으로 함.
- 브라우저 X11 키 입력 포커스 이탈 등 환경적 기동 실패는 회차별 Task ID와 실패 원인을 원장에 투명하게 공개함.

## 9. 백서 v1.0 [?] 수치 채움 목록 (Whitepaper Metric Mapping)
| 백서 섹션 | 대상 지표 항목 | T6 종결 실측 수치 | 원장 포인터 | 판정 및 비고 |
|---|---|---|---|---|
| 2.1 Viewing Volume | 가시 볼륨 체적 | 카메라 배치 40개 중 유효 2개 (5.0%), 유효 격자 탐색 $X \in [-1.3, +1.3]\text{ m}$, $Y \in [1.6, 3.0]\text{ m}$, $Z \in [-1.5, +6.0]\text{ m}$ | `docs/p3/raw/viewing_volume_metrics.json` | 실측 확정 |
| 3.2 Splat Partition | 500k 분할 스플랫 수량 | L1: 916개, R1: 1,459개 (동적 합: 3,740개, 정적: 496,260개, 부유물: 8개) | `docs/p3/raw/t5_500k_partition_metrics.json` | 실측 확정 |
| 3.3 Diff Glow | 부품 차분 발광율 | L1: 3.25%, R1: 4.21% | `docs/p3/raw/t5_diff_glow.json` | 기준 $< 15\%$ 충족 |
| 4.1 Picking Evaluation | 부품 bbox 보정 레이캐스트 픽킹 정확도 (정책 v2) | 79.3% (119/150 hits), 정적 오탐 0.0% (0/75) | `docs/p3/raw/t5c_pick_eval.json` | 기준 $\ge 70.0\%$, 오탐 $\le 15.0\%$ 충족 |
| 5.1 Physics Drop | 낙하 착지 시각 | 0.450 s (이론값 $\approx 0.4515\text{ s}$ 근접) | `docs/p3/raw/t6c_scenarios.json` | 기준 충족 |
| 5.1 Physics Drop | 낙하 안착 바닥차 | L1: 1.96 cm, R1: 0.93 cm | `docs/p3/raw/t6c_scenarios.json` | 기준 $[-2, +3]\text{ cm}$ 충족 |
| 5.1 Physics Drop | 낙하 안착 회전각 | L1: 9.48°, R1: 1.90° | `docs/p3/raw/t6c_scenarios.json` | 기준 $\le 15^\circ$ 충족 |
| 5.2 Physics Throw | 2.5 m/s 투척 활주 거리 | L1: 0.669 m, R1: 0.586 m | `docs/p3/raw/t6c_scenarios.json` | 기준 $> 0.5\text{ m}$ 충족 |
| 5.3 Physics Latency | 물리 스텝 지연시간 | p50: 5.98 ms, p95: 8.96 ms (CPU llvmpipe 환경, `docs/p3/raw/t6c_scenarios.json`) | 고정 dt 1/60 s 물리 스텝 기준($\le 16.67\text{ ms}$) 충족 (렌더 FPS: [?] llvmpipe, 미측정) |
| 5.4 Determinism | 물리 시뮬레이션 결정론 | 0 diff (동일 WASM 프로세스 2회 비트 일치) | `docs/p3/raw/t6_determinism.json` | 결정론 검증 통과 |
| 5.5 Mass Property | 동적 팔레트 상자 질량 | 300.0 kg (임의 상수, 사양 미확정 [미확정]) | `docs/p3/raw/t6close_rest.json` | 사양 미확정 표기 유지 |
