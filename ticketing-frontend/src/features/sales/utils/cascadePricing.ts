import type { SalesTicketOption } from "../api/salesApi";

const CASCADE_GROUP_STRATEGIES = new Set([
  "stock_cascade",
  "time_and_stock_cascade",
]);

export function calculateSelectionSubtotal(
  selectedTicket: SalesTicketOption,
  quantity: number,
  allTickets: SalesTicketOption[]
): number {
  const fallbackSubtotal = Number(selectedTicket.price) * quantity;

  if (
    quantity <= 0 ||
    !selectedTicket.sale_group_id ||
    !selectedTicket.sale_group_strategy ||
    !CASCADE_GROUP_STRATEGIES.has(selectedTicket.sale_group_strategy)
  ) {
    return fallbackSubtotal;
  }

  const groupTicketTypes = allTickets
    .filter(
      (ticket) => ticket.sale_group_id === selectedTicket.sale_group_id
    )
    .sort(
      (first, second) =>
        (first.sale_order ?? Number.MAX_SAFE_INTEGER) -
        (second.sale_order ?? Number.MAX_SAFE_INTEGER)
    );
  const startIndex = groupTicketTypes.findIndex(
    (ticket) => ticket.id === selectedTicket.id
  );

  if (startIndex < 0) return fallbackSubtotal;

  let remaining = quantity;
  let subtotal = 0;

  for (const ticket of groupTicketTypes.slice(startIndex)) {
    const availableQuantity = Math.max(
      0,
      Number(ticket.available_quantity || 0)
    );
    const allocatedQuantity = Math.min(remaining, availableQuantity);

    subtotal += allocatedQuantity * Number(ticket.price);
    remaining -= allocatedQuantity;

    if (remaining === 0) return subtotal;
  }

  return fallbackSubtotal;
}
