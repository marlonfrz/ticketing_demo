import type { ReactNode } from "react";
import { privateRouteMetadata } from "@/metadata";

export const metadata = privateRouteMetadata;
export default function PromoterLayout({ children }: { children: ReactNode }) { return children; }
