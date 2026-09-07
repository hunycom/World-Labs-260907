# 다시점 데이터셋 라이선스 조사 및 판정 보고서 (Dataset Licenses Survey)

- 작성 일시: 2026-09-06
- 지시서: `EXE-260906-P3-00-C` Task 2
- 목적: 백서 인용 및 상용 에어갭 디지털 트윈 납품이 가능한 다시점 사진 데이터셋 선별 및 라이선스 원문 검증

---

## 1. 데이터셋 후보군 라이선스 원문 조사 및 판정 요약

| 데이터셋 | 관리 주체 | 라이선스 형태 | 상용 이용 가능 여부 | 판정 | 백서 인용 |
|---|---|---|---|---|---|
| **BlendedMVS / BlendedMVG** (실사 기반 블렌딩) | Yao et al. (CVPR 2020 / HKUST) | **CC BY 4.0** | **허용 (`even commercially`)** | **최종 채택 (미러 대조 검증)** | **인용 가능 (블렌딩 명시 필수)** |
| **Smithsonian 3D Open Access** | Smithsonian Institution | **CC0 1.0 Universal** | **허용 (`including commercial use`)** | 적합 (참조) | 인용 가능 |
| **Poly Haven** | Poly Haven | **CC0 1.0 Universal** | **허용 (`including commercial work`)** | **Task 1 채택** | **인용 가능** |
| **World Labs Spark Samples** | World Labs Technologies, Inc. | **MIT License** | **허용 (`without restriction / sell`)** | **Task 3 채택** | **인용 가능** |
| Tanks and Temples | Knapitsch et al. (SIGGRAPH 2017) | CC BY-NC-SA 4.0 | 불가 (NonCommercial) | 배제 (내부 검증용) | 인용 불가 |
| DTU Robot Image Dataset | Aanæs et al. (DTU) | Research/Academic Only | 불가 (NonCommercial) | 배제 (내부 검증용) | 인용 불가 |
| ScanNet | Dai et al. (CVPR 2017) | ScanNet Terms of Use | 불가 (Non-commercial research only) | 배제 (내부 검증용) | 인용 불가 |
| CO3D (Common Objects in 3D) | Reizenstein et al. (Meta AI) | CC BY-NC 4.0 | 불가 (NonCommercial) | 배제 (내부 검증용) | 인용 불가 |
| Stanford Light Field Archive | Stanford CG Lab | Research/Educational Only | 불가 (Non-commercial research only) | 배제 (내부 검증용) | 인용 불가 |
| ETH3D Benchmark | Schöps et al. (CVPR 2017) | CC BY-NC-SA 3.0 | 불가 (NonCommercial) | 배제 (내부 검증용) | 인용 불가 |

---

## 2. 채택 데이터셋 라이선스 원문 인용

### (1) BlendedMVS / BlendedMVG (Task 2 실사 기반 블렌딩 데이터셋 채택)
- 원본 배포처: `https://github.com/YoYo000/BlendedMVS`
- 다운로드 미러: `https://huggingface.co/datasets/vctvct123/BlendedMVS_processed`
- 미러 사용 및 원본 대조 결과:
  - 내려받은 경로는 HuggingFace 제3자 미러(`vctvct123/BlendedMVS_processed`)입니다.
  - 원본 배포처(`YoYo000/BlendedMVS`)의 공식 씬 목록 파일(`project_lists/all_list.txt`)에 대상 두 씬 ID(`567a0fb0a825d2fb79ac9a20`, `5643df56138263b51db1b5f3`)가 정식 포함되어 있음을 확인하였습니다.
  - 단, 개별 이미지 파일 및 카메라 포즈(`.npz`)에 대한 원본과의 1:1 바이트/파라미터 대조는 공식 원본 다운로드 경로(OneDrive/Baidu Netdisk 아카이브) 미수행으로 인해 **미확인(Unverified)** 상태이며, 제3자 미러가 제공한 데이터를 기반으로 사용합니다.
- 데이터셋 성격 규정:
  - BlendedMVS는 실사(real-world imagery)와 렌더 텍스처를 기하 기반으로 블렌딩(blended)하여 제작된 대규모 MVS 벤치마크 데이터셋입니다.
  - 순수 야외/실내 사진(pure photographic images)이 아니므로, 백서 및 기술 문서에는 **"실사 기반 블렌딩 데이터셋 (Blended real-synthetic dataset)"**으로 정확히 표기합니다.
- 라이선스: Creative Commons Attribution 4.0 International (CC BY 4.0)
- 원문 인용:
> "BlendedMVS and BlendedMVG are licensed under a Creative Commons Attribution 4.0 International License!"
> 
> CC BY 4.0 Deed:
> "You are free to:
> - Share — copy and redistribute the material in any medium or format for any purpose, even commercially.
> - Adapt — remix, transform, and build upon the material for any purpose, even commercially.
> Under the following terms:
> - Attribution — You must give appropriate credit, provide a link to the license, and indicate if changes were made."

