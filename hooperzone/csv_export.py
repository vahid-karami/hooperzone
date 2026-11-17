"""CSV downloads for the admin portal. Excel needs the UTF-8 BOM to show Persian text."""
import csv

from django.http import HttpResponse
from django.utils import timezone


# A cell that starts with one of these is run as a formula by Excel and LibreOffice.
FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value):
    """Text typed by customers (names, addresses, notes) must open as text, never as a formula.

    "=HYPERLINK(...)" in a shipping address would otherwise run on the computer of the staff
    member who opens the export. A leading apostrophe makes spreadsheets show the cell as text.
    """
    if isinstance(value, str) and value.startswith(FORMULA_STARTS):
        return "'" + value
    return value


def csv_response(filename, header, rows):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    stamp = timezone.localtime().strftime("%Y%m%d-%H%M")
    response["Content-Disposition"] = f'attachment; filename="{filename}-{stamp}.csv"'
    response.write("﻿")
    writer = csv.writer(response)
    writer.writerow(header)
    for row in rows:
        writer.writerow([safe_cell(cell) for cell in row])
    return response
