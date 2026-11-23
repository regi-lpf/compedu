import csv
import io
import re
import unicodedata
import uuid
from dataclasses import dataclass
from typing import Any
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
import xlrd

MAX_IMPORT_ROWS = 60
MAX_IMPORT_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class StudentImportRow:
    line_number: int
    full_name: str | None


def normalize_student_name(name: str) -> str:
    decomposed = unicodedata.normalize("NFKD", name).casefold()
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_accents.split())


def generated_school_identifier() -> str:
    return f"AUTO-{uuid.uuid4().hex}"


def _read_csv(content: bytes) -> list[list[Any]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("cp1252")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    try:
        return list(csv.reader(io.StringIO(text), dialect))
    except csv.Error as exc:
        raise ValueError("Não foi possível ler o arquivo CSV.") from exc


def _read_xlsx(content: bytes) -> list[list[Any]]:
    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except (BadZipFile, InvalidFileException, ValueError) as exc:
        raise ValueError("O arquivo XLSX é inválido ou está corrompido.") from exc
    try:
        if not workbook.worksheets:
            return []
        return [list(row) for row in workbook.worksheets[0].iter_rows(values_only=True)]
    finally:
        workbook.close()


def _read_xls(content: bytes) -> list[list[Any]]:
    try:
        workbook = xlrd.open_workbook(file_contents=content, on_demand=True)
    except xlrd.XLRDError as exc:
        raise ValueError("O arquivo XLS é inválido ou está corrompido.") from exc
    try:
        if not workbook.sheet_names():
            return []
        sheet = workbook.sheet_by_index(0)
        return [sheet.row_values(index) for index in range(sheet.nrows)]
    finally:
        workbook.release_resources()


def _name_column(header: list[Any]) -> int | None:
    accepted = {
        "nome", "nome completo", "nome do aluno", "nome completo do aluno", "nome do estudante",
        "nome completo do estudante", "aluno", "estudante", "name", "student",
    }
    for index, value in enumerate(header):
        if not isinstance(value, str):
            continue
        normalized = re.sub(r"[^a-z0-9]+", " ", normalize_student_name(value)).strip()
        tokens = set(normalized.split())
        if normalized in accepted or ("nome" in tokens and tokens.intersection({"aluno", "estudante"})):
            return index
    return None


def parse_student_import(filename: str, content: bytes) -> list[StudentImportRow]:
    if not content:
        raise ValueError("Selecione um arquivo não vazio.")
    if len(content) > MAX_IMPORT_BYTES:
        raise ValueError("O arquivo excede o limite de 2 MB.")

    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension == "csv":
        rows = _read_csv(content)
    elif extension == "xlsx":
        rows = _read_xlsx(content)
    elif extension == "xls":
        rows = _read_xls(content)
    else:
        raise ValueError("Formato não suportado. Envie um arquivo CSV, XLS ou XLSX.")

    first_data_index = 0
    name_index = 0
    if rows:
        header_index = next((index for index, row in enumerate(rows) if any(
            value is not None and str(value).strip() for value in row
        )), None)
        if header_index is not None:
            detected_column = _name_column(rows[header_index])
            if detected_column is not None:
                first_data_index = header_index + 1
                name_index = detected_column

    result: list[StudentImportRow] = []
    for row_index in range(first_data_index, len(rows)):
        values = rows[row_index]
        if not any(value is not None and str(value).strip() for value in values):
            continue
        value = values[name_index] if name_index < len(values) else None
        name = value.strip() if isinstance(value, str) else None
        if name is not None and not 2 <= len(name) <= 160:
            name = None
        result.append(StudentImportRow(row_index + 1, name))
        if len(result) > MAX_IMPORT_ROWS:
            raise ValueError("A planilha contém mais de 60 linhas de alunos. Divida a lista em arquivos menores.")
    return result
