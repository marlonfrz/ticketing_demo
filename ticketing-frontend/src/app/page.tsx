import type { Metadata } from "next";

import { serverApiRequest } from "../api/server";
import MainPage from "../features/home/pages/MainPage";
import type { Event } from "../types/domain";

export const metadata: Metadata = {
  title: "Eventos",
  description: "Descubre y compra entradas para los proximos eventos.",
};

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const events = await serverApiRequest<Event[]>("/events", {
    cache: "no-store",
  });

  return <MainPage events={events} />;
}
