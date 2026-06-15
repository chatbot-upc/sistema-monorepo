import {
  fetchDocuments,
  fetchDocumentsSummary,
  fetchProgramOptions,
} from "@/lib/api/documents";
import { DocumentsView } from "./_components/DocumentsView";

const PAGE_SIZE = 20;

interface DocumentsPageProps {
  searchParams: Promise<{ page?: string }>;
}

export default async function DocumentsPage({
  searchParams,
}: DocumentsPageProps) {
  const { page: pageParam } = await searchParams;
  const parsed = Number.parseInt(pageParam ?? "1", 10);
  const currentPage = Number.isFinite(parsed) && parsed > 0 ? parsed : 1;

  // Parallel fetch: list + summary + program options son independientes
  // (skill: async-parallel).
  const [page, summary, programOptions] = await Promise.all([
    fetchDocuments({ page: currentPage, size: PAGE_SIZE }),
    fetchDocumentsSummary(),
    fetchProgramOptions(),
  ]);

  return (
    <DocumentsView
      documents={page.items}
      currentPage={page.page}
      totalPages={page.pages}
      total={page.total}
      summary={summary}
      programOptions={programOptions}
    />
  );
}
