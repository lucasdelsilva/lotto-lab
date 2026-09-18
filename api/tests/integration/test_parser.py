"""Testes do parser das planilhas da Caixa. Nao tocam no banco."""

from __future__ import annotations

import io
import re
import zipfile
from datetime import date
from typing import Any

import pytest
from openpyxl import Workbook

from app.core.errors import ImportValidationError, ValidationError
from app.domain.enums import Modality
from app.infrastructure.parsers.caixa_xlsx import (
    ensure_valid,
    normalize_header,
    parse_file,
)


def build_xlsx(header: list[str], rows: list[list[Any]], title_row: bool = False) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    if title_row:
        sheet.append(["Resultados oficiais"])
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def build_xlsx_com_dimensao_mentirosa(header: list[str], rows: list[list[Any]]) -> bytes:
    """Reproduz o arquivo oficial da Caixa, que declara a aba como uma unica celula.

    No modo read_only o openpyxl confia nessa declaracao e para no cabecalho, o que fazia
    uma planilha com milhares de concursos chegar ao parser como se estivesse vazia.
    """
    original = build_xlsx(header, rows)
    entrada = io.BytesIO(original)
    saida = io.BytesIO()
    with zipfile.ZipFile(entrada) as origem, zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as destino:
        for item in origem.infolist():
            conteudo = origem.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                conteudo = re.sub(rb'<dimension ref="[^"]*"/>', b'<dimension ref="A1"/>', conteudo)
            destino.writestr(item, conteudo)
    return saida.getvalue()


MEGA_HEADER = ["Concurso", "Data do Sorteio", "Bola1", "Bola2", "Bola3", "Bola4", "Bola5", "Bola6"]
MEGA_ROWS = [
    [1, "11/03/1996", 4, 5, 30, 33, 41, 52],
    [2, "18/03/1996", 9, 37, 39, 41, 43, 49],
    [3, "25/03/1996", 10, 11, 29, 30, 36, 47],
]


class TestNormalizacaoDeCabecalho:
    def test_remove_acento_espaco_e_caixa(self) -> None:
        assert normalize_header("Data do Sorteio") == "datadosorteio"
        assert normalize_header("  Mês da Sorte ") == "mesdasorte"
        assert normalize_header("Bola 1") == "bola1"
        assert normalize_header(None) == ""

    def test_desfaz_entidade_html(self) -> None:
        # A planilha oficial do Dia de Sorte grava o mes assim.
        assert normalize_header("Mar&ccedil;o") == "marco"
        assert normalize_header("Mar&ccedil;o") == normalize_header("Março")


class TestPlanilhaOficialDaCaixa:
    def test_dimensao_declarada_como_uma_celula_ainda_le_todas_as_linhas(self) -> None:
        content = build_xlsx_com_dimensao_mentirosa(MEGA_HEADER, MEGA_ROWS)
        result = parse_file(Modality.MEGA_SENA, "mega.xlsx", content)

        assert result.is_valid
        assert len(result.draws) == 3
        assert result.last_contest == 3

    def test_mes_da_sorte_com_entidade_html(self) -> None:
        header = ["Concurso", "Data Sorteio", *[f"Bola{i}" for i in range(1, 8)], "Mês da Sorte"]
        rows = [[1, "16/03/2018", 3, 7, 11, 17, 21, 25, 31, "Mar&ccedil;o"]]
        result = parse_file(Modality.DIA_DE_SORTE, "dds.xlsx", build_xlsx(header, rows))

        assert result.is_valid
        assert result.draws[0].extras == {"month": 3}

    def test_colunas_extras_de_premiacao_sao_ignoradas(self) -> None:
        header = [
            *MEGA_HEADER,
            "Ganhadores 6 acertos",
            "Cidade / UF",
            "Rateio 6 acertos",
            "Ganhadores 5 acertos",
        ]
        rows = [[*MEGA_ROWS[0], 0, "", "0,00", 55]]
        result = parse_file(Modality.MEGA_SENA, "mega.xlsx", build_xlsx(header, rows))

        assert result.is_valid
        assert result.draws[0].numbers == (4, 5, 30, 33, 41, 52)


