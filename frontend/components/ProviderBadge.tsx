import type { Health } from "@/lib/api";

export function ProviderBadge({ health }: { health: Health | null }) {
  if (health === null) {
    return null;
  }

  const tone = health.provider_reachable ? "bg-ok" : "bg-bad";
  const label = health.provider_reachable ? "provider reachable" : "provider unreachable";

  return (
    <div className="flex items-center gap-2 text-xs text-muted" title={health.detail ?? label}>
      <span className={`size-2 rounded-full ${tone}`} aria-hidden />
      <span className="font-mono">{health.model}</span>
      <span>{label}</span>
    </div>
  );
}
