"""Regras do jogo verificadas com dados roteirizados (sem aleatoriedade)."""

import pytest

import cobras_escadas as ce


def lance(casa, dado, p_escada=1.0, imune=False, sorteios=()):
    j = ce.Jogador(casa, imune=imune)
    venceu = j.jogar(ce.DadoRoteirizado([dado], sorteios), p_escada)
    return j, venceu


@pytest.mark.parametrize(("base", "topo"), ce.ESCADAS.items())
def test_toda_escada_sobe(base, topo):
    j, _ = lance(base - 1, 1)
    assert j.casa == topo and j.escadas == 1


@pytest.mark.parametrize(("cabeca", "rabo"), ce.COBRAS.items())
def test_toda_cobra_desce_e_e_contada(cabeca, rabo):
    j, _ = lance(cabeca - 1, 1)
    assert j.casa == rabo and j.cobras == 1


@pytest.mark.parametrize(("casa", "dado"), [(30, 6), (33, 6), (34, 5), (35, 1)])
def test_chegar_ou_passar_da_ultima_casa_vence(casa, dado):
    j, venceu = lance(casa, dado)
    assert venceu and j.casa == ce.ULTIMA


def test_escada_que_falha_mantem_na_base():
    j, _ = lance(1, 2, p_escada=0.5, sorteios=[0.7])
    assert j.casa == 3 and j.escadas == 0


def test_escada_que_funciona_com_p_parcial():
    j, _ = lance(1, 2, p_escada=0.5, sorteios=[0.2])
    assert j.casa == 16


def test_imunidade_vale_so_para_a_primeira_cobra():
    j = ce.Jogador(10, imune=True)
    dado = ce.DadoRoteirizado([2, 2])
    j.jogar(dado, 1.0)  # cai na 12, imune: fica na cabeça
    assert (j.casa, j.cobras, j.imune) == (12, 0, False)
    j.casa = 10
    j.jogar(dado, 1.0)  # cai na 12 de novo: agora desce
    assert (j.casa, j.cobras) == (2, 1)


def test_partida_roteirizada_alterna_jogadores():
    # J1 1->3->16 | J2 1->2 | J1 16->21->32 | J2 2->3->16 | J1 32->36
    p = ce.jogar_partida(ce.Regras(), ce.DadoRoteirizado([2, 1, 5, 1, 4]))
    assert (p.vencedor, p.lances) == (1, 5)


def test_tabuleiro_consistente():
    ce.validar_tabuleiro()
