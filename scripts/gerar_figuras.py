"""Gera as figuras usadas no README (salvas em figures/).

Uso:  python scripts/gerar_figuras.py
"""

import pathlib
import random
import sys

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "python"))
import cobras_escadas as ce  # noqa: E402

OUT = RAIZ / "figures"
OUT.mkdir(exist_ok=True)

AZUL, LARANJA, VERDE = "#2a78d6", "#eb6834", "#1baf7a"
TXT, TXT2, GRADE, FUNDO = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update(
    {
        "figure.dpi": 150,
        "figure.facecolor": FUNDO,
        "axes.facecolor": FUNDO,
        "axes.edgecolor": GRADE,
        "axes.labelcolor": TXT2,
        "axes.titlecolor": TXT,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.grid": True,
        "grid.color": GRADE,
        "grid.linewidth": 0.8,
        "xtick.color": TXT2,
        "ytick.color": TXT2,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
        "lines.linewidth": 2,
        "font.size": 10,
    }
)


def coord(casa):
    """Centro da casa no tabuleiro 6x6 em zigue-zague (linha 0 embaixo)."""
    lin, k = divmod(casa - 1, 6)
    col = k if lin % 2 == 0 else 5 - k
    return col + 0.5, lin + 0.5


def lances_esperados():
    """E[lances até terminar] partindo de cada casa: (I - Q)^-1 · 1."""
    P, _ = ce.matriz(1.0)
    estados = [ce.idx(c, 1) for c in range(1, ce.ULTIMA)]
    Q = P[np.ix_(estados, estados)]
    E = np.linalg.solve(np.eye(len(estados)) - Q, np.ones(len(estados)))
    return {c: E[c - 1] for c in range(1, ce.ULTIMA)} | {ce.ULTIMA: 0.0}


