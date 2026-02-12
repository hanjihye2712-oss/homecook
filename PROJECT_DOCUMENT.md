# HomeCook 프로젝트 문서

## 1. 프로젝트 개요

홈쿡(HomeCook)은 Django 기반의 요리 챌린지 플랫폼입니다.
사용자가 음식 이미지, 영수증, 레시피, 기록장을 챌린지 세트 단위로 관리하고, 다른 사용자와 공유할 수 있습니다.

---

## 2. 기술 스택

| 항목 | 버전 |
|------|------|
| Python | 3.14 |
| Django | 6.0.1 |
| Pillow | 12.1.0 |
| Database | SQLite3 |
| Language | Korean (ko-kr) |
| Timezone | Asia/Seoul |

---

## 3. 디렉토리 구조

```
homecook/                          # 프로젝트 루트
├── manage.py
├── requirements.txt
├── db.sqlite3
├── .venv/                         # 가상환경
│
├── mysite/                        # Django 프로젝트 설정
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── homecook/                      # 메인 앱 (요리 챌린지)
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── forms.py
│   ├── admin.py
│   ├── apps.py
│   └── migrations/
│
├── accounts/                      # 사용자 인증 & 프로필
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── forms.py
│   └── migrations/
│
├── information/                   # 가계부 (금융 거래 추적)
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── forms.py
│   └── migrations/
│
├── templates/homecook/            # HTML 템플릿 (20개)
│   ├── challenge_set_create_all.html
│   ├── challenge_set_edit.html
│   ├── challenge_set_confirm_delete.html
│   ├── food_image_form.html
│   ├── food_image_detail.html
│   ├── food_image_confirm_delete.html
│   ├── receipt_form.html
│   ├── receipt_detail.html
│   ├── receipt_confirm_delete.html
│   ├── recipe_form.html
│   ├── recipe_detail.html
│   ├── recipe_confirm_delete.html
│   ├── journal_form.html
│   ├── journal_detail.html
│   ├── landing.html
│   ├── my_challenge.html
│   ├── walking.html
│   ├── weight.html
│   └── healing.html
│
├── static/homecook/
│   ├── css/                       # 스타일시트 (16개)
│   │   ├── base.css
│   │   ├── accounts.css
│   │   ├── dashboard.css
│   │   ├── detail.css
│   │   ├── index.css
│   │   ├── landing.css
│   │   ├── main_index.css
│   │   ├── my_challenge.css
│   │   ├── receipt_detail.css
│   │   └── ...
│   └── img/
│       └── background.jpg
│
└── media/                         # 사용자 업로드 파일
    ├── food_images/
    └── receipts/
```

---

## 4. 모델 구조

### 4.1 homecook 앱

#### ChallengeSet (챌린지 세트)
음식이미지, 영수증, 레시피, 기록장을 하나로 묶는 단위

| 필드 | 타입 | 설명 |
|------|------|------|
| user | ForeignKey(User) | 작성자 |
| title | CharField(100) | 챌린지 제목 |
| created_at | DateTimeField | 생성일시 (자동) |
| updated_at | DateTimeField | 수정일시 (자동) |

#### FoodImage (음식 이미지)

| 필드 | 타입 | 설명 |
|------|------|------|
| challenge_set | OneToOneField | 챌린지 세트 연결 |
| user | ForeignKey(User) | 작성자 |
| image | ImageField | 이미지 파일 (최대 5MB, jpg/jpeg/png) |
| title | CharField(100) | 제목 (선택) |
| created_at | DateTimeField | 생성일시 (자동) |

#### Receipt (영수증)

| 필드 | 타입 | 설명 |
|------|------|------|
| challenge_set | OneToOneField | 챌린지 세트 연결 |
| user | ForeignKey(User) | 작성자 |
| image | ImageField | 영수증 이미지 |
| created_at | DateTimeField | 생성일시 (자동) |

#### Recipe (레시피)

