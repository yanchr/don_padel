import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";
import { Fragment, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import "../pages/TimesPage.css";

dayjs.extend(utc);
dayjs.extend(timezone);

const SPORT_ID = "PADEL";
const DEFAULT_TZ = "Europe/Zurich";
const PLAYTOMIC_ORIGIN = "https://playtomic.com";
const STEP_MIN = 30;
const SLOTS_PER_DAY = (24 * 60) / STEP_MIN;
const NAME_COL_PX = 200;
const DATA_ROW_PX = 48;
const HEAD_ROW_PX = 36;

type TenantResource = {
  resource_id: string;
  name: string;
  sport_id?: string;
};

type TenantResponse = {
  resources: TenantResource[];
  tenant_name?: string;
  slug?: string;
  address?: { timezone?: string };
};

type AvailSlot = { start_time: string; duration: number; price: string };

type AvailabilityResource = { resource_id: string; start_date: string; slots: AvailSlot[] };

function timeToMinutes(t: string): number {
  const p = t.split(":");
  return Number(p[0] ?? 0) * 60 + Number(p[1] ?? 0);
}

function minutesToLabel(m: number): string {
  if (m === 0) return "12am";
  if (m < 12 * 60) {
    if (m % 60 === 0) return `${m / 60}am`;
    const hh = Math.floor(m / 60);
    return `${hh}:${String(m % 60).padStart(2, "0")}am`;
  }
  if (m === 12 * 60) return "12pm";
  if (m < 13 * 60) {
    return `12:${String(m - 12 * 60).padStart(2, "0")}pm`;
  }
  const h24 = Math.floor(m / 60);
  const h12 = h24 - 12;
  if (m % 60 === 0) {
    return `${h12}pm`;
  }
  return `${h12}:${String(m % 60).padStart(2, "0")}pm`;
}

function isCoveredBySlot(cellStart: number, s: number, duration: number): boolean {
  return s <= cellStart && cellStart + STEP_MIN <= s + duration;
}

function buildAvailableSet(slots: AvailSlot[]): Set<number> {
  const available = new Set<number>();
  for (const slot of slots) {
    const s = timeToMinutes(slot.start_time);
    for (let block = 0; block < SLOTS_PER_DAY; block += 1) {
      const start = block * STEP_MIN;
      if (isCoveredBySlot(start, s, slot.duration)) {
        available.add(start);
      }
    }
  }
  return available;
}

export type PlaytomicScheduleViewProps = {
  /** Playtomic tenant UUID; same as `playtomic_venue_id` from the DB / venues API. */
  tenantId: string;
  /** Slug for club URL and Playtomic links until the tenant response loads. */
  clubSlugFallback?: string;
  initialDate: string;
  /** e.g. sync ?date= with parent on /times */
  onUserDateChange?: (date: string) => void;
  layout: "page" | "embed";
  onClose?: () => void;
};

export default function PlaytomicScheduleView({
  tenantId,
  clubSlugFallback,
  initialDate,
  onUserDateChange,
  layout,
  onClose,
}: PlaytomicScheduleViewProps) {
  const [date, setDate] = useState(initialDate);
  const [clock, setClock] = useState(0);
  const [tenant, setTenant] = useState<TenantResponse | null>(null);
  const [availability, setAvailability] = useState<AvailabilityResource[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const tz = tenant?.address?.timezone && tenant.address.timezone.length > 0
    ? tenant.address.timezone
    : DEFAULT_TZ;

  useEffect(() => {
    setDate(initialDate);
  }, [initialDate]);

  useEffect(() => {
    const t = setInterval(() => {
      setClock((c) => c + 1);
    }, 30_000);
    return () => {
      clearInterval(t);
    };
  }, []);

  useEffect(() => {
    const ac = new AbortController();
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const [tRes, aRes] = await Promise.all([
          fetch(`/_papi/v1/tenants/${tenantId}`, { signal: ac.signal }),
          fetch(
            `/_pweb/api/clubs/availability?tenant_id=${tenantId}&date=${encodeURIComponent(
              date,
            )}&sport_id=${SPORT_ID}`,
            { signal: ac.signal },
          ),
        ]);
        if (!tRes.ok) {
          throw new Error(`Tenant API ${tRes.status}`);
        }
        if (!aRes.ok) {
          throw new Error(`Availability API ${aRes.status}`);
        }
        const tJson = (await tRes.json()) as TenantResponse;
        const aJson = (await aRes.json()) as AvailabilityResource[];
        setTenant(tJson);
        setAvailability(aJson);
      } catch (e) {
        if (e instanceof DOMException && e.name === "AbortError") {
          return;
        }
        setError(e instanceof Error ? e.message : "Request failed");
      } finally {
        setLoading(false);
      }
    })();
    return () => {
      ac.abort();
    };
  }, [tenantId, date]);

  const nameById = useMemo(() => {
    const m = new Map<string, string>();
    for (const r of tenant?.resources ?? []) {
      m.set(r.resource_id, r.name);
    }
    return m;
  }, [tenant]);

  const { nowMinutes, showNowLine, dayIsPast, dayIsFuture } = useMemo(() => {
    void clock;
    const z = dayjs().tz(tz);
    const view = dayjs.tz(date, "YYYY-MM-DD", tz);
    const today = z.startOf("day");
    if (view.isBefore(today, "day")) {
      return { nowMinutes: 0, showNowLine: false, dayIsPast: true, dayIsFuture: false };
    }
    if (view.isAfter(today, "day")) {
      return { nowMinutes: 0, showNowLine: false, dayIsPast: false, dayIsFuture: true };
    }
    return {
      nowMinutes: z.hour() * 60 + z.minute() + z.second() / 60,
      showNowLine: true,
      dayIsPast: false,
      dayIsFuture: false,
    };
  }, [date, clock, tz]);

  const isCellPast = (cellStartMin: number): boolean => {
    if (dayIsPast) {
      return true;
    }
    if (dayIsFuture) {
      return false;
    }
    return cellStartMin + STEP_MIN <= nowMinutes;
  };

  const gridRows = useMemo(() => {
    if (!availability) {
      return [];
    }
    const byId = new Map(availability.map((r) => [r.resource_id, r]));
    const order: string[] = [];
    const seen = new Set<string>();
    for (const r of tenant?.resources ?? []) {
      if (byId.has(r.resource_id) && !seen.has(r.resource_id)) {
        order.push(r.resource_id);
        seen.add(r.resource_id);
      }
    }
    for (const a of availability) {
      if (!seen.has(a.resource_id)) {
        order.push(a.resource_id);
        seen.add(a.resource_id);
      }
    }
    return order.map((id) => {
      const av = byId.get(id)!;
      const available = buildAvailableSet(av.slots);
      return {
        id,
        name: nameById.get(id) ?? `Resource ${id.slice(0, 8)}…`,
        available,
      };
    });
  }, [availability, nameById, tenant?.resources]);

  const nowLinePercent = showNowLine ? Math.min(100, Math.max(0, (nowMinutes / (24 * 60)) * 100)) : null;

  const onDateInput = (value: string) => {
    setDate(value);
    onUserDateChange?.(value);
  };

  const playtomicClubPageUrl = useMemo(() => {
    const slug =
      (tenant?.slug && tenant.slug.length > 0 ? tenant.slug : null) ?? clubSlugFallback;
    if (!slug) {
      return null;
    }
    const u = new URL(`${PLAYTOMIC_ORIGIN}/clubs/${slug}`);
    u.searchParams.set("date", date);
    return u.toString();
  }, [tenant?.slug, clubSlugFallback, date]);

  const playtomicAvailabilityApiUrl = useMemo(() => {
    const u = new URL(`${PLAYTOMIC_ORIGIN}/api/clubs/availability`);
    u.searchParams.set("tenant_id", tenantId);
    u.searchParams.set("date", date);
    u.searchParams.set("sport_id", SPORT_ID);
    return u.toString();
  }, [tenantId, date]);

  const nRows = gridRows.length;
  const dataRowCount = nRows;
  const wrapClass = `timesPage${layout === "embed" ? " timesPage--embed" : ""}`;

  return (
    <div className={wrapClass}>
      <header className="timesPage__bar">
        <div>
          <h1>{layout === "page" ? "Schedule" : "Playtomic schedule"}</h1>
          <p className="timesPage__subtitle">
            {tenant?.tenant_name ?? "…"} &middot; {date} &middot; Padel
            {layout === "embed" && (
              <span className="timesPage__tenantMeta" translate="no">
                {" "}
                &middot; <code>tenant</code> {tenantId}
              </span>
            )}
          </p>
          <p className="timesPage__sources" aria-label="Source links">
            {playtomicClubPageUrl ? (
              <a
                className="timesPage__extLink"
                href={playtomicClubPageUrl}
                target="_blank"
                rel="noopener noreferrer"
              >
                Club page
              </a>
            ) : (
              <span className="timesPage__extLink timesPage__extLink--muted" title="No slug until tenant loads">
                Club page
              </span>
            )}
            <span className="timesPage__sourceSep" aria-hidden>
              ·
            </span>
            <a
              className="timesPage__extLink"
              href={playtomicAvailabilityApiUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              Availability API
            </a>
          </p>
        </div>
        <div className="timesPage__controls">
          <label className="timesPage__dateLabel">
            Date
            <input type="date" value={date} onChange={(e) => onDateInput(e.target.value)} />
          </label>
          {layout === "page" ? (
            <Link to="/" className="timesPage__back">
              Map home
            </Link>
          ) : (
            <button type="button" className="timesPage__close" onClick={onClose}>
              Close
            </button>
          )}
        </div>
      </header>

      {error ? <div className="timesPage__error">{error}</div> : null}
      {loading ? <p className="timesPage__loading">Loading…</p> : null}

      {!loading && !error && (
        <div className="timesTableWrap">
          <div
            className="timesTable"
            style={{
              gridTemplateRows: `${HEAD_ROW_PX}px repeat(${dataRowCount}, ${DATA_ROW_PX}px)`,
            }}
          >
            <div className="timesTable__corner" style={{ gridRow: 1, gridColumn: 1 }} />
            {Array.from({ length: 24 }, (_, h) => (
              <div
                key={h}
                className="timesTable__headCell"
                style={{ gridRow: 1, gridColumn: `${2 + 2 * h} / ${2 + 2 * h + 2}` }}
              >
                {minutesToLabel(h * 60)}
              </div>
            ))}

            {gridRows.map((row, ri) => {
              const gRow = 2 + ri;
              return (
                <Fragment key={row.id}>
                  <div
                    className="timesTable__name"
                    style={{ gridRow: gRow, gridColumn: 1 }}
                    title={`${row.name} (${row.id})`}
                  >
                    <span className="timesTable__courtTitle">{row.name}</span>
                    <span className="timesTable__resourceId" translate="no">
                      {row.id}
                    </span>
                  </div>
                  {Array.from({ length: SLOTS_PER_DAY }, (_, i) => {
                    const start = i * STEP_MIN;
                    const past = isCellPast(start);
                    const open = !past && row.available.has(start);
                    const cls = ["timesTable__cell"];
                    if (past) {
                      cls.push("timesTable__cell--past");
                    } else {
                      cls.push(open ? "timesTable__cell--open" : "timesTable__cell--closed");
                    }
                    return (
                      <div
                        key={start}
                        className={cls.join(" ")}
                        style={{ gridRow: gRow, gridColumn: 2 + i }}
                      />
                    );
                  })}
                </Fragment>
              );
            })}

            {nowLinePercent != null ? (
              <div
                className="timesTable__nowLine"
                style={{
                  top: HEAD_ROW_PX,
                  left: `calc(${NAME_COL_PX}px + (100% - ${NAME_COL_PX}px) * ${(nowLinePercent / 100).toFixed(6)})`,
                }}
                aria-hidden
              />
            ) : null}
          </div>
        </div>
      )}

      <p className="timesPage__legend">
        <span>
          <i className="lg lg-open" /> available
        </span>
        <span>
          <i className="lg lg-closed" /> not available
        </span>
        <span>
          <i className="lg lg-past" /> past
        </span>
        {showNowLine ? <span>Blue line: now ({tz})</span> : null}
      </p>
    </div>
  );
}
