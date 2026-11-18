const EVENT_STATUS_LABELS = {
  not_reviewed: "No revisado",
  in_review: "En revisión",
  draft: "Aprobado",
  published: "Publicado",
  unpublished: "Despublicado",
  cancelled: "Cancelado",
  finished: "Finalizado",
  sold_out: "Agotado",
  archived: "Borrado",
  disabled: "Desactivado",
};

const TICKET_STATUS_LABELS = {
  draft: "Borrador",
  published: "Publicado",
  sold_out: "Agotado",
  archived: "Archivado",
  disabled: "Desactivado",
};

const SALE_GROUP_STATUS_LABELS = {
  draft: "Borrador",
  published: "Publicado",
  archived: "Archivado",
  disabled: "Desactivado",
};

const ORDER_STATUS_LABELS = {
  pending: "Pendiente",
  paid: "Pagado",
  cancelled: "Cancelado",
  expired: "Caducado",
  refunded: "Reembolsado",
};

const PAYMENT_STATUS_LABELS = {
  pending: "Pendiente",
  requires_action: "Requiere acción",
  requires_review: "Requiere revisión",
  paid: "Pagado",
  failed: "Fallido",
  cancelled: "Cancelado",
  refunded: "Reembolsado",
};

const USER_STATUS_LABELS = {
  active: "Activo",
  disabled: "Desactivado",
  pending: "Pendiente",
};

const AVAILABILITY_STATUS_LABELS = {
  available: "Disponible",
  low_stock: "Últimas unidades",
  sold_out: "Agotado",
  not_started: "Venta no iniciada",
  ended: "Venta finalizada",
  paused: "Pausado",
  disabled: "No disponible",
  draft: "No disponible",
};

function getLabel(labels: Readonly<Record<string, string>>, status?: string | null): string {
  if (!status) return "Sin estado";
  return labels[status] || status;
}

export function getEventStatusLabel(status?: string | null): string {
  return getLabel(EVENT_STATUS_LABELS, status);
}

export function getTicketStatusLabel(status?: string | null): string {
  return getLabel(TICKET_STATUS_LABELS, status);
}

export function getSaleGroupStatusLabel(status?: string | null): string {
  return getLabel(SALE_GROUP_STATUS_LABELS, status);
}

export function getOrderStatusLabel(status?: string | null): string {
  return getLabel(ORDER_STATUS_LABELS, status);
}

export function getPaymentStatusLabel(status?: string | null): string {
  return getLabel(PAYMENT_STATUS_LABELS, status);
}

export function getUserStatusLabel(status?: string | null): string {
  return getLabel(USER_STATUS_LABELS, status);
}

export function getAvailabilityStatusLabel(status?: string | null): string {
  return getLabel(AVAILABILITY_STATUS_LABELS, status);
}
