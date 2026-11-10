# 검수 및 수정 기록 — 2026-10-04

## 수정

1. Nootbaar 카드에 양쪽 발뒤꿈치 수술 회복 후 6월 5일 복귀와 8월 3일 Arizona 트레이드 맥락을 추가했다. 334PA는 부상 복귀와 팀 이동을 겪은 표본이다. Savant의 STL 48경기·183PA·타율 .234·3HR와 Arizona 42경기·151PA·5HR를 대조했다. 합계는 90경기·334PA·8HR이며 시즌 wOBA .320과 xwOBA .343은 원래 보고서와 일치한다. 타율과 wOBA는 서로 다른 지표다.
2. Bat tracking의 근거 없는 2024-04-03을 삭제했다. Savant가 안내하는 데이터 범위는 2023 시즌 후반부터이며, MLB의 공개 소개일은 2024-05-13이다. 데이터 범위와 공개일을 구분했다. 2015-2026 전체를 커버하지 못한다는 결론은 유지한다.
3. PDF 코드 예시에서 DataFrame `features`와 열 목록 `feature_cols`를 분리하고 열 목록의 정의를 포함했다. 원래 `study.fit_model(train, features)`의 함수 인자 `features`는 열 목록이므로 실제 함수에는 이름 충돌 오류가 없었다. 기존 모델 코드를 변경할 필요는 없었다.
4. RMSE 그림 제목을 `Most recent year: 2026`으로 변경했다. 수치, 축 범위, 모델 선택, 공식 2027 전망은 동일하다. Korean HTML 및 notebook 내 그림도 반영했다.
5. 영문 `α=100·1000`, `n=15·25`, `21.3%·41.4%`, `2025·2026`을 명확한 and/respectively 표현으로 바꿨다. Hard-hit, K%, BB%, ISO는 이미 입력이며 새로 표시한 mean launch angle만 모델 외 설명 자료임을 명시했다.
6. Appendix E의 .025는 상측 단측 꼬리, 앞 벤치마크 표는 probability-ordered 양측 꼬리라는 차이를 명시했다.
7. 33/36은 원래 전체 정밀도 값으로 집계하면 맞으므로 유지했다. 표시된 반올림 값으로 비교하면 동점처럼 보일 수 있다는 설명을 추가했다.

## 다시 계산한 항목

- ZIP의 41개 원자료 파일 SHA256이 각 metadata와 모두 일치했다.
- 2026 Savant PA 합계와 MLB 합계는 183,849. Savant 선수 ID에 맞춰 대조하면 8명의 ±1PA 차이가 유지된다. 차이 원인은 확인되지 않았으며, 임의 수정하지 않았다.
- 5명, 2025/2026의 PA, wOBA, xwOBA, hard-hit, K%, BB%, ISO, mean launch angle과 생년월일 기반 7월 나이가 카드와 일치했다. ISO는 입력 CSV의 표시 SLG minus AVG로 계산한 값이다. 더 정밀한 비율로 계산한 공개 ISO와 마지막 자리 차이가 날 수 있다.
- 다섯 α 모두 2026 M3 RMSE > M2 RMSE. 개발 MAE의 M2 minus M1은 α=10에서 +0.000010913, 100에서 -0.000013765, 1000에서 -0.000389391이다. 기존 문장은 맞다.
- 전체 정밀도 민감도 개수 및 범위, 정책 성공 수 및 손실 분해, 무작위 분포 및 꼬리, 검정력 예시는 일치했다. 재계산 결과는 supplement의 CSV/JSON에 있다.
- 선수 소속은 공개 MLB/Savant 프로필에서 Miami, Athletics, Cincinnati, Arizona, Cincinnati로 대조했다. 현재 소속 표시는 역사 시즌 전체를 동일 팀에서 보냈다는 의미가 아니다.

## 첨부 파일의 버전 차이

첨부 영문 PDF 두 개는 SHA256까지 같은 27쪽 문서다. 첨부 ZIP에는 더 이른 22쪽 한국어 PDF와 core 코드/자료가 들어 있으며, 영문 PDF가 참조한 `src/report_supplement.py`, `src/refine_report.py`, `src/decision_addendum.py`, 이전 follow-up addendum/hash 등은 없다.

없는 원본을 복원했다고 주장하지 않는다. 이번에 별도 `src/review_verification.py`로 해당 수치 검증을 재계산하고, `src/review_presentation.py`로 제공된 영문 PDF의 레이아웃을 유지하며 수정했다. Appendix E 규칙은 제공 PDF에서 별도 전사했다. 영문 PDF의 실행 명령과 경로도 실제 ZIP 내용에 맞게 수정했다. 원자료, 공식 전망, 원래 2027 평가 계획과 해시는 보존했다. 원래 PDF/그림은 reference에 보관한다.

## 공개 출처

Accessed 2026-10-04.

- Nootbaar Savant: https://baseballsavant.mlb.com/savant-player/lars-nootbaar-663457
- Injury recovery / June 5 return: https://www.reuters.com/sports/reports-cardinals-ship-lars-nootbaar-diamondbacks--flm-2026-08-03/
- Trade date: https://www.mlb.com/amp/press-release/d-backs-acquire-lars-nootbaar-from-cardinals.html
- Bat tracking coverage: https://baseballsavant.mlb.com/leaderboard/bat-tracking
- Public introduction: https://www.mlb.com/news/what-you-need-to-know-about-statcast-bat-tracking
- Other roster profiles: https://baseballsavant.mlb.com/savant-player/heriberto-hernandez-681715 ; https://www.mlb.com/player/lawrence-butler-671732 ; https://www.mlb.com/player/spencer-steer-668715 ; https://www.mlb.com/player/tyler-stephenson-663886

## 재현

```bash
python -m src.review_verification
python -m src.review_presentation
```

Core 환경은 requirements.txt, PDF 수정 환경은 추가로 PyMuPDF를 사용한다. Notebook의 계산 로직은 동일하며, 고정된 numeric 결과를 확인하는 기존 assertion이 유지된다. 업데이트된 HTML/그림은 self-contained payload와 저장된 출력에 반영했다.
