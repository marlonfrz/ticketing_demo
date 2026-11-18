import type { ReactNode } from "react";
import styles from "./PageContainer.module.css";

type PageContainerProps = {
  title?: string;
  children: ReactNode;
};

export default function PageContainer({ title, children }: PageContainerProps) {
  return (
    <div className={styles.wrapper}>
      <div className={styles.card}>
        {title ? <h1 className={styles.title}>{title}</h1> : null}
        {children}
      </div>
    </div>
  );
}
