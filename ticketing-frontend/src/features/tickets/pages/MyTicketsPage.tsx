import { useEffect, useMemo, useState } from "react";

import PageContainer from "../../../components/ui/PageContainer";
import { getApiErrorMessage } from "../../../api/errors";
import useAuth from "../../../hooks/useAuth";
import type { Order } from "../../../types/domain";
import {
  downloadOrderTicketsPdfRequest,
  getMyOrdersRequest,
} from "../api/ticketsApi";
import TicketOrdersList from "../components/TicketOrdersList";
import { matchesTicketSearch } from "../utils/ticketSearch";

import styles from "./MyTicketsPage.module.css";

export default function MyTicketsPage() {
  const { user, authLoading } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [search, setSearch] = useState("");
  const [downloadingOrderId, setDownloadingOrderId] = useState("");

  useEffect(() => {
    if (!user) return;

    const loadOrders = async () => {
      try {
        setLoading(true);
        setErrorMsg("");
        setOrders(await getMyOrdersRequest());
      } catch (error) {
        setErrorMsg(getApiErrorMessage(error, "No se pudieron cargar tus entradas."));
      } finally {
        setLoading(false);
      }
    };

    void loadOrders();
  }, [user]);

  const paidOrders = useMemo(
    () =>
      orders.filter(
        (order) => order.status === "paid" && order.tickets.length > 0
      ),
    [orders]
  );
  const filteredOrders = useMemo(
    () => paidOrders.filter((order) => matchesTicketSearch(order, search)),
    [paidOrders, search]
  );

  const handleDownloadPdf = async (order: Order) => {
    try {
      setDownloadingOrderId(order.id);
      setErrorMsg("");
      const blob = await downloadOrderTicketsPdfRequest(order.id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `entradas-${order.id.slice(0, 8)}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      setErrorMsg(getApiErrorMessage(error, "No se pudo descargar el PDF."));
    } finally {
      setDownloadingOrderId("");
    }
  };

  if (authLoading) {
    return (
      <PageContainer title="Mis entradas">
        <p>Cargando entradas...</p>
      </PageContainer>
    );
  }

  if (!user) {
    return (
      <PageContainer title="Mis entradas">
        <p>No hay sesion iniciada.</p>
      </PageContainer>
    );
  }

  return (
    <PageContainer title="Mis entradas">
      <div className={styles.searchField}>
        <label htmlFor="ticket-search">Buscar entradas</label>
        <input
          id="ticket-search"
          className={styles.searchInput}
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Nombre del evento o localizador"
        />
      </div>

      {loading ? <p>Cargando entradas...</p> : null}
      {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}

      {!loading && paidOrders.length === 0 ? (
        <p className={styles.muted}>Todavia no tienes entradas compradas.</p>
      ) : null}
      {!loading && paidOrders.length > 0 && filteredOrders.length === 0 ? (
        <p className={styles.muted}>No hay entradas que coincidan con la busqueda.</p>
      ) : null}

      <TicketOrdersList
        orders={filteredOrders}
        downloadingOrderId={downloadingOrderId}
        onDownload={handleDownloadPdf}
      />
    </PageContainer>
  );
}
