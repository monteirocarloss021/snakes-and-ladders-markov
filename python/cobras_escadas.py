#!/usr/bin/env python3
"""
Cobras e Escadas (tabuleiro 6x6, casas 1..36) — solução computacional em Python
================================================================================
  1. Monte Carlo: 10.000 partidas por cenário (como pede o enunciado),
     com IC 95% (Wilson p/ proporções, normal p/ médias).
  2. Validação: solução EXATA por cadeia de Markov absorvente; o programa
     confere que a simulação é compatível com o valor exato (|z| < 3,5).
  3. Testes unitários do motor com dados roteirizados.

Uso:
    python3 cobras_escadas.py                     # 10.000 jogos, semente 2026
    python3 cobras_escadas.py --jogos 100000 --semente 7 --refino 200000
Dependência: numpy (só para a validação exata).
"""
from __future__ import annotations

import argparse
import math
import random
import sys
from dataclasses import dataclass

import numpy as np

# ------------------------------------------------------------------ tabuleiro
ULTIMA = 36
ESCADAS = {3: 16, 5: 7, 15: 25, 18: 20, 21: 32}
COBRAS = {12: 2, 14: 11, 17: 4, 31: 19, 35: 22}
GATILHOS = set(ESCADAS) | set(COBRAS)


def validar_tabuleiro() -> None:
    assert all(a < b for a, b in ESCADAS.items()), "escada tem que subir"
    assert all(a > b for a, b in COBRAS.items()), "cobra tem que descer"
    assert len(GATILHOS) == len(ESCADAS) + len(COBRAS), "casa com escada E cobra"
    destinos = set(ESCADAS.values()) | set(COBRAS.values())
    assert not destinos & GATILHOS, "encadeamento de atalhos não previsto"


# --------------------------------------------------------------------- regras
@dataclass(frozen=True)
class Regras:
    inicio_j2: int = 1
    p_escada: float = 1.0       # Q3: 0.5
    imunidade_j2: bool = False  # Q5


# --------------------------------------------------------------------- motor
@dataclass
class Jogador:
    casa: int
    imune: bool = False
    lances: int = 0
    cobras: int = 0
    escadas: int = 0

    def jogar(self, rng, p_escada: float) -> bool:
        """Executa um lance; devolve True se venceu (chegou ou passou de 36)."""
        self.lances += 1
        d = min(self.casa + rng.randint(1, 6), ULTIMA)
        if d in ESCADAS:
            # p == 1 não consome sorteio (mantém fluxos comparáveis)
            if p_escada >= 1 or rng.random() < p_escada:
                d = ESCADAS[d]
                self.escadas += 1
        elif d in COBRAS:
            if self.imune:
                self.imune = False          # imunidade gasta; fica na cabeça
            else:
                d = COBRAS[d]
                self.cobras += 1
        self.casa = d
        return d == ULTIMA


@dataclass(frozen=True)
class Partida:
    vencedor: int
    lances: int
    cobras_j1: int
    cobras_j2: int


def jogar_partida(regras: Regras, rng) -> Partida:
    j = (Jogador(1), Jogador(regras.inicio_j2, imune=regras.imunidade_j2))
    vez = 0
    while not j[vez].jogar(rng, regras.p_escada):
        vez ^= 1
    return Partida(vez + 1, j[0].lances + j[1].lances, j[0].cobras, j[1].cobras)


# ------------------------------------------------------------- estatística
Z95 = 1.959963984540054


@dataclass(frozen=True)
class IC:
    est: float
    inf: float
    sup: float

    @property
    def se(self) -> float:
        return (self.sup - self.inf) / (2 * Z95)


def wilson(k: int, n: int) -> IC:
    p, z2 = k / n, Z95 ** 2
    den = 1 + z2 / n
    c = (p + z2 / (2 * n)) / den
    m = Z95 * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / den
    return IC(p, c - m, c + m)


def ic_media(xs) -> IC:
    x = np.asarray(xs, float)
    m, e = x.mean(), Z95 * x.std(ddof=1) / math.sqrt(x.size)
    return IC(m, m - e, m + e)


@dataclass
class Resumo:
    n: int
    vitorias_j1: int
    lances: IC
    cobras: IC
    cobras_j1: IC
    cobras_j2: IC

    @property
    def p_j1(self) -> IC:
        return wilson(self.vitorias_j1, self.n)


def simular(regras: Regras, n: int, semente: int) -> Resumo:
    rng = random.Random(semente)
    ps = [jogar_partida(regras, rng) for _ in range(n)]
    c1 = [p.cobras_j1 for p in ps]
    c2 = [p.cobras_j2 for p in ps]
    return Resumo(n, sum(p.vencedor == 1 for p in ps),
                  ic_media([p.lances for p in ps]),
                  ic_media([a + b for a, b in zip(c1, c2)]),
                  ic_media(c1), ic_media(c2))


