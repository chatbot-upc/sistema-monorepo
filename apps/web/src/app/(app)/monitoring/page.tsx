import { fetchMonitoringHealth } from "@/lib/api/monitoring";
import { MonitoringClient } from "./_components/MonitoringClient";

export const dynamic = "force-dynamic";

export default async function MonitoringPage() {
  const health = await fetchMonitoringHealth();
  return <MonitoringClient initial={health} />;
}