| 필드 | 타입 | 설명 |
|------|------|------|
| challenge_set | OneToOneField | 챌린지 세트 연결 |
| user | ForeignKey(User) | 작성자 |
| title | CharField(100) | 레시피 제목 |
| content | TextField(300) | 레시피 내용 (최대 300자) |
| views | IntegerField | 조회수 |
| likes | ManyToManyField(User) | 좋아요 |
| created_at | DateTimeField | 생성일시 (자동) |
| updated_at | DateTimeField | 수정일시 (자동) |

#### Journal (기록장)

| 필드 | 타입 | 설명 |
|------|------|------|
| challenge_set | OneToOneField | 챌린지 세트 연결 |
| user | ForeignKey(User) | 작성자 |
| title | CharField(100) | 제목 |
| content | TextField(200) | 내용 (최대 200자) |
| visibility | CharField(10) | 공개/비공개 |
| created_at | DateTimeField | 생성일시 (자동) |
| updated_at | DateTimeField | 수정일시 (자동) |

### 4.2 accounts 앱

#### UserProfile (사용자 프로필)

| 필드 | 타입 | 설명 |
|------|------|------|
| user | OneToOneField(User) | 사용자 연결 |
| points | IntegerField | 포인트 (챌린지 생성 시 +100P) |

### 4.3 information 앱

#### Transaction (거래 내역)

| 필드 | 타입 | 설명 |
|------|------|------|
| user | ForeignKey(User) | 사용자 |
| transaction_type | CharField | 입금/출금/서울페이 |
| amount | DecimalField | 금액 |
| category | CharField | 카테고리 (급여, 식비, 교통비 등) |
| description | CharField | 설명 |
| balance_after | DecimalField | 거래 후 잔액 |
| transaction_date | DateField | 거래일 |
| memo | TextField | 메모 (선택) |

---

## 5. URL 패턴

### 5.1 루트 URL (mysite/urls.py)

| URL | 앱 |
|-----|-----|
| `/admin/` | Django Admin |
| `/` | homecook 앱 |
| `/accounts/` | accounts 앱 + Django auth |
| `/information/` | information 앱 |

### 5.2 homecook 앱 URL (homecook/urls.py)

#### 메인 페이지

| URL | View | 설명 |
|-----|------|------|
| `/` | MainIndexView | 2x2 카테고리 그리드 |
| `/walking/` | WalkingView | 오늘의 Walking |
| `/weight/` | WeightView | 오늘의 Weight |
| `/healing/` | HealingView | 오늘의 Healing |
| `/landing/` | HomecookLandingView | 홈쿡 랜딩 (최근 음식 사진 30개) |

#### 챌린지 세트 관리

| URL | View | 설명 |
|-----|------|------|
| `/my-challenge/` | HomecookMyChallengeView | 내 챌린지 목록 |
| `/challenge-set/create/` | HomecookChallengeSetCreateView | 챌린지 세트 생성 |
| `/challenge-set/<pk>/edit/` | HomecookChallengeSetEditView | 챌린지 세트 편집 |
| `/challenge-set/<pk>/delete/` | HomecookChallengeSetDeleteView | 챌린지 세트 삭제 |
| `/challenge-set/<pk>/update-title/` | update_challenge_set_title | 제목 수정 (POST) |

#### 항목 추가 (POST)

| URL | View | 설명 |
|-----|------|------|
| `/challenge-set/<set_pk>/add-food-image/` | add_food_image_to_set | 음식 이미지 추가 |
| `/challenge-set/<set_pk>/add-receipt/` | add_receipt_to_set | 영수증 추가 |
| `/challenge-set/<set_pk>/add-recipe/` | add_recipe_to_set | 레시피 추가 |
| `/challenge-set/<set_pk>/add-journal/` | add_journal_to_set | 기록장 추가 |

#### 상세보기 / 수정 / 삭제

