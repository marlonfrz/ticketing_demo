"use client";

import dynamic from "next/dynamic";

const ValidatorScanPage = dynamic(
  () => import("../../../features/validationStations/pages/ValidatorScanPage"),
  { ssr: false, loading: () => <p>Cargando escaner...</p> }
);

export default ValidatorScanPage;
