import Link from "next/link";
import { redirect, useParams } from "next/navigation";
import { type SubmitEvent, useCallback, useEffect, useMemo, useState } from "react";

import Button from "../../../components/ui/Button";
import PageContainer from "../../../components/ui/PageContainer";
import useAuth from "../../../hooks/useAuth";
import { getValidationStationActivityRequest } from "../api/validationStationsApi";
import { ROUTES, routeTo } from "../../../routes/paths";

import styles from "./ValidationStationActivityPage.module.css";
import { getApiErrorMessage } from "../../../api/errors";
import type { ApiSchema, ApiScope } from "../../../types/api";

const PAGE_SIZE = 50;

const RESULT_LABELS: Readonly<Record<string, string>> = {
  success: "Validada",
  already_used: "Ya usada",
  forbidden: "Otra sesion",
  invalid: "No encontrada",
  cancelled: "Cancelada",
  invalid_status: "Estado invalido",
  invalid_session: "Sesion no abierta",
  too_early: "Demasiado pronto",
  session_finished: "Sesion finalizada",
  reported: "Incidencia",
};

function getResultLabel(result: string): string {
  return RESULT_LABELS[result] || result;
}

export default function ValidationStationActivityPage() {
  const stationId = useParams<{ stationId: string }>()?.stationId;
  const { isAdmin, canAccessPromoter, authLoading } = useAuth();
  const [data, setData] = useState<ApiSchema<"ValidationStationActivityListResponse"> | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [offset, setOffset] = useState(0);
  const [filters, setFilters] = useState({ result: "", ticket_code: "" });
  const [draftFilters, setDraftFilters] = useState(filters);

  const scope: ApiScope = isAdmin ? "admin" : "promoter";

  const loadActivity = useCallback(async () => {
    if (!stationId) return;
    try {
      setLoading(true);
      setErrorMsg("");
      const params: {
        limit: number;
        offset: number;
        result?: string;
        ticket_code?: string;
      } = {
        limit: PAGE_SIZE,
        offset,
      };
      if (filters.result) params.result = filters.result;
      if (filters.ticket_code.trim()) {
        params.ticket_code = filters.ticket_code.trim();
      }

      setData(await getValidationStationActivityRequest(stationId, scope, params));
    } catch (error) {
      console.error("Error cargando actividad del puesto:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudo cargar la actividad del puesto"));
    } finally {
      setLoading(false);
    }
  }, [filters, offset, scope, stationId]);

  useEffect(() => {
    if (canAccessPromoter) {
      loadActivity();
    }
  }, [canAccessPromoter, loadActivity]);

  const totalPages = useMemo(() => {
    if (!data?.total) return 1;
    return Math.max(1, Math.ceil(data.total / PAGE_SIZE));
  }, [data?.total]);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  if (authLoading) return <p>Cargando...</p>;
  if (!canAccessPromoter) redirect(ROUTES.home);

  const applyFilters = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    setOffset(0);
    setFilters(draftFilters);
  };

  const clearFilters = () => {
    const emptyFilters = { result: "", ticket_code: "" };
    setDraftFilters(emptyFilters);
    setFilters(emptyFilters);
    setOffset(0);
  };

  return (
    <PageContainer title="Actividad del validador">
      {data?.station ? (
        <div className={styles.header}>
          <div>
            <h2 className={styles.stationName}>{data.station.name}</h2>
            <p>{data.station.event_title}</p>
            <p>{data.station.session_label}</p>
          </div>
          <div className={styles.summary}>
            <strong>{data.station.validated_count || 0}</strong>
            <span>entradas validadas</span>
          </div>
        </div>
      ) : null}

      {data?.station?.event_id ? (
        <Link
          className={styles.backLink}
          href={routeTo.eventManage(data.station.event_id, {
            session_id: data.station.session_id,
          })}
        >
          Volver a gestion del evento
        </Link>
      ) : null}

      <form className={styles.filters} onSubmit={applyFilters}>
        <label className={styles.field}>
          Resultado
          <select
            className={styles.input}
            value={draftFilters.result}
            onChange={(event) =>
              setDraftFilters((current) => ({
                ...current,
                result: event.target.value,
              }))
            }
          >
            <option value="">Todos</option>
            {Object.entries(RESULT_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className={styles.field}>
          Codigo de entrada
          <input
            className={styles.input}
            value={draftFilters.ticket_code}
            onChange={(event) =>
              setDraftFilters((current) => ({
                ...current,
                ticket_code: event.target.value,
              }))
            }
            placeholder="Buscar por codigo"
          />
        </label>
        <Button className={styles.filterAction} variant="primary" type="submit" disabled={loading}>
          Filtrar
        </Button>
        <Button
          className={styles.filterAction}
          type="button"
          disabled={loading}
          onClick={clearFilters}
        >
          Limpiar
        </Button>
      </form>

      {loading ? <p>Cargando actividad...</p> : null}
      {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}

      {!loading && data?.items?.length === 0 ? (
        <p className={styles.empty}>No hay registros con estos filtros.</p>
      ) : null}

      {data?.items?.length ? (
        <div className={styles.activityList}>
          {data.items.map((item) => (
            <article className={styles.activityRow} key={item.id}>
              <div>
                <strong>{getResultLabel(item.result)}</strong>
                <span>{item.message}</span>
                {item.notes ? <small>{item.notes}</small> : null}
              </div>
              <div className={styles.activityMeta}>
                <span>{item.ticket_code || "Sin entrada vinculada"}</span>
                <small>{new Date(item.validated_at).toLocaleString()}</small>
              </div>
            </article>
          ))}
        </div>
      ) : null}

      {data?.total ? (
        <div className={styles.pagination}>
          <Button
            type="button"
            disabled={loading || offset === 0}
            onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}
          >
            Anterior
          </Button>
          <span>
            Pagina {currentPage} de {totalPages} - {data.total} registros
          </span>
          <Button
            type="button"
            disabled={loading || offset + PAGE_SIZE >= data.total}
            onClick={() => setOffset((current) => current + PAGE_SIZE)}
          >
            Siguiente
          </Button>
        </div>
      ) : null}
    </PageContainer>
  );
}
