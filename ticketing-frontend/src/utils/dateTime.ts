const dateTimeFormatter = new Intl.DateTimeFormat("es-ES", {
  dateStyle: "short",
  timeStyle: "medium",
  timeZone: "Atlantic/Canary",
});

const eventDateTimeFormatter = new Intl.DateTimeFormat("es-ES", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "Atlantic/Canary",
});

export function formatDateTime(value: string | number | Date): string {
  return dateTimeFormatter.format(new Date(value));
}

export function formatEventDateTime(value: string | number | Date): string {
  return eventDateTimeFormatter.format(new Date(value));
}