| URL | 설명 |
|-----|------|
| `/food-image/<pk>/` | 음식 이미지 상세 |
| `/food-image/<pk>/update/` | 음식 이미지 수정 |
| `/food-image/<pk>/delete/` | 음식 이미지 삭제 |
| `/receipt/<pk>/` | 영수증 상세 |
| `/receipt/<pk>/update/` | 영수증 수정 |
| `/receipt/<pk>/delete/` | 영수증 삭제 |
| `/recipe/<pk>/` | 레시피 상세 (조회수 증가) |
| `/recipe/<pk>/update/` | 레시피 수정 |
| `/recipe/<pk>/delete/` | 레시피 삭제 |
| `/recipe/<pk>/like/` | 레시피 좋아요 토글 (AJAX) |
| `/journal/<pk>/` | 기록장 상세 (접근 제어) |
| `/journal/<pk>/update/` | 기록장 수정 |
| `/journal/<pk>/delete/` | 기록장 삭제 |

---

## 6. Views 구조

### 유틸리티 함수

| 함수 | 설명 |
|------|------|
| `check_image_resolution()` | 이미지 해상도 체크 (권장: 1000x1000) |
| `delete_file_safely()` | 파일 안전 삭제 |

### Mixin 클래스

| Mixin | 설명 |
|-------|------|
| `UserFilterMixin` | 사용자별 데이터 필터링 |
| `SuccessMessageMixin` | 성공 메시지 표시 |
| `DeleteMessageMixin` | 삭제 메시지 표시 |

---

## 7. 주요 기능

### 7.1 챌린지 세트 시스템
- 음식 이미지 + 영수증 + 레시피 + 기록장을 하나의 세트로 묶어 관리
- 세트 생성 시 **100P 적립**, 삭제 시 **100P 차감**
- 통합 생성 폼에서 한 번에 모든 항목 등록 가능
- 편집 페이지에서 개별 항목 추가/수정/삭제 가능

### 7.2 소셜 기능
- **랜딩 페이지**: 다른 사용자들의 최근 음식 사진 30개 표시
- **레시피 공유**: 공개 레시피 조회수, 좋아요 기능
- **기록장 공개/비공개**: 공개 설정 시 다른 사용자도 열람 가능

### 7.3 포인트 시스템
- 챌린지 세트 생성 시 100P 적립
- 챌린지 세트 삭제 시 100P 차감 (최소 0P)

### 7.4 이미지 관리
- 음식 이미지: 최대 5MB, jpg/jpeg/png, 권장 1000x1000px
- 영수증 이미지: 최대 10MB
- 이미지 업로드 시 미리보기 지원
- 삭제 시 파일 시스템에서도 안전하게 제거

---

## 8. 변경 이력

### 2026-02-10: OCR 기능 제거

영수증 관련 코드는 유지하고, OCR(텍스트 추출) 기능만 제거

#### 제거된 항목

| 파일 | 제거 내용 |
|------|----------|
| `homecook/models.py` | `ocr_text` (TextField), `is_processed` (BooleanField) 필드 |
| `homecook/views.py` | `process_ocr()` 함수, `pytesseract` import |
| `homecook/views.py` | `_add_receipt()`, `add_receipt_to_set()`, `ReceiptUpdateView`에서 OCR 호출 |
| `homecook/forms.py` | OCR 관련 help_text |
| `homecook/admin.py` | `is_processed` list_display/list_filter |
| `receipt_detail.html` | OCR 텍스트 표시 섹션, 처리 상태 배지 |
| `receipt_form.html` | 버튼 텍스트 "업로드 & OCR 처리" → "업로드" |
| `receipt_confirm_delete.html` | 처리 상태 배지, OCR 삭제 안내 문구 |
| `challenge_set_create_all.html` | 헤더에서 "OCR" 텍스트, OCR help text |
| `challenge_set_edit.html` | `is_processed` 상태 배지 |
| `receipt_detail.css` | `.ocr-text-full` 스타일 |
| `requirements.txt` | `pytesseract==0.3.13` 패키지 |

#### 적용된 Migration
- `0005_remove_receipt_is_processed_remove_receipt_ocr_text`
