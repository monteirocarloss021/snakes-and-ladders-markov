# Cobras e Escadas: simulação e cadeia de Markov

[![CI](https://github.com/monteirocarloss021/snakes-and-ladders-markov/actions/workflows/ci.yml/badge.svg)](https://github.com/monteirocarloss021/snakes-and-ladders-markov/actions/workflows/ci.yml)

Resolução de um problema de probabilidade sobre um jogo de Cobras e Escadas num tabuleiro 6×6. As perguntas pediam simulações de 10.000 partidas. Além de simular, resolvi o problema de forma exata com cadeias de Markov e usei isso para conferir a simulação.

<p align="center"><img src="figures/tabuleiro.png" width="440" alt="Tabuleiro com escadas e cobras"></p>

<p align="center"><sub>Cada casa mostra o número esperado de lances para terminar o jogo a partir dela.</sub></p>

## O problema

Dois jogadores começam na casa 1 e se revezam jogando um dado de 6 faces. Quem cai na base de uma escada sobe até o topo, e quem cai na cabeça de uma cobra desce até o rabo. Vence quem chegar ou passar da casa 36.

- **Escadas:** 3 → 16, 5 → 7, 15 → 25, 18 → 20, 21 → 32
- **Cobras:** 12 → 2, 14 → 11, 17 → 4, 31 → 19, 35 → 22

As perguntas eram:

1. Qual a probabilidade de o jogador que começa vencer?
2. Em média, em quantas cobras os jogadores caem por partida?
3. Se cada escada só funcionar com 50% de chance, quantos lances dura uma partida, em média?
4. Em qual casa o jogador 2 deve começar para que o jogo fique o mais justo possível?
5. Se o jogador 2 for imune à primeira cobra em que cair, qual a probabilidade de o jogador 1 vencer?

## Resultados

| Pergunta | Simulação (10.000 partidas) | Valor exato |
|:-:|:-:|:-:|
| 1 | 0,531 ± 0,010 | 0,5255 |
| 2 | 3,09 ± 0,05 | 3,094 |
| 3 | 22,4 ± 0,2 | 22,49 |
| 4 | casa 7 | casa 7 |
| 5 | 0,383 ± 0,010 | 0,3864 |

Os valores com ± são intervalos de confiança de 95%.

Hipóteses que adotei onde o enunciado deixava dúvida:

- Na pergunta 2, contei as cobras dos dois jogadores juntos.
- Na pergunta 3, contei os lances dos dois jogadores. Se a escada falhar, o jogador fica na base dela.
- Na pergunta 4, não considerei as casas de base de escada nem de cabeça de cobra, porque ninguém para nelas.
- Na pergunta 5, ao cair na primeira cobra o jogador 2 fica na cabeça dela e perde a imunidade.

## Como resolvi

### 1. Simulação

Escrevi uma função que joga uma partida inteira e outra que repete isso 10.000 vezes. As variações das perguntas 3, 4 e 5 entram como parâmetros da mesma função, então a lógica do jogo fica escrita uma vez só. A semente aleatória é fixa, para os resultados serem reproduzíveis.

Para as probabilidades usei o intervalo de Wilson, e para as médias, o intervalo usual com o desvio padrão amostral $s$:

$$
\bar{x} \pm 1{,}96 \, \frac{s}{\sqrt{n}}
$$

A pergunta 4 deu mais trabalho. Com o jogador 2 começando na casa 7, o jogador 1 vence com probabilidade 0,4968, e na casa 8 com 0,4881. Essa diferença é menor que a margem de erro de 10.000 partidas (cerca de ±0,01), e em alguns testes a simulação escolhia a casa errada. Por isso fiz em duas etapas: primeiro simulei todas as casas com 10.000 partidas, depois simulei de novo só as casas que ficaram perto de 0,5, com 200.000 partidas.

### 2. Solução exata com cadeia de Markov

A próxima casa de um jogador depende só da casa em que ele está, então cada jogador sozinho é uma cadeia de Markov, com a casa 36 como estado absorvente. Para a pergunta 5, o estado também guarda se a imunidade já foi usada.

Montei a matriz de transição $P$ e fui propagando a distribuição de probabilidade lance a lance:

$$
v_{n+1} = v_n \, P
$$

Com isso calculei, para um jogador sozinho, três sequências:

$$
f_n = P(T = n), \qquad S_n = P(T > n), \qquad s_n = P(\text{cair numa cobra no lance } n)
$$

em que $T$ é o número de lances que ele leva para terminar.

Os dois jogadores não interferem um no outro, então $T_1$ e $T_2$ são independentes. O jogador 1 joga primeiro, logo ele vence se terminar no seu lance $n$ antes de o jogador 2 terminar:

$$
P(\text{J1 vence}) = \sum_{n \geq 1} f^{(1)}_n \, S^{(2)}_{n-1}
$$

Essa fórmula responde às perguntas 1, 4 e 5. Para as outras duas, o raciocínio é parecido. O jogador 1 faz o lance $n$ se $T_2 \geq n$, e o jogador 2 faz o lance $n$ se $T_1 > n$. Assim, o número esperado de cobras é

$$
E[\text{cobras}] = \sum_{n \geq 1} \left( s^{(1)}_n \, S^{(2)}_{n-1} + s^{(2)}_n \, S^{(1)}_n \right)
$$

Se o jogador 1 vence no seu lance $n$, a partida teve $2n - 1$ lances. Se o jogador 2 vence, teve $2n$. Então

$$
E[\text{lances}] = \sum_{n \geq 1} \left( (2n-1) \, f^{(1)}_n \, S^{(2)}_{n-1} + 2n \, f^{(2)}_n \, S^{(1)}_n \right)
$$

As somas foram feitas até $n = 4000$. A probabilidade de uma partida durar tanto é desprezível.

### 3. Conferência

O programa compara cada resultado da simulação com o valor exato e só termina sem erro se a diferença for pequena (menos de 3,5 erros padrão). Também escrevi testes que conferem as regras do jogo com sequências de dados fixas, por exemplo "tirando 2 na casa 1, o jogador tem que parar na 16".

## Algumas observações

**A vantagem de começar vem só dos empates.** Por simetria, a chance de o jogador 1 terminar em menos lances que o jogador 2 é igual à chance contrária. A diferença está no caso em que os dois precisam do mesmo número de lances, que o jogador 1 sempre ganha por jogar antes. Por isso

$$
P(\text{J1 vence}) = \frac{1}{2} + \frac{1}{2} \, P(T_1 = T_2) = \frac{1}{2} + \frac{1}{2} \sum_{n \geq 1} f_n^2 \approx 0{,}5255
$$

<p align="center"><img src="figures/convergencia.png" width="680" alt="Convergência da simulação"></p>

**A curva da pergunta 4 não é monótona.** Começar na casa 11 é pior para o jogador 2 do que na 10, porque da 11 três das seis faces caem em cobras (12, 14 e 17).

<p align="center"><img src="figures/equilibrio_q4.png" width="680" alt="Probabilidade do jogador 1 vencer em função da casa inicial do jogador 2"></p>

**A imunidade pesa muito.** Ignorar uma única cobra faz a chance do jogador 1 cair de 52,6% para 38,6%. O número médio de lances do jogador 2 para terminar cai de 13,4 para 10,6.

**Escadas pela metade deixam o jogo cerca de 18% mais longo**, de 19,05 para 22,49 lances por partida:

<p align="center"><img src="figures/duracao.png" width="680" alt="Distribuição do número de lances da partida"></p>

## Como rodar

```bash
pip install -r requirements.txt
python python/cobras_escadas.py
```

Também dá para mudar o número de partidas e a semente:

```bash
python python/cobras_escadas.py --jogos 100000 --semente 7
```

Fiz uma versão em C++, que roda bem mais rápido:

```bash
g++ -std=c++17 -O2 -o cobras cpp/cobras_escadas.cpp
./cobras
```

Para rodar os testes:

```bash
pip install pytest
pytest
```

## Arquivos

| Pasta | Conteúdo |
|---|---|
| `python/` | `cobras_escadas.py` (solução completa) e `cobras_escadas_simples.py` (versão mais curta e comentada) |
| `cpp/` | a mesma solução em C++ |
| `tests/` | testes automáticos |
| `notebooks/` | notebook com a análise e os gráficos |
| `scripts/` | script que gera as figuras |

---

Carlos Alberto Monteiro da Cunha, Engenharia Civil-Aeronáutica, ITA. Licença MIT.
