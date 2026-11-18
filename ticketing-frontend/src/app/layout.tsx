import type { Metadata } from "next";
import { Suspense, type ReactNode } from "react";

import Navbar from "../components/layout/Navbar";
import Footer from "../components/layout/Footer";
import styles from "../routes/AppRouter.module.css";
import "../index.css";
import Providers from "./providers";

export const metadata: Metadata = {
  title: {
    default: "Ticketing Demo",
    template: "%s | Ticketing Demo",
  },
  description: "Gestion y venta de entradas para eventos.",
  robots:
    process.env.APP_ENV === "staging"
      ? { index: false, follow: false, nocache: true }
      : undefined,
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="es">
      <body>
        <Providers>
          <div className={styles.appShell}>
            <Navbar />
            <main className={styles.mainContent}>
              <Suspense fallback={null}>{children}</Suspense>
            </main>
            <Footer />
          </div>
        </Providers>
      </body>
    </html>
  );
}
