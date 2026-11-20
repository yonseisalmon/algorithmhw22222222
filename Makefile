# 과제2를 한 단어로 돌리기 위한 Makefile.
# 컨테이너 안에서 실행한다 (Codespaces 터미널, 또는 docker compose exec lab bash).
#
#   make test        유닛 테스트 (tests/test_*.py)
#   make serve       체이닝(8000) + 선형 탐지(8001) 웹 서버
#   make serve STRATEGY=linear  선형 탐지만 포트 8000에서 실행
#   make experiment  적재율에 따른 탐지 횟수 실험
#   make compare     두 충돌 처리 방식 비교 및 보고서 생성
#   make clean       캐시 정리
#
# 외부 라이브러리를 쓰지 않는다. Python 표준 모듈만으로 돈다.

PORT ?= 8000
LINEAR_PORT ?= 8001
STRATEGY ?= both

ifeq ($(STRATEGY),both)
SERVE_ARGS = --port $(PORT) --linear-port $(LINEAR_PORT)
else
SERVE_ARGS = --port $(PORT) --strategy $(STRATEGY)
endif

.PHONY: all test serve experiment compare clean

all: test

test:
	@python3 -m unittest discover -s tests -v

serve:
	@python3 -m src.server $(SERVE_ARGS)

experiment:
	@python3 -m experiments.probe_experiment

compare:
	@python3 -m experiments.compare_probing

clean:
	rm -rf src/__pycache__ tests/__pycache__ experiments/__pycache__