class TestMegaSena:
    def test_arquivo_valido(self) -> None:
        result = parse_file(Modality.MEGA_SENA, "mega.xlsx", build_xlsx(MEGA_HEADER, MEGA_ROWS))

        assert result.is_valid
        assert len(result.draws) == 3
        assert result.first_contest == 1
        assert result.last_contest == 3
        assert result.first_drawn_at == date(1996, 3, 11)
        assert result.draws[0].numbers == (4, 5, 30, 33, 41, 52)
        assert len(result.file_hash) == 64

    def test_dezenas_ficam_ordenadas(self) -> None:
        rows = [[1, "11/03/1996", 52, 41, 33, 30, 5, 4]]
        result = parse_file(Modality.MEGA_SENA, "mega.xlsx", build_xlsx(MEGA_HEADER, rows))

        assert result.draws[0].numbers == (4, 5, 30, 33, 41, 52)

    def test_cabecalho_abaixo_de_uma_linha_de_titulo(self) -> None:
        content = build_xlsx(MEGA_HEADER, MEGA_ROWS, title_row=True)
        result = parse_file(Modality.MEGA_SENA, "mega.xlsx", content)

        assert result.is_valid
        assert len(result.draws) == 3

    def test_dezena_fora_do_universo(self) -> None:
        rows = [*MEGA_ROWS, [4, "01/04/1996", 4, 5, 30, 33, 41, 61]]
        result = parse_file(Modality.MEGA_SENA, "mega.xlsx", build_xlsx(MEGA_HEADER, rows))

        assert not result.is_valid
        assert len(result.draws) == 3  # as linhas validas continuam separadas
        assert "fora do universo" in result.errors[0].message
        assert result.errors[0].value == "61"

    def test_concurso_duplicado(self) -> None:
        rows = [*MEGA_ROWS, [2, "01/04/1996", 1, 2, 3, 4, 5, 6]]
        result = parse_file(Modality.MEGA_SENA, "mega.xlsx", build_xlsx(MEGA_HEADER, rows))

        assert not result.is_valid
        assert "duplicado" in result.errors[0].message

    def test_dezenas_repetidas_na_mesma_linha(self) -> None:
        rows = [[1, "11/03/1996", 4, 4, 30, 33, 41, 52]]
        result = parse_file(Modality.MEGA_SENA, "mega.xlsx", build_xlsx(MEGA_HEADER, rows))

        assert not result.is_valid
        assert "repetidas" in result.errors[0].message

    def test_data_invalida(self) -> None:
        rows = [[1, "31/02/1996", 4, 5, 30, 33, 41, 52]]
        result = parse_file(Modality.MEGA_SENA, "mega.xlsx", build_xlsx(MEGA_HEADER, rows))

        assert not result.is_valid
        assert result.errors[0].field == "data"

    def test_quantidade_de_dezenas_errada(self) -> None:
        """Contagem diferente da modalidade barra o arquivo inteiro, nao linha a linha.

        Cinco colunas com prefixo bola sao o formato da Quina, entao a recusa vem da trava
        de modalidade e o parser nem chega a ler as linhas.
        """
        header = MEGA_HEADER[:-1]
        rows = [[1, "11/03/1996", 4, 5, 30, 33, 41]]

        with pytest.raises(ImportValidationError) as excecao:
            parse_file(Modality.MEGA_SENA, "mega.xlsx", build_xlsx(header, rows))

        assert "5 colunas" in str(excecao.value)

    def test_colunas_de_dezenas_irreconheciveis(self) -> None:
        """Sem nenhuma coluna de dezena reconhecida o erro continua sendo por linha."""
        header = ["Concurso", "Data do Sorteio", "X1", "X2"]
        rows = [[1, "11/03/1996", 4, 5]]
        result = parse_file(Modality.MEGA_SENA, "mega.xlsx", build_xlsx(header, rows))

        assert not result.is_valid
        assert result.errors[0].field == "dezenas"


class TestLotofacil:
    def test_quinze_dezenas(self) -> None:
        header = ["Concurso", "Data Sorteio", *[f"Bola{i}" for i in range(1, 16)]]
        rows = [[1, "29/09/2003", *range(1, 16)]]
        result = parse_file(Modality.LOTOFACIL, "lotofacil.xlsx", build_xlsx(header, rows))

        assert result.is_valid
        assert result.draws[0].numbers == tuple(range(1, 16))

    def test_dezena_acima_de_vinte_e_cinco(self) -> None:
        header = ["Concurso", "Data Sorteio", *[f"Bola{i}" for i in range(1, 16)]]
        rows = [[1, "29/09/2003", *range(12, 27)]]
        result = parse_file(Modality.LOTOFACIL, "lotofacil.xlsx", build_xlsx(header, rows))

        assert not result.is_valid


