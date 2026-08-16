import { SessionViewer } from "@/components/sessions/SessionViewer";

interface SessionDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function SessionDetailPage({ params }: SessionDetailPageProps) {
  const { id } = await params;
  return <SessionViewer initialSessionId={id} />;
}
