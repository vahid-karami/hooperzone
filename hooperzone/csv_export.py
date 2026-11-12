"""CSV downloads for the admin portal. Excel needs the UTF-8 BOM to show Persian text."""
import csv

from django.http import HttpResponse
from django.utils import timezone


def csv_response(filename, header, rows):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    stamp = timezone.localtime().strftime("%Y%m%d-%H%M")
    response["Content-Disposition"] = f'attachment; filename="{filename}-{stamp}.csv"'
    response.write("﻿")
    writer = csv.writer(response)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    return response