# =================================================== solução exata (Markov)
# Estado = casa + 37*gasta (gasta=1: sem imunidade). Para um jogador isolado:
#   f[n] = P(T = n+1),  S[n] = P(T > n),  s[n] = P(cobra no lance n+1).
NMAX = 4000                  # cauda ~ 0.81^n -> truncamento desprezível
K = 2 * (ULTIMA + 1)
idx = lambda c, gasta: c + (ULTIMA + 1) * gasta


def matriz(p_escada: float) -> tuple[np.ndarray, np.ndarray]:
    P, h = np.zeros((K, K)), np.zeros(K)
    for g in (0, 1):
        for i in range(1, ULTIMA):
            a = idx(i, g)
            for d in range(1, 7):
                j, w = min(i + d, ULTIMA), 1 / 6
                if j in COBRAS:
                    if g == 0:
                        P[a, idx(j, 1)] += w                  # usa imunidade
                    else:
                        P[a, idx(COBRAS[j], 1)] += w
                        h[a] += w
                elif j in ESCADAS:
                    P[a, idx(ESCADAS[j], g)] += w * p_escada
                    P[a, idx(j, g)] += w * (1 - p_escada)
                else:
                    P[a, idx(j, g)] += w
        P[idx(ULTIMA, g), idx(ULTIMA, g)] = 1
    return P, h


@dataclass
class Dist:
    f: np.ndarray
    S: np.ndarray
    s: np.ndarray


def jogador_exato(inicio=1, p_escada=1.0, imune=False) -> Dist:
    P, h = matriz(p_escada)
    v = np.zeros(K)
    v[idx(inicio, 0 if imune else 1)] = 1
    fim = [idx(ULTIMA, 0), idx(ULTIMA, 1)]
    S, s = np.empty(NMAX + 1), np.empty(NMAX)
    S[0] = 1 - v[fim].sum()
    for n in range(NMAX):
        s[n] = v @ h
        v = v @ P
        S[n + 1] = 1 - v[fim].sum()
    return Dist(S[:-1] - S[1:], S, s)


def exato_p_j1(a: Dist, b: Dist) -> float:
    """J1 vence no seu lance n <=> T1 = n e T2 >= n."""
    return float(np.sum(a.f * b.S[:-1]))


def exato_cobras(a: Dist, b: Dist) -> float:
    """J1 joga o lance n se T2 >= n; J2 joga o lance n se T1 > n."""
    return float(np.sum(a.s * b.S[:-1]) + np.sum(b.s * a.S[1:]))


def exato_lances(a: Dist, b: Dist) -> float:
    """J1 vence no lance n -> 2n-1 lances; J2 vence no lance n -> 2n lances."""
    n = np.arange(1, NMAX + 1)
    return float(np.sum(a.f * b.S[:-1] * (2 * n - 1)) + np.sum(b.f * a.S[1:] * 2 * n))


# ===================================================== testes do motor
class DadoRoteirizado:
    """Substitui o rng: devolve lances e sorteios pré-definidos."""

    def __init__(self, dados, sorteios=()):
        self.dados, self.sorteios = list(dados), list(sorteios)

    def randint(self, a, b):
        return self.dados.pop(0)

    def random(self):
        return self.sorteios.pop(0)


def testes() -> None:
    def lance(casa, d, p=1.0, imune=False, sorteios=()):
        j = Jogador(casa, imune=imune)
        venceu = j.jogar(DadoRoteirizado([d], sorteios), p)
        return j.casa, venceu, j.cobras, j.imune

    assert lance(1, 2)[0] == 16                          # escada 3 -> 16
    assert lance(1, 4)[0] == 7                           # escada 5 -> 7
    assert lance(10, 4)[0] == 11                         # cobra 14 -> 11
    assert lance(30, 5)[:3] == (22, False, 1)            # cobra 35 -> 22, conta 1
    assert lance(33, 6)[:2] == (36, True)                # passar de 36 vence
    assert lance(30, 6)[:2] == (36, True)                # cair exato em 36 vence
    assert lance(1, 2, .5, sorteios=[.7])[0] == 3        # escada falha: fica na base
    assert lance(1, 2, .5, sorteios=[.2])[0] == 16       # escada funciona
    assert lance(10, 2, imune=True) == (12, False, 0, False)   # imunidade usada
    assert lance(10, 2)[0] == 2                          # cobra 12 -> 2
    # J1 1->3->16 | J2 1->2 | J1 16->21->32 | J2 2->3->16 | J1 32->36
    p = jogar_partida(Regras(), DadoRoteirizado([2, 1, 5, 1, 4]))
    assert (p.vencedor, p.lances) == (1, 5), p
    print("Testes do motor: OK")


