# Phase 3 P3-02 Task 4: 3DGS 장면 자산 부품 분할 알고리즘 명세서 (Partition Method Spec)

- **문서 번호**: `DOC-260906-P3-02-PART`
- **적용 대상**: World Labs Marble 생성 3DGS 점군 (`run01_500k.spz` / `run01_splats.ply`) 및 충돌 메시 (`run01_collider_mesh.glb`)
- **수행 원칙**: 임의 좌표 슬라이싱(하드코딩 Bounding Box) 완전 폐기, 수학적/기하학적 군집화 및 연결 성분 분석 적용

---

## 1. 분할 접근 방식 및 알고리즘 선정

World Labs Marble의 출력물은 단일 통합 3DGS 점군(Unified Splat Cloud)으로 생성되며 개별 오브젝트 세그멘테이션 마스크를 제공하지 않습니다. 본 파이프라인에서는 런타임 물리 상호작용 및 파트 픽킹을 위해 **공간-색상 결합 k-평균 군집화 (Spatial-Color Feature k-Means Clustering)**와 **충돌 메시 연결 성분(Connected Components)**을 결합한 하이브리드 분할 알고리즘을 채택합니다.

### 선정 알고리즘: 고정 시드 k-평균 점군 분할 (Deterministic Feature k-Means)
- **부품 수**: $k = 5$ (Floor/Ground, Racks Left, Racks Right, Structural Ceiling, Stored Pallets/Aisle Goods)
- **시드 (Random Seed)**: 42 (결정론적 재현성 보장)
- **최대 반복수**: 100회 (수렴 허용 오차 $\epsilon = 10^{-4}$)

---

## 2. 수학적 정식화 (Mathematical Formulation)

각 스플랫 $i$ ($i \in \{1, \dots, N\}$)는 위치 좌표 $\mathbf{p}_i = (x_i, y_i, z_i) \in \mathbb{R}^3$와 sRGB 색상 $\mathbf{c}_i = (r_i, g_i, b_i) \in [0, 1]^3$을 가집니다.

### (1) 특징 벡터 정규화
위치와 색상의 스케일 차이를 보정하기 위해 정규화된 6차원 특징 벡터 $\mathbf{f}_i$를 구성합니다:
$$\mathbf{f}_i = \left[ \frac{x_i - \mu_x}{\sigma_x}, \frac{y_i - \mu_y}{\sigma_y}, \frac{z_i - \mu_z}{\sigma_z}, \alpha \cdot r_i, \alpha \cdot g_i, \alpha \cdot b_i \right]^T \in \mathbb{R}^6$$
- $\boldsymbol{\mu}, \boldsymbol{\sigma}$: 전체 점군의 위치 평균 및 표준편차
- $\alpha$: 색상 가중치 계수 ($\alpha = 0.5$, 공간 기하학 우선 반영)

### (2) 목적 함수 (Lloyd's Algorithm)
군집 중심점 $\mathbf{m}_1, \dots, \mathbf{m}_k$에 대해 군집 내 제곱합(WCSS, Within-Cluster Sum of Squares)을 최소화합니다:
$$\arg\min_{\mathcal{S}} \sum_{j=1}^{k} \sum_{\mathbf{f}_i \in S_j} \|\mathbf{f}_i - \mathbf{m}_j\|^2$$
- $S_j$: $j$번째 부품에 할당된 스플랫 인덱스 집합

---

## 3. 원본 보존 불변식 (Invariance & Memory Architecture)

1. **단일 버퍼 공유 (Shared PackedSplats)**:
   - 원본 PLY/SPZ 점군을 부품별 개별 파일로 쪼개어 중복 저장하지 않습니다.
   - 단일 메모리 버퍼 `PackedSplats`를 유지하고, 각 부품은 인덱스 마스크 `part_indices: Uint32Array`로 참조합니다.
2. **스플랫 총합 보존식**:
   $$\sum_{j=1}^{5} |S_j| = N_{\text{total}}$$
   - 어떠한 스플랫도 누락되거나 중복 할당되지 않음을 검증합니다 ($S_a \cap S_b = \emptyset, \forall a \neq b$).

---

## 4. 부품 ID 및 물리 속성 매핑 (5 Parts)

| Part ID | 명칭 (Label) | 공간 기하 특성 | Rapier 강체 유형 | 질량 계수 |
|---|---|---|---|---|
| `part_0` | Concrete Floor (바닥) | $y \approx 0\text{ m}$, 하단 평면 | 고정체 (`Fixed`) | $\infty$ |
| `part_1` | Pallet Racks Left (좌측 랙) | $x < 0$, 수직 다층 프레임 | 고정체 (`Fixed`) | $\infty$ |
| `part_2` | Pallet Racks Right (우측 랙) | $x > 0$, 수직 다층 프레임 | 고정체 (`Fixed`) | $\infty$ |
| `part_3` | Cargo Goods A (적재물 세트 A) | 랙 내부 적재 화물 | 동역학 강체 (`Dynamic`) | 체적 $\times 500\text{ kg/m}^3$ |
| `part_4` | Cargo Goods B (적재물 세트 B) | 통로 및 랙 하단 화물 | 동역학 강체 (`Dynamic`) | 체적 $\times 500\text{ kg/m}^3$ |

---

## 5. 출처 및 참고 문헌
1. Lloyd, S. "Least squares quantization in PCM." *IEEE Transactions on Information Theory* 28.2 (1982): 129-137.
2. Scikit-learn: Machine Learning in Python, Pedregosa et al., JMLR 12, pp. 2825-2830, 2011.
3. World Labs Marble Documentation: Semantics & Collider Meshes (`https://docs.worldlabs.ai`).
