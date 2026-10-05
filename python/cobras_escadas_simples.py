"""
Cobras e Escadas - solução computacional

Como o problema foi resolvido
-----------------------------
1. SIMULAÇÃO (Monte Carlo): o jogo é simulado 10.000 vezes em cada cenário e as
   respostas são as médias/frequências observadas, com intervalo de confiança.
2. CONFERÊNCIA EXATA: cada jogador, isoladamente, é uma cadeia de Markov (a
   próxima casa só depende da casa atual). Com isso dá para calcular as respostas
   sem sorteio nenhum. Usei esse cálculo para checar se a simulação está certa.

Os dois métodos precisam dar praticamente o mesmo número. Se derem, o código
está correto.

Como rodar:  python cobras_escadas.py      (precisa do numpy)
"""

import math
import random

import numpy as np

# ---------------------------------------------------------------------------
# 1. TABULEIRO (lido da figura)
# ---------------------------------------------------------------------------
ULTIMA = 36
ESCADAS = {3: 16, 5: 7, 15: 25, 18: 20, 21: 32}  # base -> topo
COBRAS = {12: 2, 14: 11, 17: 4, 31: 19, 35: 22}  # cabeça -> rabo

N_JOGOS = 10_000
SEMENTE = 2026  # semente fixa: quem rodar de novo obtém os mesmos números


# ---------------------------------------------------------------------------
# 2. SIMULAÇÃO
# ---------------------------------------------------------------------------
def jogar_partida(rng, inicio_j2=1, p_escada=1.0, j2_imune=False):
    """Simula UMA partida. Devolve (vencedor, total de lances, total de cobras).

    inicio_j2 : casa onde o jogador 2 começa            (pergunta 4)
    p_escada  : chance de a escada funcionar            (pergunta 3)
    j2_imune  : jogador 2 ignora a primeira cobra       (pergunta 5)
    """
    casa = [1, inicio_j2]  # posição de cada jogador
    imune = [False, j2_imune]  # quem ainda tem imunidade
    lances = 0
    cobras = 0
    vez = 0  # 0 = jogador 1 (começa), 1 = jogador 2

    while True:
        lances += 1
        nova = min(casa[vez] + rng.randint(1, 6), ULTIMA)  # passar da última = chegar

        if nova in ESCADAS:
            if rng.random() < p_escada:  # se p_escada = 1 sempre sobe
                nova = ESCADAS[nova]
        elif nova in COBRAS:
            if imune[vez]:
                imune[vez] = False  # gasta a imunidade, fica na casa
            else:
                nova = COBRAS[nova]
                cobras += 1

        casa[vez] = nova
        if nova == ULTIMA:
            return vez, lances, cobras
        vez = 1 - vez  # passa a vez


def simular(semente, n=N_JOGOS, **regras):
    """Joga n partidas e devolve três vetores: vencedores, lances e cobras."""
    rng = random.Random(semente)
    resultados = [jogar_partida(rng, **regras) for _ in range(n)]
    vencedores, lances, cobras = zip(*resultados, strict=True)
    return np.array(vencedores), np.array(lances), np.array(cobras)


def media_ic(x):
    """Média e intervalo de confiança de 95% (aproximação normal)."""
    x = np.asarray(x, dtype=float)
    erro = 1.96 * x.std(ddof=1) / math.sqrt(len(x))
    return x.mean(), erro


# ---------------------------------------------------------------------------
# 3. CÁLCULO EXATO (cadeia de Markov) - usado só para conferir a simulação
# ---------------------------------------------------------------------------
# Estado de um jogador = (casa, já usou a imunidade?). Cada lance leva de um
# estado a outros com probabilidade 1/6 por face do dado. Propagando a
# distribuição lance a lance obtemos, para um jogador sozinho:
#   f[n] = P(termina exatamente no lance n+1)
#   S[n] = P(ainda não terminou depois de n lances)
#   s[n] = P(cair numa cobra no lance n+1)
NMAX = 1000  # a chance de passar de 1000 lances é ~1e-90: pode ignorar


def distribuicao(inicio=1, p_escada=1.0, imune=False):
    K = 2 * (ULTIMA + 1)

    def idx(casa, usou):
        return casa + (ULTIMA + 1) * usou

    P = np.zeros((K, K))  # matriz de transição
    h = np.zeros(K)  # chance de cair numa cobra a partir de cada estado
    for usou in (0, 1):
        for i in range(1, ULTIMA):
            for d in range(1, 7):
                j = min(i + d, ULTIMA)
                de = idx(i, usou)
                if j in COBRAS:
                    if usou == 0:
                        P[de, idx(j, 1)] += 1 / 6  # imunidade gasta
                    else:
                        P[de, idx(COBRAS[j], 1)] += 1 / 6
                        h[de] += 1 / 6
                elif j in ESCADAS:
                    P[de, idx(ESCADAS[j], usou)] += p_escada / 6
                    P[de, idx(j, usou)] += (1 - p_escada) / 6
                else:
                    P[de, idx(j, usou)] += 1 / 6
        P[idx(ULTIMA, usou), idx(ULTIMA, usou)] = 1  # fim: estado absorvente

    v = np.zeros(K)
    v[idx(inicio, 0 if imune else 1)] = 1
    fim = [idx(ULTIMA, 0), idx(ULTIMA, 1)]

    S = [1 - v[fim].sum()]
    s = []
    for _ in range(NMAX):
        s.append(v @ h)
        v = v @ P
        S.append(1 - v[fim].sum())
    S, s = np.array(S), np.array(s)
    f = S[:-1] - S[1:]
    return f, S, s


