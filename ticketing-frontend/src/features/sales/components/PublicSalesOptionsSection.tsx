import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { type FieldErrors, useForm } from "react-hook-form";
import Button from "../../../components/ui/Button";
import useAuth from "../../../hooks/useAuth";
import {
  getEventSalesOptionsRequest,
  type SalesOptionItem,
  type SalesTicketOption,
} from "../api/salesApi";
import { createReservationWithOrderRequest } from "../../checkout/api/reservationsApi";
import PublicSaleGroupCard from "./PublicSaleGroupCard";
import PublicTicketOptionCard from "./PublicTicketOptionCard";
import { ROUTES, routeTo } from "../../../routes/paths";
import PurchaseAccountModal from "../../auth/components/PurchaseAccountModal";
import { getAccountStatusRequest } from "../../auth/api/authApi";
import { calculateSelectionSubtotal } from "../utils/cascadePricing";

import styles from "./PublicSalesOptionsSection.module.css";
import { getApiErrorMessage } from "../../../api/errors";
import type { ApiSchema, EntityId } from "../../../types/api";
import type { EventSession } from "../../../types/domain";

type GuestForm = {
  full_name: string;
  email: string;
  email_confirm: string;
  phone: string;
  accept_terms: boolean;
};

type PendingPurchase = {
  payloadItems: ApiSchema<"ReservationItemCreate">[];
  customerPayload: ApiSchema<"ReservationCustomerCreate">;
};

type PublicSalesOptionsSectionProps = {
  eventId: EntityId;
  sessions?: EventSession[];
  selectedSessionId?: EntityId | null;
  onSelectSession?: (sessionId: EntityId | null) => void;
  publicRelationsCode?: string | null;
};

function formatTotal(value: string | number): string {
  return Number(value).toFixed(2);
}

function flattenTickets(items: SalesOptionItem[]): SalesTicketOption[] {
  const tickets: SalesTicketOption[] = [];

  items.forEach((item) => {
    if (item.type === "ticket_type") {
      tickets.push(item.ticket_type);
    }

    if (item.type === "sale_group") {
      item.ticket_types.forEach((ticket) => {
        tickets.push({
          ...ticket,
          sale_group_id: item.id,
          sale_group_strategy: item.strategy,
        });
      });
    }
  });

  return tickets;
}

function getTicketMaxQuantity(ticket: SalesTicketOption): number {
  return Math.max(
    0,
    Math.min(
      Number(ticket.max_selectable_quantity || 0),
      Number(ticket.max_per_purchase || ticket.max_selectable_quantity || 0)
    )
  );
}

function formatSessionDate(value: string): string {
  return new Date(value).toLocaleString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getGuestFormError(errors: FieldErrors<GuestForm>): string {
  return (
    errors.full_name?.message ||
    errors.email?.message ||
    errors.email_confirm?.message ||
    errors.phone?.message ||
    errors.accept_terms?.message ||
    ""
  );
}

function isSelectedQuantities(value: unknown): value is Record<EntityId, number> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return false;
  }

  return Object.values(value).every(
    (quantity) =>
      typeof quantity === "number" &&
      Number.isInteger(quantity) &&
      quantity >= 0
  );
}

