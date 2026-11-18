import type { Order } from "../../../types/domain";

function normalizeSearch(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLocaleLowerCase("es")
    .trim();
}

export function getOrderEventTitle(order: Order): string {
  return order.tickets[0]?.event?.title || "Evento";
}

export function matchesTicketSearch(order: Order, search: string): boolean {
  const query = normalizeSearch(search);
  if (!query) return true;

  const searchableValues = [
    getOrderEventTitle(order),
    order.id,
    order.id.slice(0, 8),
    ...order.tickets.map((ticket) => ticket.ticket_code),
  ];

  return searchableValues.some((value) => normalizeSearch(value).includes(query));
}
