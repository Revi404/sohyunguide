# 소현생정 링크페이지

인스타그램 프로필용 링크페이지 → https://revi404.github.io/sohyunguide/

## 자동으로 되는 것

| 항목 | 방식 | 주기 |
|---|---|---|
| 블로그 새 글 탭 | 네이버 블로그 RSS에서 카테고리별 최신 글 수집 | 3시간마다 |
| 추천템 탭 | 블로그 글 본문의 제휴 링크(쿠팡·여기어때·마이리얼트립 등)를 찾아 카드로 표시 | 3시간마다 |
| 배포 | GitHub Actions → GitHub Pages | 수집 직후 · 파일 수정 시 |

- 최근 14일 안의 글은 매번 다시 확인하므로, 발행 후 제휴 링크를 추가해도 반영됩니다.
- RSS에서 빠진 예전 글의 제휴 링크도 `data/affiliates-cache.json`에 남아 계속 노출됩니다.
- 바로 반영하려면: 저장소 → Actions → "블로그 수집 및 배포" → Run workflow

## 직접 수정하는 곳: `config.json`

| 하고 싶은 것 | 수정 위치 |
|---|---|
| 상단 공지 띄우기 | `notice.show`를 `true`, `text`·`url` 입력 |
| 바로가기 버튼 추가 | `links`에 항목 추가 (`icon`: blog·mail·insta·youtube·link) |
| 블로그 밖 상품 직접 추가 | `products`에 항목 추가 (아래 예시) |
| 자동 수집된 상품 숨기기 | `affiliate.hidden`에 그 상품의 제휴 URL 추가 |
| 새 제휴처 인식 | `affiliate.rules`에 `{ "partner": "이름", "match": ["도메인"] }` 추가 |
| 카테고리별 글 개수 | `blog.perCategory` |
| 클릭 통계 | GoatCounter 가입 후 코드(예: `sohyunguide`)를 `goatcounter`에 입력 |

상품 직접 추가 예시:

```json
"products": [
  { "title": "상품명", "partner": "쿠팡", "url": "https://link.coupang.com/a/xxxx",
    "image": "assets/products/상품.jpg", "note": "한 줄 평", "cta": "최저가 보기",
    "postUrl": "https://blog.naver.com/teanotcar/글번호" }
]
```
