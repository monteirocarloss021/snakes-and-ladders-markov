"""Testes do código de Cobras e Escadas."""
import numpy as np
import pytest

import cobras_escadas as ce


class DadoFixo:
    """Faz o papel do gerador aleatório, mas devolve valores escolhidos."""

    def __init__(self, dados, sorteios=()):
        self.dados = list(dados)
        self.sorteios = list(sorteios)

    def randint(self, a, b):
        return self.dados.pop(0)

    def random(self):
        return self.sorteios.pop(0) if self.sorteios else 0.0


# ----------------------------------------------------------------- regras
def test_partida_roteirizada():
    # J1: 1 -> 3 (escada) -> 16 | J2: 1 -> 2 | J1: 16 -> 21 (escada) -> 32
    # J2: 2 -> 3 (escada) -> 16 | J1: 32 -> 36, vence
    vencedor, lances, cobras = ce.jogar_partida(DadoFixo([2, 1, 5, 1, 4]))
    assert (vencedor, lances, cobras) == (0, 5, 0)


def test_cobra_desce_e_e_contada():
    # J2 começa na 10. J1: 1 -> 3 (escada) -> 16 | J2: 10 -> 12 (cobra) -> 2
    # J1: 16 -> 21 (escada) -> 32 | J2: 2 -> 3 (escada) -> 16 | J1: 32 -> 36
    assert ce.jogar_partida(DadoFixo([2, 2, 5, 1, 4]), inicio_j2=10) == (0, 5, 1)


def test_imunidade_evita_a_primeira_cobra():
    # Mesmos dados, mas o J2 é imune: fica na 12, depois anda para a 13
    resultado = ce.jogar_partida(DadoFixo([2, 2, 5, 1, 4]), inicio_j2=10, j2_imune=True)
    assert resultado == (0, 5, 0)


def test_escada_que_funciona():
    dado = DadoFixo([2, 1, 5, 1, 4], sorteios=[0.1, 0.0])
    assert ce.jogar_partida(dado, p_escada=0.5) == (0, 5, 0)


def test_escada_que_falha():
    # Sorteio 0,9 >= 0,5: a escada da 3 falha e o J1 fica na 3.
    # J1: 3 | J2: 2 | J1: 8 | J2: 3 -> 16 | J1: 12 -> 2 (cobra) | J2: 22
    # J1: 8 | J2: 28 | J1: 14 -> 11 (cobra) | J2: 34 | J1: 17 -> 4 (cobra) | J2: 36
    dado = DadoFixo([2, 1, 5, 1, 4] + [6] * 7, sorteios=[0.9, 0.0])
    assert ce.jogar_partida(dado, p_escada=0.5) == (1, 12, 3)


def test_passar_da_ultima_casa_vence():
    # J2 começa na 33 e tira 6: passaria para 39, mas conta como chegar na 36
    assert ce.jogar_partida(DadoFixo([1, 6]), inicio_j2=33) == (1, 2, 0)


def test_simulacao_reprodutivel():
    a = ce.simular(42, n=300)
    b = ce.simular(42, n=300)
    assert all(np.array_equal(x, y) for x, y in zip(a, b))


# --------------------------------------------------------- cadeia de Markov
@pytest.fixture(scope="module")
def base():
    return ce.distribuicao()


def test_distribuicao_soma_um(base):
    f, S, _ = base
    assert f.sum() == pytest.approx(1.0, abs=1e-12)
    assert S[-1] < 1e-12


def test_tempo_medio(base):
    _, S, _ = base
    assert S[:-1].sum() == pytest.approx(13.3826, abs=1e-4)


def test_vantagem_de_quem_comeca(base):
    # P(J1 vence) = 1/2 + 1/2 * P(T1 = T2)
    f = base[0]
    assert ce.exato_p_j1(base, base) == pytest.approx(0.5 + 0.5 * np.sum(f**2), abs=1e-12)


def test_respostas_exatas(base):
    meia = ce.distribuicao(p_escada=0.5)
    assert ce.exato_p_j1(base, base) == pytest.approx(0.5255, abs=1e-4)
    assert ce.exato_cobras(base, base) == pytest.approx(3.0937, abs=1e-4)
    assert ce.exato_lances(meia, meia) == pytest.approx(22.4933, abs=1e-4)
    assert ce.exato_p_j1(base, ce.distribuicao(imune=True)) == pytest.approx(0.3864, abs=1e-4)


def test_melhor_casa_para_o_jogador_2(base):
    casas = [c for c in range(1, ce.ULTIMA) if c not in ce.ESCADAS and c not in ce.COBRAS]
    p = {c: ce.exato_p_j1(base, ce.distribuicao(inicio=c)) for c in casas}
    assert min(p, key=lambda c: abs(p[c] - 0.5)) == 7


# ------------------------------------------------- simulação x valor exato
def test_simulacao_concorda_com_exato(base):
    venc, _, cobras = ce.simular(1, n=5000)
    m, e = ce.media_ic(venc == 0)
    assert abs(m - ce.exato_p_j1(base, base)) < 3.5 * e / 1.96
    m, e = ce.media_ic(cobras)
    assert abs(m - ce.exato_cobras(base, base)) < 3.5 * e / 1.96
