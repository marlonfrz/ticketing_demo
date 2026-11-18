import { type SubmitEvent, useCallback, useEffect, useMemo, useState } from "react";
import { getTicketTypesByEventRequest } from "../../ticketTypes/api/ticketTypesApi";
import {
  downloadComplimentaryTicketsPdfRequest,
  generateComplimentaryTicketsRequest,
  getComplimentaryTicketsSummaryRequest,
} from "../api/complimentaryTicketsApi";
import ConfirmDialog from "../../../components/ui/ConfirmDialog";
import Button from "../../../components/ui/Button";

import styles from "./ComplimentaryTicketsSection.module.css";
import { getApiErrorMessage } from "../../../api/errors";
import type { ApiSchema, EntityId } from "../../../types/api";
import type { EventSession, ManagedEvent, TicketType } from "../../../types/domain";

function formatDate(value?: string | null): string {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function getAvailableStock(ticketType: TicketType): number {
  return Math.max(0, Number(ticketType.stock || 0) - Number(ticketType.sold_count || 0));
}

export default function ComplimentaryTicketsSection({
  event,
  selectedSession,
  canManage,
  onReloadEvent,
}: {
  event: ManagedEvent;
  selectedSession: EventSession;
  canManage: boolean;
  onReloadEvent?: () => void | Promise<void>;
}) {
  const [ticketTypes, setTicketTypes] = useState<TicketType[]>([]);
  const [summary, setSummary] = useState<ApiSchema<"ComplimentaryTicketSummaryResponse"> | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [pendingSubmit, setPendingSubmit] = useState<{ quantity: number } | null>(null);
  const [form, setForm] = useState({
    ticket_type_id: "",
    quantity: 1,
    recipient_name: "",
    note: "",
  });

  const loadData = useCallback(async () => {
    if (!event?.id || !selectedSession?.id || !canManage) return;

    try {
      setLoading(true);
      setErrorMsg("");

      const [ticketTypesData, summaryData] = await Promise.all([
        getTicketTypesByEventRequest(event.id, selectedSession.id),
        getComplimentaryTicketsSummaryRequest(event.id, selectedSession.id),
      ]);

      const availableTypes = ticketTypesData.filter((ticketType) =>
        ["published", "sold_out"].includes(ticketType.status) &&
        ["published", "sold_out"].includes(selectedSession.status)
      );

      setTicketTypes(availableTypes);
      setSummary(summaryData);
      setForm((current) => ({
        ...current,
        ticket_type_id:
          availableTypes.some((ticketType) => ticketType.id === current.ticket_type_id)
            ? current.ticket_type_id
            : availableTypes[0]?.id || "",
      }));
    } catch (error) {
      console.error("Error cargando invitaciones:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudo cargar la informacion de invitaciones"));
    } finally {
      setLoading(false);
    }
  }, [canManage, event?.id, selectedSession?.id, selectedSession?.status]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const selectedTicketType = useMemo(
    () => ticketTypes.find((ticketType) => ticketType.id === form.ticket_type_id),
    [form.ticket_type_id, ticketTypes]
  );

  const selectedAvailableStock = selectedTicketType
    ? getAvailableStock(selectedTicketType)
    : 0;
  const canGenerateInvitations = ["published", "sold_out"].includes(
    selectedSession?.status
  );

  const validateForm = () => {
    if (!form.ticket_type_id) {
      setErrorMsg("Selecciona un tipo de entrada");
      return null;
    }

    const quantity = Number(form.quantity || 0);
    if (quantity <= 0) {
      setErrorMsg("La cantidad debe ser mayor que cero");
      return null;
    }

    return quantity;
  };

  const handleSubmit = (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    const quantity = validateForm();
    if (!quantity) return;

    setPendingSubmit({ quantity });
  };

  const confirmGenerateInvitations = async () => {
    if (!pendingSubmit) return;
    try {
      setSubmitting(true);
      setErrorMsg("");
      setSuccessMsg("");

      await generateComplimentaryTicketsRequest(event.id, {
        session_id: selectedSession.id,
        ticket_type_id: form.ticket_type_id,
        quantity: pendingSubmit.quantity,
        recipient_name: form.recipient_name.trim() || null,
        note: form.note.trim() || null,
      });

      setSuccessMsg("Invitaciones generadas correctamente");
      setForm((current) => ({
        ...current,
        quantity: 1,
        recipient_name: "",
        note: "",
      }));
      setPendingSubmit(null);
      await loadData();
      await onReloadEvent?.();
    } catch (error) {
      console.error("Error generando invitaciones:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudieron generar las invitaciones"));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDownloadPdf = async (orderId: EntityId) => {
    try {
      const blob = await downloadComplimentaryTicketsPdfRequest(
        event.id,
        orderId,
        selectedSession?.id
      );
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `invitaciones-${String(orderId).split("-")[0]}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Error descargando invitaciones:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudo descargar el PDF de invitaciones"));
    }
  };

  if (!canManage) return null;

  return (
    <section className={styles.wrapper}>
      <div className={styles.header}>
        <div>
          <h3 className={styles.title}>Invitaciones</h3>
          <p className={styles.subtitle}>
            Entradas gratis para {selectedSession?.location_name || "la sesion seleccionada"}.
            Consumen stock, pero no suman recaudacion.
          </p>
        </div>
        <div className={styles.totalBox}>
          <span className={styles.totalLabel}>Total invitadas</span>
          <strong>{summary?.total || 0}</strong>
        </div>
      </div>

      {loading ? <p>Cargando invitaciones...</p> : null}
      {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}
      {successMsg ? <p className={styles.success}>{successMsg}</p> : null}

      {!loading ? (
        <>
          <div className={styles.summaryGrid}>
            {(summary?.by_ticket_type || []).length > 0 ? (
              summary?.by_ticket_type.map((item) => (
                <div className={styles.summaryItem} key={item.ticket_type_id}>
                  <span>{item.ticket_type_name}</span>
                  <strong>{item.quantity}</strong>
                </div>
              ))
            ) : (
              <p className={styles.empty}>Todavia no hay invitaciones generadas.</p>
            )}
          </div>

          {canGenerateInvitations ? (
            <form className={styles.form} onSubmit={handleSubmit}>
              <label className={styles.field}>
                Tipo de entrada
                <select
                  className={styles.input}
                  value={form.ticket_type_id}
                  onChange={(e) =>
                    setForm((current) => ({
                      ...current,
                      ticket_type_id: e.target.value,
                    }))
                  }
                >
                  {ticketTypes.map((ticketType) => (
                    <option key={ticketType.id} value={ticketType.id}>
                      {ticketType.name} - disponibles {getAvailableStock(ticketType)}
                    </option>
                  ))}
                </select>
              </label>

              <label className={styles.field}>
                Cantidad
                <input
                  className={styles.input}
                  type="number"
                  min="1"
                  max={Math.max(1, selectedAvailableStock)}
                  value={form.quantity}
                  onChange={(e) =>
                    setForm((current) => ({
                      ...current,
                      quantity: Number(e.target.value),
                    }))
                  }
                />
              </label>

              <label className={styles.field}>
                Nombre o referencia
                <input
                  className={styles.input}
                  value={form.recipient_name}
                  maxLength={255}
                  onChange={(e) =>
                    setForm((current) => ({
                      ...current,
                      recipient_name: e.target.value,
                    }))
                  }
                  placeholder="Invitado, lista, colaborador..."
                />
              </label>

              <label className={styles.fieldWide}>
                Nota interna
                <textarea
                  className={styles.textarea}
                  value={form.note}
                  maxLength={1000}
                  onChange={(e) =>
                    setForm((current) => ({
                      ...current,
                      note: e.target.value,
                    }))
                  }
                  placeholder="Motivo o contexto de la invitacion"
                />
              </label>

              <Button
                className={styles.formSubmit}
                variant="primary"
                type="submit"
                disabled={submitting || ticketTypes.length === 0 || selectedAvailableStock <= 0}
              >
                {submitting ? "Generando..." : "Generar invitaciones"}
              </Button>
            </form>
          ) : null}

          <div className={styles.log}>
            <h4 className={styles.logTitle}>Registro</h4>

            {(summary?.tickets || []).length > 0 ? (
              <div className={styles.tableWrapper}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Codigo</th>
                      <th>Tipo</th>
                      <th>Referencia</th>
                      <th>Generada por</th>
                      <th>Fecha</th>
                      <th>Nota</th>
                      <th>PDF</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary?.tickets.map((ticket) => (
                      <tr key={ticket.id}>
                        <td>{ticket.ticket_code}</td>
                        <td>{ticket.ticket_type?.name || "-"}</td>
                        <td>{ticket.recipient_name || "-"}</td>
                        <td>
                          {ticket.generated_by
                            ? `${ticket.generated_by.full_name} (${ticket.generated_by.email})`
                            : "-"}
                        </td>
                        <td>{formatDate(ticket.created_at)}</td>
                        <td>{ticket.generation_note || "-"}</td>
                        <td>
                          <Button
                            className={styles.downloadButton}
                            size="small"
                            type="button"
                            onClick={() => handleDownloadPdf(ticket.order_id)}
                          >
                            Descargar
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className={styles.empty}>El registro aparecera aqui cuando generes invitaciones.</p>
            )}
          </div>
        </>
      ) : null}

      <ConfirmDialog
        isOpen={!!pendingSubmit}
        title="Generar invitaciones"
        message={`Vas a generar ${pendingSubmit?.quantity || 0} entrada(s) gratis. Consumiran stock y quedaran registradas como invitaciones.`}
        confirmLabel="Generar invitaciones"
        loading={submitting}
        onCancel={() => setPendingSubmit(null)}
        onConfirm={confirmGenerateInvitations}
      />
    </section>
  );
}
