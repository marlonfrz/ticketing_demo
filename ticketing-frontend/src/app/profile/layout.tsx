import type { ReactNode } from "react";
import { privateRouteMetadata } from "@/metadata";

export const metadata = privateRouteMetadata;
export default function ProfileLayout({ children }: { children: ReactNode }) { return children; }
