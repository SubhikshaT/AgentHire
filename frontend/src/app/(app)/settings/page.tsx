import type { Metadata } from "next";

import { RecruiterSettings } from "@/components/settings/settings-page";

export const metadata: Metadata = { title: "Settings" };

export default function Page() {
  return <RecruiterSettings />;
}
