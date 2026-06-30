import { flagUrl } from "@/lib/api";

export function Flag({ code, team, size = 40 }: { code: string; team: string; size?: number }) {
  if (!code) {
    return <span className="flag-placeholder" title={team}>?</span>;
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      className="flag"
      src={flagUrl(code, size)}
      alt={team}
      width={size * 0.7}
      height={size * 0.5}
      loading="lazy"
    />
  );
}