class TestDiaDeSorte:
    def test_mes_da_sorte_por_nome(self) -> None:
        header = ["Concurso", "Data Sorteio", *[f"Bola{i}" for i in range(1, 8)], "Mês da Sorte"]
        rows = [[1, "16/03/2018", 3, 7, 11, 17, 21, 25, 31, "setembro"]]
        result = parse_file(Modality.DIA_DE_SORTE, "dds.xlsx", build_xlsx(header, rows))

        assert result.is_valid
        assert result.draws[0].extras == {"month": 9}

    def test_mes_da_sorte_por_numero(self) -> None:
        header = ["Concurso", "Data Sorteio", *[f"Bola{i}" for i in range(1, 8)], "Mes de Sorte"]
        rows = [[1, "16/03/2018", 3, 7, 11, 17, 21, 25, 31, 12]]
        result = parse_file(Modality.DIA_DE_SORTE, "dds.xlsx", build_xlsx(header, rows))

        assert result.draws[0].extras == {"month": 12}

    def test_mes_ausente_invalida_a_linha(self) -> None:
        header = ["Concurso", "Data Sorteio", *[f"Bola{i}" for i in range(1, 8)], "Mês da Sorte"]
        rows = [[1, "16/03/2018", 3, 7, 11, 17, 21, 25, 31, None]]
        result = parse_file(Modality.DIA_DE_SORTE, "dds.xlsx", build_xlsx(header, rows))

        assert not result.is_valid
        assert result.errors[0].field == "extras"


class TestSuperSete:
    def test_colunas_mantem_a_ordem(self) -> None:
        header = ["Concurso", "Data do Sorteio", *[f"Coluna{i}" for i in range(1, 8)]]
        rows = [[1, "02/10/2020", 5, 3, 0, 9, 1, 1, 7]]
        result = parse_file(Modality.SUPER_SETE, "supersete.xlsx", build_xlsx(header, rows))

        assert result.is_valid
        # A ordem das colunas importa, entao o parser nao ordena.
        assert result.draws[0].numbers == (5, 3, 0, 9, 1, 1, 7)
        assert result.draws[0].extras == {"columns": [5, 3, 0, 9, 1, 1, 7]}

    def test_digito_repetido_entre_colunas_e_valido(self) -> None:
        header = ["Concurso", "Data do Sorteio", *[f"Coluna{i}" for i in range(1, 8)]]
        rows = [[1, "02/10/2020", 9, 9, 9, 9, 9, 9, 9]]
        result = parse_file(Modality.SUPER_SETE, "supersete.xlsx", build_xlsx(header, rows))

        assert result.is_valid

    def test_digito_fora_do_intervalo(self) -> None:
        header = ["Concurso", "Data do Sorteio", *[f"Coluna{i}" for i in range(1, 8)]]
        rows = [[1, "02/10/2020", 5, 3, 0, 10, 1, 1, 7]]
        result = parse_file(Modality.SUPER_SETE, "supersete.xlsx", build_xlsx(header, rows))

        assert not result.is_valid


class TestCsv:
    def test_csv_com_ponto_e_virgula(self) -> None:
        linhas = ["Concurso;Data Sorteio;Bola1;Bola2;Bola3;Bola4;Bola5;Bola6"]
        linhas += ["1;11/03/1996;04;05;30;33;41;52", "2;18/03/1996;09;37;39;41;43;49"]
        content = "\n".join(linhas).encode("utf-8")
        result = parse_file(Modality.MEGA_SENA, "mega.csv", content)

        assert result.is_valid
        assert result.draws[0].numbers == (4, 5, 30, 33, 41, 52)

    def test_csv_com_virgula(self) -> None:
        linhas = ["Concurso,Data Sorteio,Bola1,Bola2,Bola3,Bola4,Bola5,Bola6"]
        linhas += ["1,11/03/1996,4,5,30,33,41,52", "2,18/03/1996,9,37,39,41,43,49"]
        content = "\n".join(linhas).encode("utf-8")
        result = parse_file(Modality.MEGA_SENA, "mega.csv", content)

        assert result.is_valid
        assert len(result.draws) == 2


