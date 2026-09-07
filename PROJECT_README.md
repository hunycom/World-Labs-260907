# Spark Spatial Intelligence OS
> **차세대 AI 공간 지능 & 3D 가우시안 스플래팅(3DGS) 분해·인터랙션 플랫폼**

---

## 1. 프로젝트 개요 (Overview)

**Spark Spatial Intelligence OS**는 World Labs의 오픈소스 3DGS 렌더러인 [Spark.js](https://github.com/sparkjsdev/spark)를 기반으로 확장 구축된 **AI 공간 지능 및 3D 가우시안 스플랫 공간 분해·조작 플랫폼**입니다.

단일 또는 다각도 이미지/3D 모델로부터 추론된 3D Gaussian Splatting 씬을 실시간 5개 기하 부품(머리, 좌우 날개, 꼬리, 코어 몸체)으로 자동 분할하고, 3D 공간 분해도(Exploded View), 고정밀 레이캐스팅 개체 선택, 100Hz 신경계 오실로스코프 파형 동기화, 산업용 디지털 트윈 기구학 시뮬레이션을 브라우저 단일 탭에서 60 FPS로 실시간 구동합니다.

---

## 2. 저장소 구조 및 업스트림(Upstream) 관계

본 저장소는 World Labs의 공식 Spark.js 저장소를 포크(Fork)하여 상위 응용 계층(Application Layer) 및 AI 공간 분석 백엔드를 구축한 프로젝트입니다.

```
spark/
├── src/                        # [Upstream] Spark.js 핵심 WebGL/WebGPU 렌더링 엔진 (World Labs, MIT)
│   ├── SplatMesh.ts            # 3DGS 메쉬 바인딩 및 GPU 래퍼
│   ├── SparkRenderer.ts        # THREE.js 통합 렌더러
│   └── ...
├── dist/                       # 프로덕션 빌드 번들 (spark.module.js 등)
├── index.html                  # [Application] Spark Spatial OS 웹 프론트엔드 & 런타임 GUI
├── spark_ai_spatial_engine.py  # [Local Engine] 3DGS 5부품 기하 분할 & 공간 지능 엔진
├── ai_spatial_server.py        # [Local Backend] FastAPI 기반 공간 지능 REST API & 감사 텔레메트리 서버
├── scripts/                    # 브라우저 자동화 감사 오케스트레이터 및 창 캡처 도구
├── docs/                       # 엔지니어링 백서, 감사 결과 원장, 파라미터 튜닝 이력
└── 3d-model/                   # 3D 모델 및 분할된 5개 부품 PLY 가우시안 스플랫 자산
```

---

## 3. 핵심 기술 기능 (Key Capabilities)

1. **4단계 AI 공간 분할 파이프라인 (AI Spatial Segmentation Pipeline)**:
   - 전처리 정점 클러스터링 $\rightarrow$ 3D 의미적 경계 상자 추정 $\rightarrow$ k-d 트리 공간 마스크 분할 $\rightarrow$ 잔여 스플랫 보존 및 5개 독립 3DGS PLY 실시간 스트리밍.
2. **동적 3D 공간 분해도 엔진 (Dynamic Exploded View Kinematics)**:
   - 부품별 비등방성 기하 탈출 벡터($\mathbf{d}_{\text{explode}}$)를 기반으로 $0\%\sim 100\%$ 무단 슬라이더 및 자동 왕복 분해 루프 구동.
3. **고신뢰도 개체 선택 엔진 (Robust 3DGS Object Selection)**:
   - WebGL 오프스크린 GPU 컬러 ID 피킹(`readRenderTargetPixels`) 및 무(無)파라미터 기하 폴백 엔진 탑재.
   - **[개체 선택 성능 및 카메라 권장 고지]**: 부품이 시선 방향(Z축)으로 일렬 중첩되는 **정면 뷰 개체 선택 정확도는 72.0%(조립·분해 공통)**로 한계가 존재합니다. 따라서 체적 분리가 시각적으로 명확한 **기본 카메라 45° 등각 뷰(`camera.position.set(1.8, 1.4, 2.4)`, 정확도 76%~92%) 사용을 기본으로 권장**하며, 애플리케이션 초기 카메라 및 리셋 프리셋이 45°로 고정되어 있습니다.
4. **산업용 디지털 트윈 & 뉴로 런타임**:
   - EV 모터 로터 고속 회전, 6자유도(6-DoF) 다관절 로봇 암 정기구학(FK) 실시간 구동, 100Hz 뉴로-오실로스코프 파형 시각화.

---

## 4. 라이선스 및 지적재산권 고지 (License & IP Notice)

- **Spark.js Engine**: Copyright © 2025 WORLD LABS TECHNOLOGIES, INC. ([MIT License](LICENSE))
- **Spark Spatial Intelligence OS Application & AI Engine**: Copyright © 2026 Project Contributors. Released under the **MIT License**.
- **3D 자산 출처 및 사용 조건**: 상세 내용은 [`docs/ASSETS_AND_LICENSES.md`](docs/ASSETS_AND_LICENSES.md) 원장을 참조하십시오.
