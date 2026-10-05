<div align="center">

# 🐍🪜 Cobras e Escadas: simulação × cadeia de Markov

**Quem começa tem vantagem? Quantas cobras você pisa por partida? Dá para deixar o jogo justo?**
Respondido duas vezes: com 10.000 partidas simuladas por cenário **e** com o cálculo exato, e as duas respostas precisam bater.

[![CI](https://github.com/monteirocarloss021/snakes-and-ladders-markov/actions/workflows/ci.yml/badge.svg)](https://github.com/monteirocarloss021/snakes-and-ladders-markov/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![C++17](https://img.shields.io/badge/C%2B%2B-17-00599C?logo=cplusplus&logoColor=white)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

<img src="figures/tabuleiro.png" width="460" alt="Tabuleiro 6x6 com escadas e cobras; cada casa mostra o número esperado de lances até o fim">

<sub>Cada casa mostra quantos lances, em média, faltam para terminar a partir dela. Repare na casa 2 (13,3) praticamente igual à casa 1: cair na cobra da 12 te devolve para o começo.</sub>

</div>

---

## O jogo

Tabuleiro 6×6 (casas 1 a 36), dado justo de 6 faces, dois jogadores alternando, ambos começando na casa 1.

| Escadas (sobe) | Cobras (desce) |
|---|---|
| 3 → 16 · 5 → 7 · 15 → 25 · 18 → 20 · 21 → 32 | 12 → 2 · 14 → 11 · 17 → 4 · 31 → 19 · 35 → 22 |

Vence quem **chegar ou passar** da casa 36.

## As perguntas e as respostas

| # | Pergunta | Simulação (10⁴ jogos) | Exato |
|---|---|---|---|
| 1 | Probabilidade de quem começa vencer | 0,531 ± 0,010 | **0,5255** |
| 2 | Cobras por partida (os dois jogadores) | 3,09 ± 0,05 | **3,094** |
| 3 | Lances por partida se a escada só funciona 50% das vezes | 22,4 ± 0,2 | **22,49** |
| 4 | Casa inicial do J2 que deixa o jogo mais justo | casa 7 | **casa 7** (P = 0,4968) |
| 5 | P(J1 vence) se o J2 for imune à 1ª cobra | 0,383 ± 0,010 | **0,3864** |

## Como foi resolvido

### 1. Simulação (Monte Carlo)

Um único motor de jogo, parametrizado pelas regras de cada cenário (chance da escada, casa inicial do J2, imunidade). Cada cenário roda 10.000 partidas com semente fixa, e as respostas vêm com **intervalo de confiança de 95%** (Wilson para proporções, normal para médias).

### 2. Conferência exata (cadeia de Markov)

A próxima casa de um jogador depende só da casa atual, então cada jogador é uma **cadeia de Markov absorvente**. Para a Q5, o estado ganha um bit extra: *(casa, imunidade já usada?)*. Propagando a distribuição lance a lance, obtemos para um jogador isolado:

$$f_n = P(T=n), \qquad S_n = P(T>n), \qquad s_n = P(\text{cair em cobra no lance } n)$$

Como os jogadores não interagem, $T_1$ e $T_2$ são independentes. Como o J1 joga primeiro, ele vence se terminar no seu lance $n$ antes que o J2 termine:

$$P(\text{J1 vence}) = \sum_{n\ge1} f^{(1)}_n \, S^{(2)}_{n-1}$$

Com a mesma lógica saem as outras respostas:

- **Cobras:** $\sum_n s^{(1)}_n S^{(2)}_{n-1} + s^{(2)}_n S^{(1)}_n$.
- **Duração da partida:** $2n-1$ lances se o J1 vence no lance $n$, ou $2n$ se o J2 vence.

O programa **só termina com sucesso se a simulação concordar com o valor exato** em todas as perguntas. Isso roda automaticamente no CI a cada commit.

### 3. Testes do motor

Antes de simular, o motor é testado com um "dado roteirizado", isto é, sequências de lances fixas com resultado conhecido. Os testes cobrem escada, cobra, passar da casa 36, escada que falha e imunidade.

## Achados interessantes

**🎲 A vantagem de começar é exatamente metade da chance de empate.**
Por simetria, $P(T_1<T_2)=P(T_2<T_1)$. Quando os dois precisam do mesmo número de lances, quem joga primeiro leva. Então

$$P(\text{J1 vence}) = \tfrac12 + \tfrac12\,P(T_1=T_2) = \tfrac12 + \tfrac12\sum_n f_n^2 \approx 0{,}5255$$

<p align="center"><img src="figures/convergencia.png" width="720" alt="Convergência da estimativa de P(J1 vence) para o valor exato 0,5255"></p>

**⚖️ A Q4 é mais difícil do que parece.**
Com o J2 começando na casa 7, P(J1) = 0,4968. Na casa 8, P(J1) = 0,4881. A diferença (~0,009) é **menor que a margem de erro de 10.000 jogos** (±0,01), então só a simulação escolhe a casa errada em ~40% das sementes. A solução usa duas etapas:
1. **Triagem:** 10⁴ jogos em cada casa.
2. **Refinamento:** os finalistas são re-simulados com 2×10⁵ jogos.

<p align="center"><img src="figures/equilibrio_q4.png" width="720" alt="P(J1 vence) em função da casa inicial do J2"></p>

**🛡️ Imunidade vale mais que começar na frente.**
Ignorar uma única cobra derruba a chance do J1 de 52,6% para 38,6%. O J2 passa a levar em média ~10,6 lances para terminar, contra 13,4 sem imunidade.

**🐢 Escada que falha deixa o jogo ~18% mais longo** (19,05 → 22,49 lances), e a cauda da distribuição fica bem mais pesada:

<p align="center"><img src="figures/duracao.png" width="720" alt="Distribuição exata do número de lances na partida"></p>

## Estrutura

```
python/
  cobras_escadas.py          versão completa: simulação + Markov + testes + CLI
  cobras_escadas_simples.py  versão enxuta e comentada passo a passo
cpp/
  cobras_escadas.cpp         mesma solução em C++17, sem dependências (~0,1 s)
notebooks/
  analise.ipynb              análise interativa com gráficos
scripts/
  gerar_figuras.py           gera as figuras deste README
```

## Como rodar

```bash
pip install -r requirements.txt

python python/cobras_escadas.py                          # 10.000 jogos, semente 2026
python python/cobras_escadas.py --jogos 100000 --semente 7

g++ -std=c++17 -O2 -o cobras cpp/cobras_escadas.cpp && ./cobras
```

Saída (Python):

```
Q1 P(J1 vence)                       0.5308  [0.5210, 0.5406]   exato   0.5255  z=+1.06 ok
Q2 cobras/partida (J1+J2)             3.089  [3.038, 3.139]   exato    3.094  z=-0.20 ok
Q3 lances/partida (escada 50%)        22.39  [22.21, 22.56]   exato    22.49  z=-1.18 ok
   melhor casa: MC = 7 | exato = 7  ok
Q5 P(J1 vence), J2 imune             0.3828  [0.3733, 0.3924]   exato   0.3864  z=-0.74 ok

Validação MC x exato: TODAS OK
```

## Hipóteses

- O J1 joga primeiro. Chegar **ou passar** da casa 36 vence.
- **Q2** conta as cobras dos dois jogadores. **Q3** conta os lances dos dois jogadores; um jogador sozinho precisaria de 15,50.
- Escada que falha (Q3) deixa o jogador na base. O imune (Q5) fica na cabeça da cobra e perde a imunidade.
- Na Q4 ficam de fora as casas de cobra ou escada, onde ninguém "para". Começar na 5 equivale a começar na 7.

## Créditos

Por **Carlos Alberto Monteiro da Cunha** ([@monteirocarloss021](https://github.com/monteirocarloss021)), Engenharia Civil-Aeronáutica · ITA.
Código desenvolvido com auxílio do assistente de IA **Claude** (Anthropic).

Licença [MIT](LICENSE).
