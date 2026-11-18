import Image from "next/image";
import Link from "next/link";

import { getEventStatusLabel } from "../../../utils/statusLabels";
import { getMediaUrl } from "../../../utils/media";
import { getNextEventSession } from "../../../utils/eventSessions";
import { routeTo } from "../../../routes/paths";
import styles from "./PromoterEventCard.module.css";
import type { Event } from "../../../types/domain";

export default function PromoterEventCard({ event }: { event: Event }) {
  const imageUrl = getMediaUrl(event.image_url);
  const nextSession = getNextEventSession(event);

  return (
    <Link href={routeTo.eventManage(event.id)} className={styles.card}>
      <div className={styles.imageColumn}>
        {imageUrl ? (
          <Image
            className={styles.image}
            src={imageUrl}
            alt={event.title}
            width={800}
            height={450}
            sizes="(max-width: 640px) 100vw, 220px"
            quality={92}
          />
        ) : (
          <div className={styles.emptyImage}>Sin imagen</div>
        )}
      </div>

      <div className={styles.content}>
        <h3 className={styles.title}>{event.title}</h3>
        {nextSession ? (
          <>
            <p className={styles.text}>
              <strong>Ubicación:</strong> {nextSession.location_name}
            </p>
            <p className={styles.text}>
              <strong>Próxima sesión:</strong>{" "}
              {new Date(nextSession.starts_at).toLocaleString()}
            </p>
          </>
        ) : null}
        <p className={styles.text}>
          <strong>Estado:</strong> {getEventStatusLabel(event.status)}
        </p>
      </div>
    </Link>
  );
}
