import { fetchBillingOverviewAction } from "./_actions/billing";
import { BillingView } from "./_components/BillingView";

export default async function BillingPage() {
  const res = await fetchBillingOverviewAction();
  return <BillingView initialOverview={res.ok ? res.data : null} />;
}
