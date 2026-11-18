import Link from "next/link";
import { redirect } from "next/navigation";
import {
  type ChangeEvent,
  type SubmitEvent,
  type ReactNode,
  useEffect,
  useState,
} from "react";
import Button from "../../../components/ui/Button";
import PageContainer from "../../../components/ui/PageContainer";
import useAuth from "../../../hooks/useAuth";
import {
  getEventStatusLabel,
  getOrderStatusLabel,
  getPaymentStatusLabel,
  getUserStatusLabel,
} from "../../../utils/statusLabels";
import PasswordRequirements from "../../auth/components/PasswordRequirements";
import { ROUTES, routeTo } from "../../../routes/paths";
import {
  createAdminPromoterRequest,
  createAdminUserRequest,
  getAdminDashboardRequest,
  resendSupportOrderTicketsRequest,
  searchAdminEventsRequest,
  searchAdminUsersRequest,
  searchSupportOrdersRequest,
  updateSupportOrderContactRequest,
  type SupportOrder,
} from "../api/adminApi";
import styles from "./AdminUsersPage.module.css";
import { getApiErrorMessage } from "../../../api/errors";
import type { ApiSchema, EntityId } from "../../../types/api";

type AdminUser = ApiSchema<"AdminUserItemResponse">;
type AdminEvent = ApiSchema<"AdminEventItemResponse">;
type PaginatedData = { total: number; page: number; total_pages: number };

const USER_ROLE_OPTIONS = [
  { value: "", label: "Todos los roles" },
  { value: "buyer", label: "Comprador" },
  { value: "promoter", label: "Promotor" },
  { value: "admin", label: "Admin" },
];

const EVENT_STATUS_OPTIONS = [
  { value: "", label: "Todos los estados" },
  { value: "not_reviewed", label: "No revisado" },
  { value: "in_review", label: "En revisión" },
  { value: "draft", label: "Borrador" },
  { value: "published", label: "Publicado" },
  { value: "unpublished", label: "Despublicado" },
  { value: "cancelled", label: "Cancelado" },
  { value: "finished", label: "Finalizado" },
  { value: "sold_out", label: "Agotado" },
  { value: "archived", label: "Borrado" },
  { value: "disabled", label: "Desactivado" },
];

function formatDate(value?: string | null): string {
  if (!value) return "Sin fecha";
  return new Date(value).toLocaleString();
}

