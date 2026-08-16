import { StreamPageClient } from "@/components/stream/StreamPageClient";

interface StreamPageProps {
  params: Promise<{ sessionId: string }>;
}

export default async function StreamPage({ params }: StreamPageProps) {
  const { sessionId } = await params;
  return <StreamPageClient sessionId={sessionId} />;
}
