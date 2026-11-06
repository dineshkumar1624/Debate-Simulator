export const VALID_EXTENSIONS = ['pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'webp', 'bmp'] as const;
export const MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024; // 25 MB

export function validateDocumentFile(file: File): { valid: boolean; error?: string } {
  const ext = file.name.split('.').pop()?.toLowerCase();
  if (!ext || !VALID_EXTENSIONS.includes(ext as any)) {
    return {
      valid: false,
      error: 'Unsupported file format. Please upload a PDF, DOCX, TXT document, or an image (JPG, PNG, WEBP, BMP).',
    };
  }
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return {
      valid: false,
      error: 'File size exceeds 25 MB limit for processing.',
    };
  }
  return { valid: true };
}