def exato_p_j1(a, b):
    """P(jogador 1 vence). J1 joga primeiro: ele vence se terminar no lance n
    e o J2 ainda não tiver terminado nos n-1 lances anteriores."""
    return float(np.sum(a[0] * b[1][:-1]))


def exato_cobras(a, b):
    """Cobras esperadas dos dois. J1 joga o lance n se J2 ainda não terminou
    antes; J2 joga o lance n se J1 ainda não terminou até o lance n."""
    return float(np.sum(a[2] * b[1][:-1]) + np.sum(b[2] * a[1][1:]))


def exato_lances(a, b):
    """Lances esperados na partida. Se J1 vence no seu lance n, foram 2n-1
    lances no total; se J2 vence no seu lance n, foram 2n."""
    n = np.arange(1, NMAX + 1)
    return float(np.sum(a[0] * b[1][:-1] * (2 * n - 1)) + np.sum(b[0] * a[1][1:] * 2 * n))


# ---------------------------------------------------------------------------
# 4. RESPOSTAS
# ---------------------------------------------------------------------------
def confere(nome, valor, erro, exato):
    """Mostra o resultado da simulação ao lado do valor exato."""
    z = (valor - exato) / (erro / 1.96)
    print(
        f"{nome:<36} simulado {valor:7.4f} +- {erro:.4f}   exato {exato:7.4f}"
        f"   {'ok' if abs(z) < 3.5 else 'DIVERGE'}"
    )
    return abs(z) < 3.5


def main():
    tudo_ok = True
    base = distribuicao()  # jogador "normal", usado nas perguntas 1, 2 e 4

    # Pergunta 1: probabilidade de o jogador que começa vencer
    venc, lances, cobras = simular(SEMENTE + 1)
    m, e = media_ic(venc == 0)
    tudo_ok &= confere("P1  P(jogador 1 vence)", m, e, exato_p_j1(base, base))

    # Pergunta 2: média de cobras por jogo (somando os dois jogadores)
    m, e = media_ic(cobras)
    tudo_ok &= confere("P2  cobras por jogo", m, e, exato_cobras(base, base))

    # Pergunta 3: escada só funciona em 50% das vezes -> lances por jogo
    meia = distribuicao(p_escada=0.5)
    _, lances, _ = simular(SEMENTE + 3, p_escada=0.5)
    m, e = media_ic(lances)
    tudo_ok &= confere("P3  lances por jogo (escada 50%)", m, e, exato_lances(meia, meia))

    # Pergunta 4: em que casa o jogador 2 deve começar para equilibrar?
    # Testo todas as casas (menos as de cobra/escada, onde ninguém "para").
    # Passo 1: 10.000 jogos em cada casa. As casas 7 e 8 dão resultados quase
    # iguais (diferença ~0,01, do tamanho do erro), então 10.000 jogos não
    # bastam para escolher entre elas.
    # Passo 2: as casas que ficaram perto de 0,5 são simuladas de novo com
    # 200.000 jogos, o que separa uma da outra.
    candidatas = [c for c in range(1, ULTIMA) if c not in ESCADAS and c not in COBRAS]
    finalistas = []
    exatos = {}
    for c in candidatas:
        venc, _, _ = simular(SEMENTE + 4, inicio_j2=c)
        m, e = media_ic(venc == 0)
        exatos[c] = exato_p_j1(base, distribuicao(inicio=c))
        if abs(m - 0.5) < 3 * e / 1.96:
            finalistas.append(c)
    refinado = {}
    for c in finalistas:
        venc, _, _ = simular(SEMENTE + 40, n=200_000, inicio_j2=c)
        refinado[c] = (venc == 0).mean()
    melhor = min(refinado, key=lambda c: abs(refinado[c] - 0.5))
    melhor_exato = min(exatos, key=lambda c: abs(exatos[c] - 0.5))
    print(
        f"P4  melhor casa para o jogador 2:    simulado {melhor}"
        f" (P1 vence {refinado[melhor]:.4f})   exato {melhor_exato}"
        f" (P1 vence {exatos[melhor_exato]:.4f})   "
        f"{'ok' if melhor == melhor_exato else 'DIVERGE'}"
    )
    tudo_ok &= melhor == melhor_exato

    # Pergunta 5: jogador 2 imune à primeira cobra
    venc, _, _ = simular(SEMENTE + 5, j2_imune=True)
    m, e = media_ic(venc == 0)
    exato5 = exato_p_j1(base, distribuicao(imune=True))
    tudo_ok &= confere("P5  P(jogador 1 vence), J2 imune", m, e, exato5)

    print("\nSimulação e cálculo exato concordam:", "SIM" if tudo_ok else "NÃO")


if __name__ == "__main__":
    main()
