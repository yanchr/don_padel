import dayjs from "dayjs";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import PlaytomicScheduleView from "./components/PlaytomicScheduleView";
import "./App.css";

type VenueSummary = {
  total_slots: number;
  free_slots: number;
  booked_slots: number;
};

type Venue = {
  id: number;
  playtomic_venue_id: string;
  slug?: string;
  name: string;
  city?: string;
  country: string;
  latitude?: number;
  longitude?: number;
  summary: VenueSummary;
};

type AvailabilitySlot = {
  id: number;
  court_label: string;
  slot_start: string;
  slot_end: string;
  status: string;
  available_spots?: number;
  captured_at: string;
};

type VenueAvailability = {
  venue_id: number;
  at: string;
  slots: AvailabilitySlot[];
};

const formatDateTimeForInput = (date: Date) => dayjs(date).format("YYYY-MM-DDTHH:mm");

const mapCenter: [number, number] = [46.8182, 8.2275];

const toFreeRatio = (summary: VenueSummary): number | null =>
  summary.total_slots > 0 ? summary.free_slots / summary.total_slots : null;

const ratioToColor = (ratio: number | null): string => {
  if (ratio == null) {
    return "hsl(0 0% 55%)";
  }
  const clamped = Math.max(0, Math.min(1, ratio));
  const hue = Math.round(clamped * 120);
  return `hsl(${hue} 72% 45%)`;
};

function FitMapToVenues({ venues }: { venues: Venue[] }) {
  const map = useMap();

  useEffect(() => {
    if (venues.length === 0) {
      return;
    }
    if (venues.length === 1) {
      const onlyVenue = venues[0];
      map.setView([onlyVenue.latitude as number, onlyVenue.longitude as number], 11, {
        animate: false,
      });
      return;
    }
    map.fitBounds(
      venues.map((venue) => [venue.latitude as number, venue.longitude as number] as [number, number]),
      { padding: [30, 30] },
    );
  }, [map, venues]);

  return null;
}

