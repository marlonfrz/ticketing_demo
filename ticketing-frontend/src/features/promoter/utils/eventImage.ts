export const EVENT_IMAGE_ACCEPT = "image/jpeg,image/png,image/webp";

const MAX_IMAGE_BYTES = 8 * 1024 * 1024;
const ALLOWED_IMAGE_TYPES = new Set(EVENT_IMAGE_ACCEPT.split(","));

export function validateEventImage(file: File): string | null {
  if (!ALLOWED_IMAGE_TYPES.has(file.type)) {
    return "Formato no permitido. Usa JPG, PNG o WEBP.";
  }
  if (file.size > MAX_IMAGE_BYTES) {
    const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
    return `La imagen pesa ${sizeMb} MB y el maximo es 8 MB.`;
  }
  return null;
}
