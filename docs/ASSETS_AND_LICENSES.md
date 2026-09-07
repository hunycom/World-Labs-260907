# 3D 자산 출처 및 라이선스 규격서 (Asset Provenance & Licensing Specification)

## 1. 3D 모델 및 가우시안 스플랫 자산 출처 원장

본 저장소에서 사용되는 모든 3D 모델 및 3D Gaussian Splatting(3DGS) 자산의 출처 및 라이선스 현황은 아래와 같습니다:

| 자산 파일명 | 포맷 및 사양 | 정점/스플랫 수 | 출처 원천 (Origin & Source) | 라이선스 및 사용 조건 (License & Usage Terms) | 관리 상태 |
|---|---|---|---|---|---|
| `3d-model/Dragon.fbx` | FBX (Binary) | 22,126 Vertices, 37,986 Faces | Git 커밋 `9fcc6f3f` 추가 자산 (외부 원본 URL 미확인) | **출처 미확인 (데모 한정 사용 / Demo Only)** | **강등 조치 완료** |
| `3d-model/Dragon_clean.ply` | PLY (ASCII 1.0) | 22,126 Vertices, 37,986 Faces | `Dragon.fbx` 기반 삼각망 추출본 | **출처 미확인 (데모 한정 사용 / Demo Only)** | **강등 조치 완료** |
| `3d-model/Dragon_dense_splats.ply` | PLY (Binary) | 288,028 Splats | `Dragon_clean.ply` 표면 고밀도화 로컬 산출물 | 데모 한정 사용 (상용 배포 불가) | 로컬 파생 산출물 |
| `3d-model/generated_3dgs_dragon.ply` | PLY (Binary 3DGS) | 40,000 Splats | `spark_ai_spatial_engine.py` 로컬 다각도 합성 산출물 | 프로젝트 로컬 생성물 (데모 한정 사용) | 로컬 산출물 (원장 관리) |
| `3d-model/parts/dragon_part_head.ply` | PLY (Binary 3DGS) | 7,588 Splats | `spark_ai_spatial_engine.py` 3D 기하 분할 산출물 | 프로젝트 로컬 생성물 (데모 한정 사용) | 로컬 산출물 (원장 관리) |
| `3d-model/parts/dragon_part_left_wing.ply` | PLY (Binary 3DGS) | 6,107 Splats | `spark_ai_spatial_engine.py` 3D 기하 분할 산출물 | 프로젝트 로컬 생성물 (데모 한정 사용) | 로컬 산출물 (원장 관리) |
| `3d-model/parts/dragon_part_right_wing.ply` | PLY (Binary 3DGS) | 6,088 Splats | `spark_ai_spatial_engine.py` 3D 기하 분할 산출물 | 프로젝트 로컬 생성물 (데모 한정 사용) | 로컬 산출물 (원장 관리) |
| `3d-model/parts/dragon_part_tail.ply` | PLY (Binary 3DGS) | 2,104 Splats | `spark_ai_spatial_engine.py` 3D 기하 분할 산출물 | 프로젝트 로컬 생성물 (데모 한정 사용) | 로컬 산출물 (원장 관리) |
| `3d-model/parts/dragon_part_body.ply` | PLY (Binary 3DGS) | 18,113 Splats | `spark_ai_spatial_engine.py` 3D 기하 분할 산출물 | 프로젝트 로컬 생성물 (데모 한정 사용) | 로컬 산출물 (원장 관리) |
| `butterfly.spz` | SPZ (Compressed 3DGS) | ~60,000 Splats | Spark.js 공식 CDN (`https://sparkjs.dev/assets/splats/butterfly.spz`) | Spark.js 오픈소스 저장소 (MIT License) 데모 에셋, 상용 별도 라이선스 미고지 (데모 한정) | CDN 원격 에셋 |
| `woobles.spz` | SPZ (Compressed 3DGS) | ~80,000 Splats | Spark.js 공식 CDN (`https://sparkjs.dev/assets/splats/woobles.spz`) | Spark.js 오픈소스 저장소 (MIT License) 데모 에셋, 상용 별도 라이선스 미고지 (데모 한정) | CDN 원격 에셋 |
| `cat.spz` | SPZ (Compressed 3DGS) | ~70,000 Splats | Spark.js 공식 CDN (`https://sparkjs.dev/assets/splats/cat.spz`) | Spark.js 오픈소스 저장소 (MIT License) 데모 에셋, 상용 별도 라이선스 미고지 (데모 한정) | CDN 원격 에셋 |
| `robot-head.spz` | SPZ (Compressed 3DGS) | ~120,000 Splats | Spark.js 공식 CDN (`https://sparkjs.dev/assets/splats/robot-head.spz`) | Spark.js 오픈소스 저장소 (MIT License) 데모 에셋, 상용 별도 라이선스 미고지 (데모 한정) | CDN 원격 에셋 |
| `dessert.spz` | SPZ (Compressed 3DGS) | ~95,000 Splats | Spark.js 공식 CDN (`https://sparkjs.dev/assets/splats/dessert.spz`) | Spark.js 오픈소스 저장소 (MIT License) 데모 에셋, 상용 별도 라이선스 미고지 (데모 한정) | CDN 원격 에셋 |
| `food/burger-from-amboy.spz` | SPZ (Compressed 3DGS) | ~110,000 Splats | Spark.js 공식 CDN (`https://sparkjs.dev/assets/splats/food/burger-from-amboy.spz`) | Spark.js 오픈소스 저장소 (MIT License) 데모 에셋, 상용 별도 라이선스 미고지 (데모 한정) | CDN 원격 에셋 |

> **감사관 지적 사항 반영 경고 (Caveat)**:
> `Dragon.fbx` 및 `Dragon_clean.ply`는 원본 다운로드 출처 URL 및 정확한 라이선스 계약 조항이 불명확하므로, 고객 백서 및 상용 배포 문서에서의 인용을 금지하며 **기술 검증 데모 한정 사용(Demo Only)**으로 엄격히 강등 관리합니다.

## 2. 엔진 소스코드 라이선스

- **Spark.js Engine (`@sparkjsdev/spark`)**:
  - Source: [github.com/sparkjsdev/spark](https://github.com/sparkjsdev/spark)
  - License: **MIT License** (`LICENSE`)
- **3DGS 기하 분할 및 백엔드 엔진 (`spark_ai_spatial_engine.py`, `ai_spatial_server.py`)**:
  - Source: Project Local
  - License: Project Internal
