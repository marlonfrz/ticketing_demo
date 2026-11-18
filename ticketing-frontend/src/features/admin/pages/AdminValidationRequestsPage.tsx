import Link from "next/link";
import { redirect } from "next/navigation";
import { useEffect, useState } from "react";

import Button from "../../../components/ui/Button";
import PageContainer from "../../../components/ui/PageContainer";
import useAuth from "../../../hooks/useAuth";
import { ROUTES, routeTo } from "../../../routes/paths";
import {
  getValidationQuotaRequestsAdminRequest,
  reviewValidationQuotaRequestAdminRequest,
} from "../api/adminApi";

import styles from "./AdminValidationRequestsPage.module.css";
import { getApiErrorMessage } from "../../../api/errors";
import type { ApiSchema, EntityId } from "../../../types/api";

type QuotaRequest = ApiSchema<"ValidationQuotaRequestResponse">;
type ReviewForm = { approved_count: number | string; admin_note: string };

export default function AdminValidationRequestsPage() {
  const { isAdmin, authLoading } = useAuth();
  const [requests, setRequests] = useState<QuotaRequest[]>([]);
  const [forms, setForms] = useState<Record<EntityId, ReviewForm>>({});
  const [loading, setLoading] = useState(true);
  const [actionId, setActionId] = useState<EntityId | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  const loadRequests = async () => {
    try {
      setLoading(true);
      setErrorMsg("");
      const data = await getValidationQuotaRequestsAdminRequest("pending");
      setRequests(data);
      setForms((current) => ({
        ...Object.fromEntries(
          data.map((item) => [
            item.id,
            current[item.id] || {
              approved_count: item.requested_count,
              admin_note: "",
            },
          ])
        ),
      }));
      window.dispatchEvent(
        new CustomEvent("admin-validation-count-changed", {
          detail: { pendingValidationRequests: data.length },
        })
      );
    } catch (error) {
      console.error("Error cargando solicitudes de validacion:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudieron cargar las solicitudes de validacion"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAdmin) {
      loadRequests();
    }
  }, [isAdmin]);

  if (authLoading) return <p>Cargando...</p>;
  if (!isAdmin) redirect(ROUTES.home);

  const updateForm = (
    requestId: EntityId,
    field: keyof ReviewForm,
    value: string
  ) => {
    setForms((current) => ({
      ...current,
      [requestId]: {
        ...(current[requestId] || { approved_count: 0, admin_note: "" }),
        [field]: value,
      },
    }));
  };

  const reviewRequest = async (requestId: EntityId, status: "approved" | "rejected") => {
    if (actionId) return;

    try {
      setActionId(requestId);
      const form = forms[requestId];
      if (!form) return;
      await reviewValidationQuotaRequestAdminRequest(requestId, {
        status,
        approved_count:
          status === "approved" ? Number(form.approved_count) : null,
        admin_note: form.admin_note || null,
      });
      await loadRequests();
    } catch (error) {
      console.error("Error revisando solicitud de validacion:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudo revisar la solicitud"));
    } finally {
      setActionId(null);
    }
  };

  return (
    <PageContainer title="Solicitudes de validadores">
      {loading ? <p>Cargando solicitudes...</p> : null}
      {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}
      {!loading && requests.length === 0 ? (
        <p>No hay solicitudes pendientes.</p>
      ) : null}

      <div className={styles.list}>
        {requests.map((item) => (
          <article className={styles.card} key={item.id}>
            <div className={styles.info}>
              <h2 className={styles.title}>{item.event_title}</h2>
              <p>{item.session_label}</p>
              <p>Promotor: <strong>{item.requested_by_name}</strong></p>
              <p>Solicita <strong>{item.requested_count}</strong> puestos.</p>
              {item.promoter_note ? <p>{item.promoter_note}</p> : null}
              <Link
                href={routeTo.eventManage(item.event_id, {
                  session_id: item.session_id,
                })}
              >
                Abrir gestion del evento
              </Link>
            </div>
            <div className={styles.reviewForm}>
              <label className={styles.field}>
                Puestos aprobados
                <input
                  className={styles.input}
                  type="number"
                  min="0"
                  max={item.requested_count}
                  value={forms[item.id]?.approved_count ?? item.requested_count}
                  onChange={(event) =>
                    updateForm(item.id, "approved_count", event.target.value)
                  }
                />
              </label>
              <label className={styles.field}>
                Nota para el promotor
                <textarea
                  className={styles.textarea}
                  value={forms[item.id]?.admin_note || ""}
                  onChange={(event) =>
                    updateForm(item.id, "admin_note", event.target.value)
                  }
                />
              </label>
              <div className={styles.actions}>
                <Button
                  variant="primarySoft"
                  type="button"
                  disabled={!!actionId}
                  onClick={() => reviewRequest(item.id, "approved")}
                >
                  Aprobar cupo
                </Button>
                <Button
                  variant="danger"
                  type="button"
                  disabled={!!actionId}
                  onClick={() => reviewRequest(item.id, "rejected")}
                >
                  Rechazar
                </Button>
              </div>
            </div>
          </article>
        ))}
      </div>
    </PageContainer>
  );
}
