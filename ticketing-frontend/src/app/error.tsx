"use client";

import { useEffect } from "react";

import Button from "../components/ui/Button";

export default function ErrorPage({ error, reset }: { error: Error; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main>
      <h1>No se pudo cargar la pagina</h1>
      <Button variant="primary" onClick={reset}>Reintentar</Button>
    </main>
  );
}
