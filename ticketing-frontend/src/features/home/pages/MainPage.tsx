"use client";

import { useMemo, useState } from "react";

import Button from "../../../components/ui/Button";
import PageContainer from "../../../components/ui/PageContainer";
import type { Event } from "../../../types/domain";
import EventCarousel from "../components/EventCarousel";
import EventCard from "../components/EventCard";
import { getFeaturedEvents, getVisibleEvents } from "../utils/homeEvents";

import styles from "./MainPage.module.css";

const EVENTS_PER_PAGE = 8;

export default function MainPage({ events }: { events: Event[] }) {
  const [visibleCount, setVisibleCount] = useState(EVENTS_PER_PAGE);
  const featuredEvents = useMemo(() => getFeaturedEvents(events), [events]);
  const visibleEvents = getVisibleEvents(events, visibleCount);
  const hasMoreEvents = visibleCount < events.length;

  return (
    <PageContainer title="Eventos">
      {events.length === 0 ? (
        <p>No hay eventos publicados todavía.</p>
      ) : null}

      {featuredEvents.length > 0 ? (
        <div className={styles.featuredSection}>
          <EventCarousel events={featuredEvents} />
        </div>
      ) : null}

      {events.length > 0 ? (
        <section className={styles.eventsSection}>
          <h2 className={styles.sectionTitle}>Todos los eventos</h2>
          <div className={styles.grid}>
            {visibleEvents.map((event, index) => (
              <EventCard key={event.id} event={event} priority={index < 4} />
            ))}
          </div>

          {hasMoreEvents ? (
            <div className={styles.loadMore}>
              <Button
                variant="secondary"
                onClick={() =>
                  setVisibleCount((current) => current + EVENTS_PER_PAGE)
                }
              >
                Mostrar más eventos
              </Button>
            </div>
          ) : null}
        </section>
      ) : null}
    </PageContainer>
  );
}