# ----------------------------------------------------------- 1. tabuleiro
def fig_tabuleiro():
    E = lances_esperados()
    cmap = LinearSegmentedColormap.from_list("az", ["#eef4fc", "#2a78d6"])
    vmax = max(E.values())
    fig, ax = plt.subplots(figsize=(6, 6.4))
    ax.set_xlim(0, 6)
    ax.set_ylim(0, 6)
    ax.set_aspect("equal")
    ax.grid(False)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    for c in range(1, ce.ULTIMA + 1):
        x, y = coord(c)
        gat = c in ce.ESCADAS or c in ce.COBRAS
        cor = "#f1f0ec" if gat else cmap(E[c] / vmax)
        ax.add_patch(plt.Rectangle((x - 0.5, y - 0.5), 1, 1, fc=cor, ec="white", lw=2))
        ax.text(x - 0.42, y + 0.4, c, fontsize=8, color=TXT2, va="top")
        if not gat:
            ax.text(
                x + 0.3,
                y - 0.3,
                f"{E[c]:.1f}",
                ha="center",
                va="center",
                fontsize=9,
                color=TXT if E[c] < 0.6 * vmax else "white",
                fontweight="bold",
            )
    for mapa, cor in ((ce.ESCADAS, VERDE), (ce.COBRAS, LARANJA)):
        for a, b in mapa.items():
            (x0, y0), (x1, y1) = coord(a), coord(b)
            ax.annotate(
                "",
                (x1, y1),
                (x0, y0),
                arrowprops=dict(
                    arrowstyle="-|>",
                    color=cor,
                    lw=2.4,
                    shrinkA=7,
                    shrinkB=7,
                    connectionstyle="arc3,rad=0.15",
                ),
            )
    ax.plot([], [], color=VERDE, label="escada (sobe)")
    ax.plot([], [], color=LARANJA, label="cobra (desce)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=2)
    ax.set_title("Lances esperados até o fim, partindo de cada casa", pad=10)
    fig.tight_layout()
    fig.savefig(OUT / "tabuleiro.png", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------- 2. equilíbrio (Q4)
def fig_q4():
    J = ce.jogador_exato()
    casas = [c for c in range(1, ce.ULTIMA) if c not in ce.GATILHOS]
    ex = [ce.exato_p_j1(J, ce.jogador_exato(c)) for c in casas]
    mc, err = [], []
    for c in casas:
        r = ce.simular(ce.Regras(inicio_j2=c), 10_000, 2030).p_j1
        mc.append(r.est)
        err.append(r.est - r.inf)
    melhor = casas[int(np.argmin(np.abs(np.array(ex) - 0.5)))]

    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.axhline(0.5, color=LARANJA, lw=1.2, label="jogo justo (0,5)")
    ax.plot(casas, ex, color=TXT2, lw=1.3, ls="--", label="exato (Markov)")
    ax.errorbar(
        casas,
        mc,
        yerr=err,
        fmt="o",
        ms=4.5,
        color=AZUL,
        elinewidth=1,
        capsize=2,
        label="simulação 10⁴ jogos (IC 95%)",
    )
    ax.annotate(
        f"casa {melhor}",
        (melhor, ex[casas.index(melhor)]),
        (melhor + 6, 0.47),
        fontsize=9,
        color=TXT,
        arrowprops=dict(arrowstyle="-", color=TXT2, lw=0.8),
    )
    ax.set(
        xlabel="casa inicial do jogador 2",
        ylabel="P(jogador 1 vence)",
        title="Onde o jogador 2 deve começar para o jogo ficar justo?",
    )
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "equilibrio_q4.png", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------ 3. duração da partida
def fig_duracao():
    n = np.arange(1, ce.NMAX + 1)
    curvas = {}
    for nome, p in (("escadas normais", 1.0), ("escadas a 50% (Q3)", 0.5)):
        J = ce.jogador_exato(p_escada=p)
        pmf = np.zeros(2 * ce.NMAX + 1)
        np.add.at(pmf, 2 * n - 1, J.f * J.S[:-1])
        np.add.at(pmf, 2 * n, J.f * J.S[1:])
        curvas[nome] = (pmf, ce.exato_lances(J, J))
    fig, ax = plt.subplots(figsize=(8, 3.6))
    for (nome, (pmf, media)), cor in zip(curvas.items(), (AZUL, LARANJA), strict=True):
        ax.plot(np.arange(len(pmf)), pmf, color=cor, label=f"{nome} — média {media:.2f}")
        ax.axvline(media, color=cor, lw=1, ls=":")
    ax.set(
        xlim=(0, 70),
        xlabel="lances na partida (J1 + J2)",
        ylabel="probabilidade",
        title="Distribuição exata da duração da partida",
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "duracao.png", bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------- 4. convergência do Monte Carlo
def fig_convergencia():
    exato = ce.exato_p_j1(ce.jogador_exato(), ce.jogador_exato())
    rng = random.Random(7)
    v = np.array([ce.jogar_partida(ce.Regras(), rng).vencedor == 1 for _ in range(100_000)])
    k = np.arange(1, v.size + 1)
    p = v.cumsum() / k
    e = 1.96 * np.sqrt(p * (1 - p) / k)
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.fill_between(k, p - e, p + e, color=AZUL, alpha=0.15, lw=0, label="IC 95%")
    ax.plot(k, p, color=AZUL, lw=1.4, label="estimativa acumulada")
    ax.axhline(exato, color=LARANJA, lw=1.2, label=f"exato = {exato:.4f}")
    ax.axvline(10_000, color=TXT2, lw=0.8, ls=":")
    ax.text(10_000, 0.62, " 10⁴ jogos", color=TXT2, fontsize=8)
    ax.set(
        xscale="log",
        ylim=(0.4, 0.65),
        xlabel="partidas simuladas",
        ylabel="P(jogador 1 vence)",
        title="Convergência da simulação (Q1)",
    )
    ax.legend(loc="lower right", ncol=3, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "convergencia.png", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig_tabuleiro()
    fig_q4()
    fig_duracao()
    fig_convergencia()
    print("Figuras salvas em", OUT)