class TestFormatoESaida:
    def test_formato_nao_suportado(self) -> None:
        with pytest.raises(ValidationError):
            parse_file(Modality.MEGA_SENA, "mega.pdf", b"qualquer coisa")

    def test_sem_cabecalho_de_concurso(self) -> None:
        with pytest.raises(ValidationError):
            parse_file(Modality.MEGA_SENA, "mega.xlsx", build_xlsx(["A", "B"], [[1, 2]]))

    def test_ensure_valid_lanca_com_lista_de_erros(self) -> None:
        rows = [[1, "11/03/1996", 4, 5, 30, 33, 41, 61]]
        result = parse_file(Modality.MEGA_SENA, "mega.xlsx", build_xlsx(MEGA_HEADER, rows))

        with pytest.raises(ImportValidationError) as exc:
            ensure_valid(result)

        assert exc.value.status_code == 422
        assert exc.value.errors
        assert exc.value.errors[0]["row"] == 2  # cabecalho na linha 1, dados a partir da 2

    def test_ensure_valid_recusa_arquivo_sem_concursos(self) -> None:
        result = parse_file(Modality.MEGA_SENA, "mega.xlsx", build_xlsx(MEGA_HEADER, []))

        with pytest.raises(ImportValidationError):
            ensure_valid(result)

    def test_hash_muda_com_o_conteudo(self) -> None:
        primeiro = parse_file(Modality.MEGA_SENA, "a.xlsx", build_xlsx(MEGA_HEADER, MEGA_ROWS))
        segundo = parse_file(
            Modality.MEGA_SENA, "b.xlsx", build_xlsx(MEGA_HEADER, MEGA_ROWS[:2])
        )

        assert primeiro.file_hash != segundo.file_hash


DIA_HEADER = [
    "Concurso", "Data Sorteio",
    "Bola1", "Bola2", "Bola3", "Bola4", "Bola5", "Bola6", "Bola7",
    "Mes da Sorte",
]
DIA_ROWS = [[1, "16/04/2018", 2, 5, 11, 17, 23, 28, 31, "Janeiro"]]


class TestTravaDeModalidade:
    """A planilha de uma modalidade nao pode entrar em outra.

    O caso que motivou a trava: a planilha do Dia de Sorte importada na Mega-Sena passava
    batido. Bola1 a Bola6 existem nas duas, o parser truncava a setima coluna e as dezenas
    de 1 a 31 cabem no universo de 1 a 60, entao nenhuma validacao de linha reclamava.
    """

    def test_dia_de_sorte_na_mega_sena_e_recusado(self) -> None:
        with pytest.raises(ImportValidationError) as excecao:
            parse_file(Modality.MEGA_SENA, "planilha.xlsx", build_xlsx(DIA_HEADER, DIA_ROWS))

        mensagem = str(excecao.value)
        assert "7 colunas" in mensagem
        assert "Dia de Sorte" in mensagem

    def test_lotofacil_na_mega_sena_e_recusada(self) -> None:
        header = ["Concurso", "Data Sorteio", *[f"Bola{i}" for i in range(1, 16)]]
        rows = [[1, "29/09/2003", *range(1, 16)]]

        with pytest.raises(ImportValidationError) as excecao:
            parse_file(Modality.MEGA_SENA, "planilha.xlsx", build_xlsx(header, rows))

        assert "Lotofacil" in str(excecao.value)

    def test_mega_sena_na_quina_e_recusada(self) -> None:
        with pytest.raises(ImportValidationError) as excecao:
            parse_file(Modality.QUINA, "planilha.xlsx", build_xlsx(MEGA_HEADER, MEGA_ROWS))

        assert "Mega-Sena" in str(excecao.value)

    def test_nome_do_arquivo_de_outra_modalidade_e_recusado(self) -> None:
        """O nome oficial da Caixa tambem barra, mesmo com a estrutura batendo."""
        with pytest.raises(ImportValidationError) as excecao:
            parse_file(Modality.MEGA_SENA, "Dia de Sorte.xlsx", build_xlsx(MEGA_HEADER, MEGA_ROWS))

        assert "Dia de Sorte" in str(excecao.value)

    def test_nome_com_sufixo_de_download_ainda_e_reconhecido(self) -> None:
        with pytest.raises(ImportValidationError):
            parse_file(Modality.MEGA_SENA, "Lotofácil (2).xlsx", build_xlsx(MEGA_HEADER, MEGA_ROWS))

    def test_nome_neutro_nao_barra(self) -> None:
        """Arquivo renomeado nao acusa modalidade nenhuma e segue pela estrutura."""
        result = parse_file(Modality.MEGA_SENA, "resultados.xlsx", build_xlsx(MEGA_HEADER, MEGA_ROWS))

        assert result.is_valid
        assert len(result.draws) == 3

    def test_nome_da_propria_modalidade_passa(self) -> None:
        result = parse_file(Modality.MEGA_SENA, "Mega-Sena.xlsx", build_xlsx(MEGA_HEADER, MEGA_ROWS))

        assert result.is_valid

    def test_cada_modalidade_aceita_a_propria_planilha(self) -> None:
        dia = parse_file(Modality.DIA_DE_SORTE, "Dia de Sorte.xlsx", build_xlsx(DIA_HEADER, DIA_ROWS))

        assert dia.is_valid
        assert dia.draws[0].extras["month"] == 1
