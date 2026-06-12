import { fetchPromptVersions } from "@/lib/api/prompts";
import { PromptsClient } from "./_components/PromptsClient";

export default async function PromptsPage() {
  const versions = await fetchPromptVersions();
  return <PromptsClient versions={versions} />;
}
