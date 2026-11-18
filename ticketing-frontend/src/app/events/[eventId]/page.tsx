import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ServerApiError, serverApiRequest } from "../../../api/server";
import PublicEventPage from "../../../features/events/pages/PublicEventPage";
import type { ManagedEvent } from "../../../types/domain";

type EventPageProps = {
  params: Promise<{ eventId: string }>;
  searchParams: Promise<{ session_id?: string; rrpp?: string }>;
};

async function getEvent(eventId: string): Promise<ManagedEvent> {
  try {
    return await serverApiRequest<ManagedEvent>(`/events/${eventId}`, {
      next: { revalidate: 30 },
    });
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 404) notFound();
    throw error;
  }
}

export async function generateMetadata({ params }: EventPageProps): Promise<Metadata> {
  const { eventId } = await params;
  const event = await getEvent(eventId);

  return {
    title: event.title,
    description: event.description || `Entradas para ${event.title}`,
  };
}

export default async function EventPage({ params, searchParams }: EventPageProps) {
  const { eventId } = await params;
  const { session_id, rrpp } = await searchParams;
  const event = await getEvent(eventId);

  return (
    <PublicEventPage
      initialEvent={event}
      initialSessionId={session_id ?? null}
      publicRelationsCode={rrpp ?? null}
    />
  );
}
