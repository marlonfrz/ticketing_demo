import Link from "next/link";
import Image from "next/image";

import { getMediaUrl } from "../../../utils/media";
import { getNextEventSession } from "../../../utils/eventSessions";
import { formatEventDateTime } from "../../../utils/dateTime";
import { routeTo } from "../../../routes/paths";
import styles from "./EventCard.module.css";
import type { Event } from "../../../types/domain";

type EventCardProps = {
  event: Event;
  priority?: boolean;
};

export default function EventCard({ event, priority = false }: EventCardProps) {
  const isFinished = event.status === "finished";
  const imageUrl = getMediaUrl(event.image_url);
  const nextSession = getNextEventSession(event);

  return (
    <Link href={routeTo.eventDetail(event.id)} className={styles.card}>
      <div className={styles.imageFrame}>
        {imageUrl ? (
          <Image
            className={`${styles.image} ${isFinished ? styles.finishedImage : ""}`}
            src={imageUrl}
            alt={event.title}
            fill
            sizes="(max-width: 640px) 85vw, 250px"
            quality={92}
            loading={priority ? "eager" : "lazy"}
            priority={priority}
          />
        ) : (
          <div className={styles.emptyImage}>Sin imagen</div>
        )}
      </div>

      <h3 className={styles.title}>{event.title}</h3>
      {nextSession ? (
        <>
          <p className={styles.text}>
            <strong>Ubicación:</strong> {nextSession.location_name}
          </p>
          <p className={styles.text}>
            <strong>Próxima sesión:</strong>{" "}
            {formatEventDateTime(nextSession.starts_at)}
          </p>
        </>
      ) : null}

      {event.description ? (
        <p className={styles.description}>{event.description}</p>
      ) : null}
    </Link>
  );
}
