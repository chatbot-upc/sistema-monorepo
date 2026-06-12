import { fetchIntents } from "@/lib/api/intents";
import { IntentsClient } from "./_components/IntentsClient";

export default async function IntentsPage() {
  const page = await fetchIntents({ size: 100 });
  return <IntentsClient intents={page.items} />;
}