export default function AdminUsersPage() {
  const { user: currentUser, isAdmin, authLoading } = useAuth();
  const [dashboard, setDashboard] = useState<ApiSchema<"AdminDashboardResponse"> | null>(null);
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    phone: "",
    password: "",
    user_type: "promoter",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const [userSearch, setUserSearch] = useState({ q: "", role: "" });
  const [eventSearch, setEventSearch] = useState({ q: "", eventStatus: "" });
  const [userResults, setUserResults] = useState<ApiSchema<"AdminPaginatedUsersResponse"> | null>(null);
  const [eventResults, setEventResults] = useState<ApiSchema<"AdminPaginatedEventsResponse"> | null>(null);
  const [searchLoading, setSearchLoading] = useState<"" | "users" | "events">("");
  const [searchMsg, setSearchMsg] = useState("");

  const [supportQuery, setSupportQuery] = useState("");
  const [supportOrders, setSupportOrders] = useState<SupportOrder[]>([]);
  const [supportLoading, setSupportLoading] = useState(false);
  const [supportMsg, setSupportMsg] = useState("");
  const [savingContactOrderId, setSavingContactOrderId] = useState<EntityId | null>(null);
  const [resendingOrderId, setResendingOrderId] = useState<EntityId | null>(null);
  const isSuperadmin = !!currentUser?.is_superadmin;

  const loadDashboard = async () => {
    try {
      setLoading(true);
      setErrorMsg("");
      const dashboardData = await getAdminDashboardRequest();
      setDashboard(dashboardData);
    } catch (error) {
      console.error("Error cargando dashboard admin:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudo cargar admin"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAdmin) {
      loadDashboard();
    }
  }, [isAdmin]);

  const handleChange = (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setForm((current) => ({ ...current, [name]: value }));
  };

  const handleUserSearchChange = (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setUserSearch((current) => ({ ...current, [name]: value }));
  };

  const handleEventSearchChange = (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setEventSearch((current) => ({ ...current, [name]: value }));
  };

  const runUserSearch = async (page = 1) => {
    try {
      setSearchLoading("users");
      setSearchMsg("");
      setEventResults(null);
      const data = await searchAdminUsersRequest({ ...userSearch, page });
      setUserResults(data);
      if (data.items.length === 0) {
        setSearchMsg("No hay usuarios con esos filtros");
      }
    } catch (error) {
      console.error("Error buscando usuarios:", error);
      setSearchMsg(getApiErrorMessage(error, "No se pudo buscar usuarios"));
    } finally {
      setSearchLoading("");
    }
  };

  const runEventSearch = async (page = 1) => {
    try {
      setSearchLoading("events");
      setSearchMsg("");
      setUserResults(null);
      const data = await searchAdminEventsRequest({ ...eventSearch, page });
      setEventResults(data);
      if (data.items.length === 0) {
        setSearchMsg("No hay eventos con esos filtros");
      }
    } catch (error) {
      console.error("Error buscando eventos:", error);
      setSearchMsg(getApiErrorMessage(error, "No se pudo buscar eventos"));
    } finally {
      setSearchLoading("");
    }
  };

  const handleUserSearchSubmit = (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    runUserSearch(1);
  };

  const handleEventSearchSubmit = (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    runEventSearch(1);
  };

  const handleSubmit = async (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();

    try {
      setSaving(true);
      setErrorMsg("");
      setSuccessMsg("");

      const payload = {
        full_name: form.full_name,
        email: form.email,
        phone: form.phone,
        country_code: "ES",
        password: form.password,
      };

      if (form.user_type === "admin") {
        await createAdminUserRequest(payload);
      } else {
        await createAdminPromoterRequest(payload);
      }

      setSuccessMsg("Usuario creado correctamente");
      setForm({
        full_name: "",
        email: "",
        phone: "",
        password: "",
        user_type: form.user_type,
      });
      await loadDashboard();
    } catch (error) {
      console.error("Error creando usuario admin:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudo crear el usuario"));
    } finally {
      setSaving(false);
    }
  };

  const handleSupportSearch = async (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();

    try {
      setSupportLoading(true);
      setSupportMsg("");
      const data = await searchSupportOrdersRequest(supportQuery);
      setSupportOrders(data);
      if (data.length === 0) {
        setSupportMsg("No se encontraron pedidos con esos datos");
      }
    } catch (error) {
      console.error("Error buscando pedidos:", error);
      setSupportMsg(getApiErrorMessage(error, "No se pudo buscar el pedido"));
    } finally {
      setSupportLoading(false);
    }
  };

  const handleContactChange = (
    orderId: EntityId,
    field: "email" | "phone",
    value: string
  ) => {
    setSupportOrders((current) =>
      current.map((order) =>
        order.id === orderId
          ? {
              ...order,
              customer: {
                ...(order.customer || {}),
                [field]: value,
              },
            }
          : order
      )
    );
  };

  const handleSaveContact = async (order: SupportOrder) => {
    if (savingContactOrderId) return;

    try {
      setSavingContactOrderId(order.id);
      setSupportMsg("");
      const updated = await updateSupportOrderContactRequest(order.id, {
        email: order.customer?.email ?? null,
        phone: order.customer?.phone ?? null,
        reason: "Actualizado desde soporte admin",
      });
      setSupportOrders((current) =>
        current.map((item) => (item.id === order.id ? updated : item))
      );
      setSupportMsg("Contacto actualizado");
    } catch (error) {
      console.error("Error actualizando contacto:", error);
      setSupportMsg(getApiErrorMessage(error, "No se pudo actualizar el contacto"));
    } finally {
      setSavingContactOrderId(null);
    }
  };

  const handleResendTickets = async (orderId: EntityId) => {
    if (resendingOrderId) return;

    try {
      setResendingOrderId(orderId);
      setSupportMsg("");
      await resendSupportOrderTicketsRequest(orderId);
      setSupportMsg("Entradas reenviadas correctamente");
    } catch (error) {
      console.error("Error reenviando entradas:", error);
      setSupportMsg(getApiErrorMessage(error, "No se pudieron reenviar las entradas"));
    } finally {
      setResendingOrderId(null);
    }
  };

  if (authLoading) {
    return (
      <PageContainer title="Admin">
        <p>Cargando...</p>
      </PageContainer>
    );
  }

  if (!isAdmin) {
    redirect(ROUTES.home);
  }

  return (
    <PageContainer title="Admin">
      <section className={styles.stats}>
        <div className={styles.stat}>
          <span>Total usuarios</span>
          <strong>{dashboard?.total_users ?? "-"}</strong>
        </div>
        <div className={styles.stat}>
          <span>Total eventos</span>
          <strong>{dashboard?.total_events ?? "-"}</strong>
        </div>
        <div className={styles.stat}>
          <span>Revisiones pendientes</span>
          <strong>{dashboard?.pending_event_reviews ?? "-"}</strong>
        </div>
      </section>

      <section className={styles.section}>
        <h3 className={styles.title}>Busqueda admin</h3>
        <div className={styles.searchGrid}>
          <form onSubmit={handleUserSearchSubmit} className={styles.searchCard}>
            <h4 className={styles.cardTitle}>Usuarios</h4>
            <div className={styles.searchFields}>
              <label className={styles.field}>
                Nombre o email
                <input
                  className={styles.input}
                  name="q"
                  value={userSearch.q}
                  onChange={handleUserSearchChange}
                  placeholder="Buscar usuario"
                />
              </label>
              <label className={styles.field}>
                Rol
                <select
                  className={styles.input}
                  name="role"
                  value={userSearch.role}
                  onChange={handleUserSearchChange}
                >
                  {USER_ROLE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <Button variant="primary" type="submit" disabled={searchLoading === "users"}>
              {searchLoading === "users" ? "Buscando..." : "Buscar usuarios"}
            </Button>
          </form>

          <form onSubmit={handleEventSearchSubmit} className={styles.searchCard}>
            <h4 className={styles.cardTitle}>Eventos</h4>
            <div className={styles.searchFields}>
              <label className={styles.field}>
                Nombre del evento
                <input
                  className={styles.input}
                  name="q"
                  value={eventSearch.q}
                  onChange={handleEventSearchChange}
                  placeholder="Buscar evento"
                />
              </label>
              <label className={styles.field}>
                Estado
                <select
                  className={styles.input}
                  name="eventStatus"
                  value={eventSearch.eventStatus}
                  onChange={handleEventSearchChange}
                >
                  {EVENT_STATUS_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <Button variant="primary" type="submit" disabled={searchLoading === "events"}>
              {searchLoading === "events" ? "Buscando..." : "Buscar eventos"}
            </Button>
          </form>
        </div>

        {searchMsg ? <p className={styles.success}>{searchMsg}</p> : null}
        {userResults ? (
          <SearchResultsPager data={userResults} onPageChange={runUserSearch}>
            <div className={styles.table}>
              {userResults.items.map((item) => (
                <UserResultRow key={item.id} user={item} />
              ))}
            </div>
          </SearchResultsPager>
        ) : null}

        {eventResults ? (
          <SearchResultsPager data={eventResults} onPageChange={runEventSearch}>
            <div className={styles.table}>
              {eventResults.items.map((event) => (
                <EventResultLink key={event.id} event={event} />
              ))}
            </div>
          </SearchResultsPager>
        ) : null}
      </section>

      <section className={styles.section}>
        <h3 className={styles.title}>Crear usuario interno</h3>
        <form onSubmit={handleSubmit} className={styles.form}>
          <label className={styles.field}>
            Tipo
            <select
              className={styles.input}
              name="user_type"
              value={form.user_type}
              onChange={handleChange}
            >
              <option value="promoter">Promotor</option>
              {isSuperadmin ? <option value="admin">Admin</option> : null}
            </select>
          </label>

          <label className={styles.field}>
            Nombre
            <input
              className={styles.input}
              name="full_name"
              value={form.full_name}
              onChange={handleChange}
              required
            />
          </label>

          <label className={styles.field}>
            Email
            <input
              className={styles.input}
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              required
            />
          </label>

          <label className={styles.field}>
            Telefono
            <input
              className={styles.input}
              type="tel"
              name="phone"
              value={form.phone}
              onChange={handleChange}
              required
            />
          </label>

          <label className={styles.field}>
            Password
            <input
              className={styles.input}
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              minLength={12}
              required
            />
          </label>

          <PasswordRequirements password={form.password} />

          <Button variant="primary" type="submit" disabled={saving}>
            {saving ? "Creando..." : "Crear usuario"}
          </Button>
        </form>

        {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}
        {successMsg ? <p className={styles.success}>{successMsg}</p> : null}
      </section>

      <section className={styles.section}>
        <h3 className={styles.title}>Recuperacion de tickets</h3>
        <form onSubmit={handleSupportSearch} className={styles.supportSearch}>
          <input
            className={styles.input}
            value={supportQuery}
            onChange={(e) => setSupportQuery(e.target.value)}
            placeholder="Teléfono, email, nombre, localizador o ID de pago"
          />
          <Button variant="primary" type="submit" disabled={supportLoading}>
            {supportLoading ? "Buscando..." : "Buscar pedido"}
          </Button>
        </form>

        {supportMsg ? <p className={styles.success}>{supportMsg}</p> : null}

        <div className={styles.table}>
          {supportOrders.map((order) => (
            <SupportOrderRow
              key={order.id}
              order={order}
              savingContactOrderId={savingContactOrderId}
              resendingOrderId={resendingOrderId}
              onContactChange={handleContactChange}
              onSaveContact={handleSaveContact}
              onResendTickets={handleResendTickets}
            />
          ))}
        </div>
      </section>

      {loading ? <p>Cargando datos admin...</p> : null}
    </PageContainer>
  );
}

function SearchResultsPager({
  data,
  onPageChange,
  children,
}: {
  data: PaginatedData;
  onPageChange: (page: number) => void;
  children: ReactNode;
}) {
  return (
    <div className={styles.resultsBlock}>
      <div className={styles.resultsHeader}>
        <span>
          {data.total} resultado{data.total === 1 ? "" : "s"}
        </span>
        <span>
          Pagina {data.page} de {data.total_pages}
        </span>
      </div>
      {children}
      {data.total_pages > 1 ? (
        <div className={styles.pagination}>
          <Button
            type="button"
            disabled={data.page <= 1}
            onClick={() => onPageChange(data.page - 1)}
          >
            Anterior
          </Button>
          <Button
            type="button"
            disabled={data.page >= data.total_pages}
            onClick={() => onPageChange(data.page + 1)}
          >
            Siguiente
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function UserResultRow({ user }: { user: AdminUser }) {
  const isPromoter = user.roles.includes("promoter");
  const content = (
    <>
      <div>
        <strong>{user.full_name}</strong>
        <p className={styles.muted}>{user.email}</p>
      </div>
      <span>{user.roles.join(", ")}</span>
      <span>{getUserStatusLabel(user.status)}</span>
    </>
  );

  if (!isPromoter) {
    return <div className={`${styles.row} ${styles.disabledRow}`}>{content}</div>;
  }

  return (
    <Link href={routeTo.adminPromoterEvents(user.id)} className={styles.rowLink}>
      {content}
    </Link>
  );
}

function EventResultLink({ event }: { event: AdminEvent }) {
  return (
    <Link href={routeTo.eventManage(event.id)} className={styles.eventRowLink}>
      <div>
        <strong>{event.title}</strong>
        <p className={styles.muted}>{event.location_name || "Sin ubicacion"}</p>
      </div>
      <div>
        <span>{event.promoter?.full_name || "Promotor sin nombre"}</span>
        <p className={styles.muted}>{event.promoter?.email}</p>
      </div>
      <div>
        <span>{formatDate(event.starts_at)}</span>
        <p className={styles.muted}>Creado: {formatDate(event.created_at)}</p>
      </div>
      <span>{getEventStatusLabel(event.status)}</span>
    </Link>
  );
}

function SupportOrderRow({
  order,
  savingContactOrderId,
  resendingOrderId,
  onContactChange,
  onSaveContact,
  onResendTickets,
}: {
  order: SupportOrder;
  savingContactOrderId: EntityId | null;
  resendingOrderId: EntityId | null;
  onContactChange: (orderId: EntityId, field: "email" | "phone", value: string) => void;
  onSaveContact: (order: SupportOrder) => void | Promise<void>;
  onResendTickets: (orderId: EntityId) => void | Promise<void>;
}) {
  const isSavingContact = savingContactOrderId === order.id;
  const isResending = resendingOrderId === order.id;
  const isSupportActionLoading = Boolean(savingContactOrderId) || Boolean(resendingOrderId);

  return (
    <div className={styles.supportRow}>
      <div>
        <strong>{order.event?.title || "Evento"}</strong>
        <p className={styles.muted}>Pedido {order.id}</p>
        <p className={styles.muted}>
          {getOrderStatusLabel(order.status)} -{" "}
          {order.payment ? getPaymentStatusLabel(order.payment.status) : "sin pago"} -{" "}
          {Number(order.total_amount).toFixed(2)} {order.currency}
        </p>
        {(order.tickets || []).length > 0 ? (
          <details className={styles.supportTickets}>
            <summary>{order.tickets.length} entrada(s)</summary>
            <div className={styles.supportTicketList}>
              {order.tickets.map((ticket) => (
                <div className={styles.supportTicket} key={ticket.id}>
                  <strong>{ticket.ticket_code}</strong>
                  <span>{ticket.ticket_type_name || "Entrada"}</span>
                  <span>{ticket.session?.location_name || "Sin sesion"}</span>
                  <span>{ticket.status}</span>
                  <span>{ticket.source}</span>
                </div>
              ))}
            </div>
          </details>
        ) : null}
      </div>

      <label className={styles.field}>
        Email
        <input
          className={styles.input}
          value={order.customer?.email || ""}
          disabled={order.customer?.source === "account" || isSupportActionLoading}
          onChange={(e) => onContactChange(order.id, "email", e.target.value)}
        />
      </label>

      <label className={styles.field}>
        Telefono
        <input
          className={styles.input}
          value={order.customer?.phone || ""}
          disabled={order.customer?.source === "account" || isSupportActionLoading}
          onChange={(e) => onContactChange(order.id, "phone", e.target.value)}
        />
      </label>

      <div className={styles.actions}>
        <Button
          type="button"
          disabled={order.customer?.source === "account" || isSupportActionLoading}
          onClick={() => onSaveContact(order)}
        >
          {isSavingContact ? "Guardando..." : "Guardar contacto"}
        </Button>
        <Button
          variant="primary"
          type="button"
          disabled={isSupportActionLoading}
          onClick={() => onResendTickets(order.id)}
        >
          {isResending ? "Reenviando..." : "Reenviar PDF"}
        </Button>
      </div>
    </div>
  );
}