### (2) Poly Haven (Task 1 합성 3D 소품 모델 채택)
- 출처: `https://polyhaven.com/license`
- 라이선스: Creative Commons CC0 1.0 Universal (Public Domain)
- 원문 인용:
> "All assets (HDRIs, textures and 3D models) on this site are the original work of Poly Haven staff, or artists who willingly and directly donate/sell their work to Poly Haven.
> Our assets are all licensed as CC0, which is effectively Public Domain even in jurisdictions that do not support the Public Domain.
> - You can use our assets for any purpose, including commercial work.
> - You do not need to give credit or attribution when using them (although it is appreciated).
> - You can redistribute them, share them around, include them when sharing your own work, or even in a product you sell."

### (3) World Labs Spark Samples (Task 3 런타임 검증용 3DGS 기준 자산)
- 출처: World Labs Technologies, Inc. (`sparkjs.dev`, `https://github.com/sparkjsdev/spark`)
- 라이선스: MIT License
- 원문 인용:
> "Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the 'Software'), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software..."

---

## 3. 비상업(Non-Commercial) 데이터셋 라이선스 원문 인용 (배제 근거)

### (1) Tanks and Temples
- 출처 URL: `https://www.tanksandtemples.org/license/`
- 라이선스: CC BY-NC-SA 4.0
- 비상업 조항 원문:
> "NonCommercial — You may not use the material for commercial purposes."
- 판정: 상업 데모 및 백서에 인용할 경우 라이선스 위반 소지가 있으므로 내부 성능 비교 검증용으로만 한정, 백서에는 인용 불가로 분류.

### (2) DTU Robot Image Dataset
- 출처 URL: `https://roboimagedata.compute.dtu.dk/` (약관 페이지: `http://roboimagedata.compute.dtu.dk/?page_id=36`)
- 이용 약관 원문:
> "The dataset is available for academic and non-commercial research purposes only. Any commercial usage is strictly prohibited without explicit written permission."
- 판정: 비상업 연구 한정으로 상업용 백서 인용 불가.

### (3) ScanNet
- 출처 URL: `http://www.scan-net.org/` (약관 원문: `http://www.scan-net.org/ScanNet_TOS.pdf`)
- Terms of Use 원문:
> "The data is available for non-commercial research purposes only. You agree not to reproduce, duplicate, copy, sell, trade, resell or exploit for any commercial purposes, any portion of the images and and 3D models."
- 판정: 상업적 백서 인용 불가.

### (4) CO3D (Common Objects in 3D)
- 출처 URL: `https://ai.meta.com/datasets/co3d-downloads/` (라이선스 전문: `https://github.com/facebookresearch/co3d/blob/main/LICENSE`)
- 라이선스: CC BY-NC 4.0
- 비상업 조항 원문:
> "Attribution-NonCommercial 4.0 International (CC BY-NC 4.0). You may not use the material for commercial purposes."
- 판정: 상업적 백서 인용 불가.

---

## 4. 실사 기반 블렌딩 선별 자산 상세 명세

### [물체] Moai Monolith Statue (설명용 명칭, Scene ID: `567a0fb0a825d2fb79ac9a20`)
- 자산 경로: `assets/p3/real_object/`
- 성격: 실사 기반 블렌딩 데이터셋 (Blended real-synthetic dataset)
- 장수: 32장 (`00000000.jpg` ~ `00000031.jpg`)
- 카메라 포즈: 32건 (`cams/00000000.npz` ~ `cams/00000031.npz`)
- 해상도: 746 × 560
- 대상 설명: 이스터 섬 모아이 석상 독립 오브젝트 (360도 전방위 근접 촬영, 배경 하늘/잔디)
- 공식 배포처: `https://github.com/YoYo000/BlendedMVS`
- 다운로드 미러: `https://huggingface.co/datasets/vctvct123/BlendedMVS_processed/resolve/main/567a0fb0a825d2fb79ac9a20/`

### [장면] Pagoda Tower Landscape (설명용 명칭, Scene ID: `5643df56138263b51db1b5f3`)
- 자산 경로: `assets/p3/real_scene/`
- 성격: 실사 기반 블렌딩 데이터셋 (Blended real-synthetic dataset)
- 장수: 79장 (`00000000.jpg` ~ `00000078.jpg`)
- 카메라 포즈: 79건 (`cams/00000000.npz` ~ `cams/00000078.npz`)
- 해상도: 746 × 560
- 대상 설명: 다층 목탑 건축물 및 주변 숲/연못/건물 전경 궤도 촬영
- 공식 배포처: `https://github.com/YoYo000/BlendedMVS`
- 다운로드 미러: `https://huggingface.co/datasets/vctvct123/BlendedMVS_processed/resolve/main/5643df56138263b51db1b5f3/`
