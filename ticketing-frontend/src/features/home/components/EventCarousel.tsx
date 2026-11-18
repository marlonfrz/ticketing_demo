"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState, type FocusEvent } from "react";

import { routeTo } from "../../../routes/paths";
import type { Event } from "../../../types/domain";
import { getNextEventSession } from "../../../utils/eventSessions";
import { getMediaUrl } from "../../../utils/media";
import { formatEventDateTime } from "../../../utils/dateTime";
import IconButton from "../../../components/ui/IconButton";

import styles from "./EventCarousel.module.css";

const ROTATION_INTERVAL_MS = 6000;

type EventCarouselProps = {
  events: Event[];
};

function formatSessionDate(value: string): string {
  return formatEventDateTime(value);
}

export default function EventCarousel({ events }: EventCarouselProps) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [isInteracting, setIsInteracting] = useState(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  const hasMultipleEvents = events.length > 1;

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updateMotionPreference = () => setPrefersReducedMotion(mediaQuery.matches);
    updateMotionPreference();
    mediaQuery.addEventListener("change", updateMotionPreference);
    return () => mediaQuery.removeEventListener("change", updateMotionPreference);
  }, []);

  useEffect(() => {
    if (
      !hasMultipleEvents ||
      isInteracting ||
      prefersReducedMotion
    ) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      setActiveIndex((current) => (current + 1) % events.length);
    }, ROTATION_INTERVAL_MS);

    return () => window.clearInterval(intervalId);
  }, [
    events.length,
    hasMultipleEvents,
    isInteracting,
    prefersReducedMotion,
  ]);

  const safeActiveIndex = Math.min(activeIndex, Math.max(events.length - 1, 0));
  const activeEvent = events[safeActiveIndex] ?? events[0];
  if (!activeEvent) return null;

  const nextSession = getNextEventSession(activeEvent);
  const imageUrl = getMediaUrl(activeEvent.image_url);

  const changeSlide = (offset: number) => {
    setActiveIndex(
      (current) => (current + offset + events.length) % events.length
    );
  };

  const handleBlur = (event: FocusEvent<HTMLElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget)) {
      setIsInteracting(false);
    }
  };

  return (
    <section
      className={styles.carousel}
      aria-label="Eventos destacados"
      onMouseEnter={() => setIsInteracting(true)}
      onMouseLeave={() => setIsInteracting(false)}
      onFocusCapture={() => setIsInteracting(true)}
      onBlurCapture={handleBlur}
    >
      <div className={styles.frame} aria-live="off">
        <Link
          className={styles.slide}
          href={routeTo.eventDetail(activeEvent.id)}
          key={activeEvent.id}
        >
          {imageUrl ? (
            <Image
              className={styles.image}
              src={imageUrl}
              alt=""
              fill
              sizes="(max-width: 640px) 100vw, 1050px"
              quality={92}
              priority
            />
          ) : (
            <div className={styles.emptyImage} aria-hidden="true">
              <span>Ticketing</span>
            </div>
          )}

          <div className={styles.caption}>
            <span className={styles.eyebrow}>Evento destacado</span>
            <h2>{activeEvent.title}</h2>
            {nextSession ? (
              <p>
                {formatSessionDate(nextSession.starts_at)} ·{" "}
                {nextSession.location_name}
              </p>
            ) : null}
            <span className={styles.eventLink}>Ver evento</span>
          </div>
        </Link>

        {hasMultipleEvents ? (
          <>
            <IconButton
              className={`${styles.arrowButton} ${styles.previousButton}`}
              type="button"
              label="Evento anterior"
              appearance="overlay"
              onClick={() => changeSlide(-1)}
            >
              <span className={styles.previousIcon} aria-hidden="true" />
            </IconButton>
            <IconButton
              className={`${styles.arrowButton} ${styles.nextButton}`}
              type="button"
              label="Evento siguiente"
              appearance="overlay"
              onClick={() => changeSlide(1)}
            >
              <span className={styles.nextIcon} aria-hidden="true" />
            </IconButton>
          </>
        ) : null}
      </div>

      {hasMultipleEvents ? (
        <div className={styles.controls}>
          {events.length <= 8 ? (
            <div className={styles.indicators} aria-label="Seleccionar evento">
              {events.map((event, index) => (
                <button
                  key={event.id}
                  type="button"
                  className={`${styles.indicator} ${
                    index === safeActiveIndex ? styles.activeIndicator : ""
                  }`}
                  aria-label={`Mostrar evento ${index + 1}: ${event.title}`}
                  aria-current={index === safeActiveIndex ? "true" : undefined}
                  onClick={() => setActiveIndex(index)}
                />
              ))}
            </div>
          ) : (
            <span className={styles.counter}>
              {safeActiveIndex + 1} / {events.length}
            </span>
          )}
        </div>
      ) : null}
    </section>
  );
}