export default function PublicSalesOptionsSection({
  eventId,
  sessions = [],
  selectedSessionId = null,
  onSelectSession,
  publicRelationsCode = null,
}: PublicSalesOptionsSectionProps) {
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const visibleSessions = useMemo(
    () =>
      sessions
        .filter((session) => ["published", "sold_out", "finished"].includes(session.status))
        .sort((a, b) => {
          const aFinished = a.status === "finished" ? 1 : 0;
          const bFinished = b.status === "finished" ? 1 : 0;
          if (aFinished !== bFinished) return aFinished - bFinished;
          return new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime();
        }),
    [sessions]
  );
  const publicSessions = useMemo(
    () => visibleSessions.filter((session) => ["published", "sold_out"].includes(session.status)),
    [visibleSessions]
  );

  const [items, setItems] = useState<SalesOptionItem[]>([]);
  const [selectedQuantities, setSelectedQuantities] = useState<Record<EntityId, number>>({});
  const {
    getValues: getGuestValues,
    register: registerGuest,
    trigger: triggerGuestValidation,
    formState: { errors: guestErrors },
  } = useForm<GuestForm>({
    mode: "onSubmit",
    reValidateMode: "onChange",
    defaultValues: {
      full_name: "",
      email: "",
      email_confirm: "",
      phone: "",
      accept_terms: false,
    },
  });
  const [loading, setLoading] = useState(true);
  const [buying, setBuying] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [pendingPurchase, setPendingPurchase] = useState<PendingPurchase | null>(null);
  const [accountPrompt, setAccountPrompt] = useState({
    open: false,
    exists: false,
    canLogin: false,
  });
  const purchaseInFlightRef = useRef(false);
  
  const hasMultipleSessions = visibleSessions.length > 1;
  const activeSessionId =
    selectedSessionId || (publicSessions.length === 1 ? publicSessions[0]?.id ?? null : null);
  const storageKey = `event_selection_${eventId}_${activeSessionId || "event"}`;

  useEffect(() => {
    const loadSalesOptions = async () => {
      try {
        setLoading(true);
        setErrorMsg("");

        const data = await getEventSalesOptionsRequest(eventId, activeSessionId);
        setItems(data.items || []);
      } catch (error) {
        console.error("Error cargando opciones de venta:", error);
        setErrorMsg("No se pudieron cargar las entradas disponibles");
      } finally {
        setLoading(false);
      }
    };

    if (eventId && publicSessions.length > 0 && (!hasMultipleSessions || activeSessionId)) {
      loadSalesOptions();
    } else {
      setLoading(false);
      setItems([]);
    }
  }, [eventId, activeSessionId, hasMultipleSessions, publicSessions.length]);

  useEffect(() => {
    const firstPublicSessionId = publicSessions[0]?.id || null;

    if (firstPublicSessionId && !publicSessions.some((session) => session.id === selectedSessionId)) {
      onSelectSession?.(firstPublicSessionId);
    } else if (!firstPublicSessionId && selectedSessionId) {
      onSelectSession?.(null);
    }
  }, [onSelectSession, publicSessions, selectedSessionId]);

  useEffect(() => {
    const savedSelection = sessionStorage.getItem(storageKey);

    if (savedSelection) {
      try {
        const parsedSelection: unknown = JSON.parse(savedSelection);
        if (!isSelectedQuantities(parsedSelection)) {
          sessionStorage.removeItem(storageKey);
          return;
        }
        setSelectedQuantities(parsedSelection);
      } catch {
        sessionStorage.removeItem(storageKey);
      }
    }
  }, [storageKey]);

  useEffect(() => {
    sessionStorage.setItem(storageKey, JSON.stringify(selectedQuantities));
  }, [storageKey, selectedQuantities]);

  const allTickets = useMemo(() => flattenTickets(items), [items]);

  const selectedTickets = useMemo(() => {
    return allTickets
      .map((ticket) => ({
        ...ticket,
        quantity: Math.min(
          selectedQuantities[ticket.id] || 0,
          getTicketMaxQuantity(ticket)
        ),
        selectionSubtotal: calculateSelectionSubtotal(
          ticket,
          Math.min(
            selectedQuantities[ticket.id] || 0,
            getTicketMaxQuantity(ticket)
          ),
          allTickets
        ),
      }))
      .filter((ticket) => ticket.quantity > 0);
  }, [allTickets, selectedQuantities]);

  const selectedGroupIds = useMemo(() => {
    return new Set<EntityId>(
      selectedTickets
        .map((ticket) => ticket.sale_group_id)
        .filter((groupId): groupId is EntityId => Boolean(groupId))
    );
  }, [selectedTickets]);

  const total = selectedTickets.reduce((sum, ticket) => {
    return sum + ticket.selectionSubtotal;
  }, 0);

  const handleChangeQuantity = (ticketId: EntityId, quantity: number) => {
    const changedTicket = allTickets.find((ticket) => ticket.id === ticketId);
    const safeQuantity = changedTicket
      ? Math.min(quantity, getTicketMaxQuantity(changedTicket))
      : quantity;

    setSelectedQuantities((prev) => {
      const next = {
        ...prev,
        [ticketId]: safeQuantity,
      };

      if (changedTicket?.sale_group_id && safeQuantity > 0) {
        allTickets.forEach((ticket) => {
          if (
            ticket.sale_group_id === changedTicket.sale_group_id &&
            ticket.id !== changedTicket.id
          ) {
            next[ticket.id] = 0;
          }
        });
      }

      return next;
    });
  };

  const createReservation = async (
    payloadItems: ApiSchema<"ReservationItemCreate">[],
    customerPayload: ApiSchema<"ReservationCustomerCreate"> | null = null
  ) => {
    try {
      setBuying(true);
      setErrorMsg("");

      const reservation = await createReservationWithOrderRequest(
        eventId,
        payloadItems,
        customerPayload,
        publicRelationsCode
      );

      sessionStorage.removeItem(storageKey);

      router.push(routeTo.checkout(reservation.order_id));
    } catch (error) {
      console.error("Error creando reserva:", error);
      setErrorMsg(
        getApiErrorMessage(
          error,
          "No se pudo iniciar la compra. Revisa la disponibilidad."
        )
      );
    } finally {
      setBuying(false);
      purchaseInFlightRef.current = false;
    }
  };

  const handleBuy = async () => {
    if (purchaseInFlightRef.current) return;
    purchaseInFlightRef.current = true;

    if (selectedTickets.length === 0) {
      alert("Selecciona al menos una entrada");
      purchaseInFlightRef.current = false;
      return;
    }

    const invalidTicket = selectedTickets.find(
      (ticket) => ticket.quantity > getTicketMaxQuantity(ticket)
    );
    if (invalidTicket) {
      setErrorMsg(
        `Solo puedes comprar hasta ${getTicketMaxQuantity(invalidTicket)} entradas de ${invalidTicket.name}`
      );
      purchaseInFlightRef.current = false;
      return;
    }

    const payloadItems = selectedTickets.map((ticket) => ({
      ticket_type_id: ticket.id,
      quantity: ticket.quantity,
    }));

    if (isAuthenticated) {
      await createReservation(payloadItems);
      return;
    }

    const isGuestFormValid = await triggerGuestValidation();
    if (!isGuestFormValid) {
      setErrorMsg("");
      purchaseInFlightRef.current = false;
      return;
    }

    const values = getGuestValues();
    const customerPayload = {
      full_name: values.full_name.trim(),
      email: values.email.trim().toLowerCase(),
      email_confirm: values.email_confirm.trim().toLowerCase(),
      phone: values.phone.trim(),
      country_code: "ES",
      accept_terms: values.accept_terms,
      accept_privacy: values.accept_terms,
    };

    try {
      setBuying(true);
      setErrorMsg("");
      const accountStatus = await getAccountStatusRequest(customerPayload.email);
      setPendingPurchase({ payloadItems, customerPayload });
      setAccountPrompt({
        open: true,
        exists: accountStatus.exists,
        canLogin: accountStatus.can_login,
      });
    } catch (error) {
      setErrorMsg(
        getApiErrorMessage(
          error,
          "No se pudo comprobar el correo. Intentalo de nuevo."
        )
      );
    } finally {
      setBuying(false);
      purchaseInFlightRef.current = false;
    }
  };

  const continueAsGuest = async () => {
    if (!pendingPurchase || purchaseInFlightRef.current) return;
    purchaseInFlightRef.current = true;
    setAccountPrompt((current) => ({ ...current, open: false }));
    await createReservation(
      pendingPurchase.payloadItems,
      pendingPurchase.customerPayload
    );
  };

  const continueAsAuthenticated = async () => {
    if (!pendingPurchase || purchaseInFlightRef.current) return;
    purchaseInFlightRef.current = true;
    setAccountPrompt((current) => ({ ...current, open: false }));
    await createReservation(pendingPurchase.payloadItems);
  };

  return (
    <section className={styles.wrapper}>
      {visibleSessions.length === 0 ? (
        <div className={styles.teaserBox}>
          <h3 className={styles.title}>Fechas en camino</h3>
          <p>
            Todavia no hay fechas publicadas, pero esto huele a planazo. Vuelve pronto:
            cuando salgan, los mas atentos llegan primero.
          </p>
        </div>
      ) : null}

      {hasMultipleSessions ? (
        <div className={styles.sessionSelector}>
          <h3 className={styles.title}>Elige fecha y lugar</h3>
          <div className={styles.sessionGrid}>
            {visibleSessions.map((session) => {
              const isSelected = selectedSessionId === session.id;
              const isFinished = session.status === "finished";

              return (
                <button
                  key={session.id}
                  className={`${styles.sessionCard} ${
                    isSelected ? styles.sessionCardSelected : ""
                  } ${isFinished ? styles.sessionCardFinished : ""}`}
                  type="button"
                  disabled={isFinished}
                  onClick={() => {
                    if (isFinished) return;
                    onSelectSession?.(session.id);
                    setSelectedQuantities({});
                  }}
                >
                  <strong>{session.location_name}</strong>
                  <span>{formatSessionDate(session.starts_at)}</span>
                  {session.location_address ? (
                    <small>{session.location_address}</small>
                  ) : null}
                  {isFinished ? <em>Finalizada</em> : null}
                </button>
              );
            })}
          </div>
        </div>
      ) : null}

      {publicSessions.length > 0 ? (
        <h3 className={styles.title}>Entradas disponibles</h3>
      ) : null}

      {hasMultipleSessions && !activeSessionId ? (
        <p>Selecciona una fecha y lugar para ver las entradas.</p>
      ) : null}

      {visibleSessions.length > 0 && publicSessions.length === 0 ? (
        <p>Todas las fechas publicadas ya han finalizado. Gracias por estar atento.</p>
      ) : null}

      {publicSessions.length > 0 && loading ? <p>Cargando entradas...</p> : null}
      {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}

      {publicSessions.length > 0 && !loading && !errorMsg && items.length === 0 ? (
        <p>No hay entradas disponibles todavía.</p>
      ) : null}

      <div className={styles.list}>
        {items.map((item) => {
          if (item.type === "ticket_type") {
            const ticket = item.ticket_type;

            return (
              <PublicTicketOptionCard
                key={ticket.id}
                ticket={ticket}
                quantity={selectedQuantities[ticket.id] || 0}
                onChangeQuantity={(quantity) =>
                  handleChangeQuantity(ticket.id, quantity)
                }
              />
            );
          }

          if (item.type === "sale_group") {
            return (
              <PublicSaleGroupCard
                key={item.id}
                group={item}
                selectedQuantities={selectedQuantities}
                selectedGroupIds={selectedGroupIds}
                onChangeQuantity={handleChangeQuantity}
              />
            );
          }

          return null;
        })}
      </div>

      {selectedTickets.length > 0 ? (
        <div className={styles.summary}>
          <h4>Resumen</h4>

          {selectedTickets.map((ticket) => (
            <div key={ticket.id} className={styles.summaryRow}>
              <span>
                {ticket.quantity} × {ticket.name}
              </span>
              <strong>
                {formatTotal(ticket.selectionSubtotal)}{" "}
                {ticket.currency}
              </strong>
            </div>
          ))}

          <div className={styles.totalRow}>
            <span>Total</span>
            <strong>{formatTotal(total)} EUR</strong>
          </div>

          {!isAuthenticated ? (
          <div className={styles.contactBox}>
            <h4>Datos de contacto</h4>
            <label className={styles.label}>
              Nombre completo
              <input
                className={styles.input}
                {...registerGuest("full_name", {
                  required: "Indica el nombre completo del comprador",
                  minLength: {
                    value: 2,
                    message: "Indica el nombre completo del comprador",
                  },
                })}
                required
              />
            </label>

            <label className={styles.label}>
              Email
              <input
                className={styles.input}
                type="email"
                {...registerGuest("email", {
                  required: "Indica un email valido para recibir las entradas",
                  pattern: {
                    value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                    message: "Indica un email valido para recibir las entradas",
                  },
                })}
                required
              />
            </label>

            <label className={styles.label}>
              Repite el email
              <input
                className={styles.input}
                type="email"
                {...registerGuest("email_confirm", {
                  required: "Repite el email para confirmar la compra",
                  validate: (value) =>
                    value.trim().toLowerCase() === getGuestValues("email").trim().toLowerCase() ||
                    "Los emails no coinciden",
                })}
                required
              />
            </label>

            <label className={styles.label}>
              Telefono
              <input
                className={styles.input}
                type="tel"
                {...registerGuest("phone", {
                  required: "Indica un telefono de contacto valido",
                  validate: (value) =>
                    value.replace(/[^\d+]/g, "").length >= 6 ||
                    "Indica un telefono de contacto valido",
                })}
                required
              />
            </label>

            <label className={styles.checkLabel}>
              <input
                type="checkbox"
                {...registerGuest("accept_terms", {
                  required: "Debes aceptar las condiciones de compra y la politica de privacidad",
                })}
              />
              <span>
                Acepto las{" "}
                <Link href={ROUTES.terms} target="_blank">
                  condiciones de compra
                </Link>{" "}
                y la{" "}
                <Link href={ROUTES.privacy} target="_blank">
                  politica de privacidad
                </Link>
                .
              </span>
            </label>

            {getGuestFormError(guestErrors) ? (
              <p className={styles.error}>{getGuestFormError(guestErrors)}</p>
            ) : null}
          </div>
          ) : null}

          <Button
            className={styles.button}
            variant="primary"
            onClick={handleBuy}
            disabled={buying}
          >
            {buying ? "Procesando..." : "Comprar"}
          </Button>
        </div>
      ) : null}

      <PurchaseAccountModal
        isOpen={accountPrompt.open}
        accountExists={accountPrompt.exists}
        accountCanLogin={accountPrompt.canLogin}
        customer={pendingPurchase?.customerPayload || {
          email: "",
          full_name: "",
          phone: "",
          country_code: "ES",
        }}
        onClose={() =>
          setAccountPrompt((current) => ({ ...current, open: false }))
        }
        onContinueGuest={continueAsGuest}
        onAuthenticated={continueAsAuthenticated}
      />
    </section>
  );
}
