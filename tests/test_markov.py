"""Propriedades da solução exata (cadeia de Markov)."""

import numpy as np
import pytest

import cobras_escadas as ce


@pytest.mark.parametrize("p_escada", [1.0, 0.5, 0.0])
def test_matriz_estocastica(p_escada):
    P, h = ce.matriz(p_escada)
    linhas = [ce.idx(c, g) for g in (0, 1) for c in range(1, ce.ULTIMA + 1)]
    np.testing.assert_allclose(P[linhas].sum(axis=1), 1.0)
    assert np.all(P >= 0) and np.all((h >= 0) & (h <= 1))


def test_distribuicao_soma_um(base):
    assert base.f.sum() == pytest.approx(1.0, abs=1e-12)
    assert base.S[-1] < 1e-12


def test_tempo_medio_bate_com_matriz_fundamental(base):
    # E[T] = soma de P(T > n) = linha da casa 1 de (I - Q)^-1
    P, _ = ce.matriz(1.0)
    est = [ce.idx(c, 1) for c in range(1, ce.ULTIMA)]
    N = np.linalg.inv(np.eye(len(est)) - P[np.ix_(est, est)])
    assert base.S[:-1].sum() == pytest.approx(N[0].sum(), rel=1e-10)
    assert N[0].sum() == pytest.approx(13.3826, abs=1e-4)


def test_vantagem_de_quem_comeca_e_metade_do_empate(base):
    # Simetria: P(J1 vence) = 1/2 + 1/2 * P(T1 = T2)
    empate = np.sum(base.f**2)
    assert ce.exato_p_j1(base, base) == pytest.approx(0.5 + 0.5 * empate, abs=1e-12)


def test_respostas_exatas(base):
    meia = ce.jogador_exato(p_escada=0.5)
    assert ce.exato_p_j1(base, base) == pytest.approx(0.52554, abs=1e-5)
    assert ce.exato_cobras(base, base) == pytest.approx(3.09366, abs=1e-5)
    assert ce.exato_lances(meia, meia) == pytest.approx(22.4933, abs=1e-4)
    assert ce.exato_p_j1(base, ce.jogador_exato(imune=True)) == pytest.approx(0.38640, abs=1e-5)


def test_casa_mais_justa_para_o_jogador_2(base):
    casas = [c for c in range(1, ce.ULTIMA) if c not in ce.GATILHOS]
    p = {c: ce.exato_p_j1(base, ce.jogador_exato(c)) for c in casas}
    assert min(p, key=lambda c: abs(p[c] - 0.5)) == 7


def test_equilibrio_fica_entre_as_casas_6_e_7(base):
    # P(J1 vence) cruza 0,5 entre começar o J2 na casa 6 e na casa 7.
    p6 = ce.exato_p_j1(base, ce.jogador_exato(6))
    p7 = ce.exato_p_j1(base, ce.jogador_exato(7))
    assert p7 < 0.5 < p6
