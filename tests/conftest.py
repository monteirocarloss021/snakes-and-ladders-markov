import pytest

import cobras_escadas as ce


@pytest.fixture(scope="session")
def base():
    """Distribuição exata de um jogador nas regras originais."""
    return ce.jogador_exato()
