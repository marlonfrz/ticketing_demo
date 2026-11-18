import type { ReactNode } from "react";
import { privateRouteMetadata } from "@/metadata";

export const metadata = privateRouteMetadata;
export default function PaymentLayout({ children }: { children: ReactNode }) { return children; }
