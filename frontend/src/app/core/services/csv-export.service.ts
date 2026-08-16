import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class CsvExportService {
  download(filename: string, headers: string[], rows: (string | number)[][]): void {
    const lines = [headers, ...rows].map(row => row.map(field => this.escapeField(field)).join(','));
    const csv = lines.join('\r\n');

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();

    URL.revokeObjectURL(url);
  }

  private escapeField(field: string | number): string {
    const value = String(field);
    if (/[",\r\n]/.test(value)) {
      return `"${value.replace(/"/g, '""')}"`;
    }
    return value;
  }
}