function App() {
  const [atValue, setAtValue] = useState<string>(formatDateTimeForInput(new Date()));
  const [venues, setVenues] = useState<Venue[]>([]);
  const [selectedVenueId, setSelectedVenueId] = useState<number | null>(null);
  const [availability, setAvailability] = useState<VenueAvailability | null>(null);
  const [loadingVenues, setLoadingVenues] = useState(false);
  const [loadingAvailability, setLoadingAvailability] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [playtomicGridVenue, setPlaytomicGridVenue] = useState<Venue | null>(null);

  const selectedVenue = useMemo(
    () => venues.find((venue) => venue.id === selectedVenueId) ?? null,
    [selectedVenueId, venues],
  );
  const mappableVenues = useMemo(
    () => venues.filter((venue) => venue.latitude != null && venue.longitude != null),
    [venues],
  );

  useEffect(() => {
    const controller = new AbortController();
    const fetchVenues = async () => {
      setLoadingVenues(true);
      setError(null);
      try {
        const at = dayjs(atValue).toISOString();
        const response = await fetch(`/api/venues?at=${encodeURIComponent(at)}`, {
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new Error(`Failed to load venues (${response.status})`);
        }
        const data = (await response.json()) as Venue[];
        setVenues(data);
        setSelectedVenueId((current) => current ?? data[0]?.id ?? null);
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }
        setError(err instanceof Error ? err.message : "Unknown error while fetching venues.");
      } finally {
        setLoadingVenues(false);
      }
    };
    fetchVenues();
    return () => controller.abort();
  }, [atValue]);

  useEffect(() => {
    if (!selectedVenueId) {
      setAvailability(null);
      return;
    }
    const controller = new AbortController();
    const fetchAvailability = async () => {
      setLoadingAvailability(true);
      try {
        const at = dayjs(atValue).toISOString();
        const response = await fetch(
          `/api/venues/${selectedVenueId}/availability?at=${encodeURIComponent(at)}`,
          { signal: controller.signal },
        );
        if (!response.ok) {
          throw new Error(`Failed to load availability (${response.status})`);
        }
        const data = (await response.json()) as VenueAvailability;
        setAvailability(data);
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }
        setError(err instanceof Error ? err.message : "Unknown error while fetching availability.");
      } finally {
        setLoadingAvailability(false);
      }
    };
    fetchAvailability();
    return () => controller.abort();
  }, [selectedVenueId, atValue]);

  const scheduleInitialDate = dayjs(atValue).format("YYYY-MM-DD");
  const openPlaytomicGrid = useCallback((venue: Venue) => {
    if (!venue.playtomic_venue_id) {
      return;
    }
    setPlaytomicGridVenue(venue);
  }, []);

  useEffect(() => {
    if (!playtomicGridVenue) {
      return;
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setPlaytomicGridVenue(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
    };
  }, [playtomicGridVenue]);

  return (
    <main className="app">
      <header className="topbar">
        <div>
          <h1>don_padel</h1>
          <p>Swiss Playtomic availability monitor</p>
        </div>
        <div className="topbar__actions">
          <Link to="/times" className="topbar__link">
            PDL Zurich grid
          </Link>
          <label className="timeControl">
            Snapshot time
            <input
              type="datetime-local"
              value={atValue}
              onChange={(event) => setAtValue(event.target.value)}
            />
          </label>
        </div>
      </header>

      {error ? <div className="errorBanner">{error}</div> : null}

      <section className="content">
        <aside className="panel venuesPanel">
          <div className="panelHeader">
            <h2>Venues in Switzerland</h2>
            {loadingVenues ? <span className="chip">Loading…</span> : null}
          </div>
          <ul className="venueList">
            {venues.map((venue) => {
              const freeRatio = toFreeRatio(venue.summary) ?? 0;
              return (
                <li key={venue.id}>
                  <button
                    className={`venueCard ${venue.id === selectedVenueId ? "active" : ""}`}
                    onClick={() => setSelectedVenueId(venue.id)}
                    onDoubleClick={() => openPlaytomicGrid(venue)}
                    title="Click to select · double-click for live Playtomic schedule"
                    type="button"
                  >
                    <div>
                      <strong>{venue.name}</strong>
                      <p>{venue.city ?? "Unknown city"}</p>
                    </div>
                    <p className="statusLine">
                      {venue.summary.free_slots}/{venue.summary.total_slots} free
                    </p>
                    <div className="progressTrack">
                      <div className="progressFill" style={{ width: `${Math.round(freeRatio * 100)}%` }} />
                    </div>
                  </button>
                </li>
              );
            })}
            {!loadingVenues && venues.length === 0 ? <li>No venues available yet.</li> : null}
          </ul>
        </aside>

        <section className="panel mapPanel">
          <div className="panelHeader">
            <h2>Map</h2>
            <span className="mapLegend">Green = more free · Red = more booked · Gray = no data</span>
          </div>
          <MapContainer center={mapCenter} zoom={8} scrollWheelZoom className="mapFrame">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <FitMapToVenues venues={mappableVenues} />
            {mappableVenues.map((venue) => (
                <CircleMarker
                  key={venue.id}
                  center={[venue.latitude as number, venue.longitude as number]}
                  radius={venue.id === selectedVenueId ? 10 : 8}
                  pathOptions={{
                    color: ratioToColor(toFreeRatio(venue.summary)),
                    fillColor: ratioToColor(toFreeRatio(venue.summary)),
                    fillOpacity: 0.9,
                    weight: venue.id === selectedVenueId ? 3 : 2,
                  }}
                  eventHandlers={{
                    click: () => setSelectedVenueId(venue.id),
                    dblclick: () => openPlaytomicGrid(venue),
                  }}
                >
                  <Popup>
                    <strong>{venue.name}</strong>
                    <div>{venue.city ?? "Unknown city"}</div>
                    <div>
                      Free slots: {venue.summary.free_slots}/{venue.summary.total_slots}
                    </div>
                    <p className="mapPopupHint">Double-click the marker for the Playtomic time grid</p>
                  </Popup>
                </CircleMarker>
              ))}
          </MapContainer>
        </section>

        <aside className="panel detailPanel">
          <div className="panelHeader">
            <h2>{selectedVenue?.name ?? "Venue details"}</h2>
            {loadingAvailability ? <span className="chip">Loading…</span> : null}
          </div>
          <ul className="slotsList">
            {availability?.slots.map((slot) => (
              <li key={slot.id} className={`slot ${slot.status}`}>
                <div>
                  <strong>{slot.court_label}</strong>
                  <p>
                    {dayjs(slot.slot_start).format("DD MMM YYYY HH:mm")} -{" "}
                    {dayjs(slot.slot_end).format("HH:mm")}
                  </p>
                </div>
                <span>{slot.status}</span>
              </li>
            ))}
            {!loadingAvailability && (availability?.slots.length ?? 0) === 0 ? (
              <li>No availability snapshots found at this time.</li>
            ) : null}
          </ul>
        </aside>
      </section>

      {playtomicGridVenue ? (
        <div
          className="playtomicGridBackdrop"
          onClick={() => {
            setPlaytomicGridVenue(null);
          }}
          role="dialog"
          aria-modal="true"
          aria-label="Playtomic schedule"
        >
          <div
            className="playtomicGridDialog"
            onClick={(e) => {
              e.stopPropagation();
            }}
          >
            <PlaytomicScheduleView
              key={`${playtomicGridVenue.id}-${scheduleInitialDate}`}
              tenantId={playtomicGridVenue.playtomic_venue_id}
              clubSlugFallback={playtomicGridVenue.slug}
              initialDate={scheduleInitialDate}
              layout="embed"
              onClose={() => {
                setPlaytomicGridVenue(null);
              }}
            />
          </div>
        </div>
      ) : null}
    </main>
  );
}

export default App;