# ======================================================================= main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--jogos", type=int, default=10_000)
    ap.add_argument("--semente", type=int, default=2026)
    ap.add_argument("--refino", type=int, default=200_000,
                    help="jogos por finalista na etapa 2 da Q4")
    a = ap.parse_args()
    N, SEED = a.jogos, a.semente

    validar_tabuleiro()
    testes()
    print(f"Monte Carlo: {N} partidas/cenário, semente {SEED}\n")

    J = jogador_exato()
    tudo_ok = True

    # Critério: |z| < 3,5. O IC 95% sozinho falharia ~5% das vezes por puro
    # acaso; com 5 checagens isso viraria alarme falso frequente.
    def linha(nome: str, ic: IC, ex: float, dec: int) -> None:
        nonlocal tudo_ok
        z = (ic.est - ex) / ic.se
        ok = abs(z) < 3.5
        tudo_ok &= ok
        print(f"{nome:<34} {ic.est:8.{dec}f}  [{ic.inf:.{dec}f}, {ic.sup:.{dec}f}]"
              f"   exato {ex:8.{dec}f}  z={z:+5.2f} {'ok' if ok else 'DIVERGE'}")

    # Q1 / Q2
    base = simular(Regras(), N, SEED + 1)
    linha("Q1 P(J1 vence)", base.p_j1, exato_p_j1(J, J), 4)
    linha("Q2 cobras/partida (J1+J2)", base.cobras, exato_cobras(J, J), 3)
    print(f"     J1 {base.cobras_j1.est:.3f} | J2 {base.cobras_j2.est:.3f}")

    # Q3
    J3 = jogador_exato(p_escada=.5)
    q3 = simular(Regras(p_escada=.5), N, SEED + 3)
    linha("Q3 lances/partida (escada 50%)", q3.lances, exato_lances(J3, J3), 2)
    print(f"     ref. escada 100%: {base.lances.est:.2f} (exato {exato_lances(J, J):.2f})")

    # Q4 — duas etapas.
    #  (1) Triagem: N jogos em cada casa candidata (mesma semente).
    #  (2) Refinamento: casas compatíveis com 0,5 (|z| < 3) re-simuladas com
    #      --refino jogos. P(J1) nas casas 7 e 8 difere só ~0,009, abaixo da
    #      resolução de 10^4 jogos (IC ~ ±0,01): só a triagem erra a casa em
    #      boa parte das sementes.
    print("\nQ4 P(J1 vence) x casa inicial do J2  (etapa 1: triagem)")
    finalistas, exatos = [], {}
    for c in range(1, ULTIMA):
        if c in GATILHOS:                  # peça nunca repousa em gatilho
            continue
        ic = simular(Regras(inicio_j2=c), N, SEED + 4).p_j1
        exatos[c] = exato_p_j1(J, jogador_exato(c))
        fin = abs(ic.est - .5) < 3 * ic.se
        if fin:
            finalistas.append(c)
        if c <= 13:
            print(f"   casa {c:2d}: {ic.est:.4f} [{ic.inf:.4f}, {ic.sup:.4f}]"
                  f"  exato {exatos[c]:.4f} {'<- finalista' if fin else ''}")
    print(f"   etapa 2: {len(finalistas)} finalistas x {a.refino} jogos")
    refinado = {}
    for c in finalistas:
        ic = simular(Regras(inicio_j2=c), a.refino, SEED + 40).p_j1
        refinado[c] = ic.est
        print(f"   casa {c:2d}: {ic.est:.4f} [{ic.inf:.4f}, {ic.sup:.4f}]  exato {exatos[c]:.4f}")
    melhor_mc = min(refinado, key=lambda c: abs(refinado[c] - .5))
    melhor_ex = min(exatos, key=lambda c: abs(exatos[c] - .5))
    q4ok = melhor_mc == melhor_ex
    tudo_ok &= q4ok
    print(f"   melhor casa: MC = {melhor_mc} | exato = {melhor_ex}  {'ok' if q4ok else 'DIVERGE'}\n")

    # Q5
    q5 = simular(Regras(imunidade_j2=True), N, SEED + 5)
    linha("Q5 P(J1 vence), J2 imune", q5.p_j1, exato_p_j1(J, jogador_exato(imune=True)), 4)

    print(f"\nValidação MC x exato: {'TODAS OK' if tudo_ok else 'HÁ DIVERGÊNCIAS'}")
    return 0 if tudo_ok else 2


if __name__ == "__main__":
    sys.exit(main())
