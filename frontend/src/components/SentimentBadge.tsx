import { Badge } from "@mantine/core";

const COLORS: Record<string, string> = {
  positive: "teal",
  negative: "red",
  neutral: "gray",
};

export function SentimentBadge({ sentiment }: { sentiment: string }) {
  const key = (sentiment || "neutral").toLowerCase();
  return (
    <Badge color={COLORS[key] ?? "gray"} variant="light" tt="capitalize">
      {sentiment || "neutral"}
    </Badge>
  );
}
