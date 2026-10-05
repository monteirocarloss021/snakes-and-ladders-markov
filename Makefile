PY      ?= python3
CXX     ?= g++
CXXFLAGS = -std=c++17 -O2 -Wall -Wextra -Wpedantic -Werror

.PHONY: help install run test lint format cpp cpp-run sanitize figures clean

help:            ## lista os comandos
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

install:         ## instala dependências de desenvolvimento
	$(PY) -m pip install -e ".[dev,analise]"

run:             ## roda a solução completa em Python
	$(PY) python/cobras_escadas.py

test:            ## roda a suíte de testes
	$(PY) -m pytest

lint:            ## checa estilo e erros comuns
	ruff check . && ruff format --check .

format:          ## formata o código
	ruff format . && ruff check --fix .

cpp:             ## compila a versão C++
	$(CXX) $(CXXFLAGS) -o cobras cpp/cobras_escadas.cpp

cpp-run: cpp     ## compila e roda a versão C++
	./cobras

sanitize:        ## compila com AddressSanitizer + UBSan e roda
	$(CXX) $(CXXFLAGS) -g -fsanitize=address,undefined -fno-omit-frame-pointer \
		-o cobras-san cpp/cobras_escadas.cpp && ./cobras-san 2000

figures:         ## regenera as figuras do README
	$(PY) scripts/gerar_figuras.py

clean:           ## remove binários e caches
	rm -rf cobras cobras-san .pytest_cache .ruff_cache **/__pycache__
