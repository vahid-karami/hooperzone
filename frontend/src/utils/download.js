import apiClient from '../api/client';

// Downloads an authenticated file (CSV exports) by fetching it with the JWT and saving the blob.
export async function downloadFile(url, params, fallbackName) {
  const res = await apiClient.get(url, { params, responseType: 'blob' });
  const disposition = res.headers['content-disposition'] || '';
  const name = /filename="?([^"]+)"?/.exec(disposition)?.[1] || fallbackName;
  const href = URL.createObjectURL(res.data);
  const link = document.createElement('a');
  link.href = href;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(href), 1000);
}
