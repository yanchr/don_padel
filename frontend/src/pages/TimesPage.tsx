import { useSearchParams } from "react-router-dom";
import PlaytomicScheduleView from "../components/PlaytomicScheduleView";

const DEFAULT_DATE = "2026-04-26";
const TENANT_ID = "7039d452-331e-4931-ad16-5a21c63cdffe";

/**
 * PDL Zurich: fixed-tenant view. Other clubs use the map (double-click venue) and `playtomic_venue_id`.
 */
export default function TimesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialDate = searchParams.get("date") ?? DEFAULT_DATE;
  return (
    <PlaytomicScheduleView
      tenantId={TENANT_ID}
      clubSlugFallback="pdl-zurich"
      initialDate={initialDate}
      onUserDateChange={(d) => {
        setSearchParams((p) => {
          const n = new URLSearchParams(p);
          n.set("date", d);
          return n;
        });
      }}
      layout="page"
    />
  );
}
