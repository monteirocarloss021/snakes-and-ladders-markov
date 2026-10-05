"""A simulação precisa concordar com a solução exata."""

import pytest

import cobras_escadas as ce

N = 4_000


def z(ic, exato):
    return (ic.est - exato) / ic.se


def test_reprodutivel_com_mesma_semente():
    a = ce.simular(ce.Regras(), 500, semente=42)
    b = ce.simular(ce.Regras(), 500, semente=42)
    assert a.vitorias_j1 == b.vitorias_j1 and a.lances == b.lances


@pytest.mark.parametrize(
    ("regras", "dist_j2"),
    [
        (ce.Regras(), {}),
        (ce.Regras(inicio_j2=7), {"inicio": 7}),
        (ce.Regras(imunidade_j2=True), {"imune": True}),
    ],
)
def test_p_j1_bate_com_exato(base, regras, dist_j2):
    ic = ce.simular(regras, N, semente=1).p_j1
    assert abs(z(ic, ce.exato_p_j1(base, ce.jogador_exato(**dist_j2)))) < 3.5


def test_cobras_bate_com_exato(base):
    ic = ce.simular(ce.Regras(), N, semente=2).cobras
    assert abs(z(ic, ce.exato_cobras(base, base))) < 3.5


def test_lances_com_escada_50_bate_com_exato():
    meia = ce.jogador_exato(p_escada=0.5)
    ic = ce.simular(ce.Regras(p_escada=0.5), N, semente=3).lances
    assert abs(z(ic, ce.exato_lances(meia, meia))) < 3.5


@pytest.mark.slow
def test_versao_simples_concorda_com_a_completa():
    import cobras_escadas_simples as simples

    v, _, _ = simples.simular(5, n=N)
    m, e = simples.media_ic(v == 0)
    base = ce.jogador_exato()
    assert abs(m - ce.exato_p_j1(base, base)) < 3.5 * e / 1.96
