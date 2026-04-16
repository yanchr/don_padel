import dayjs from "dayjs";
import { useEffect, useMemo, useState } from "react";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import L from "leaflet";
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

L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
});

const formatDateTimeForInput = (date: Date) => dayjs(date).format("YYYY-MM-DDTHH:mm");

const mapCenter: [number, number] = [46.8182, 8.2275];

function App() {
  const [atValue, setAtValue] = useState<string>(formatDateTimeForInput(new Date()));
  const [venues, setVenues] = useState<Venue[]>([]);
  const [selectedVenueId, setSelectedVenueId] = useState<number | null>(null);
  const [availability, setAvailability] = useState<VenueAvailability | null>(null);
  const [loadingVenues, setLoadingVenues] = useState(false);
  const [loadingAvailability, setLoadingAvailability] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedVenue = useMemo(
    () => venues.find((venue) => venue.id === selectedVenueId) ?? null,
    [selectedVenueId, venues],
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

  return (
    <main className="app">
      <header className="topbar">
        <div>
          <h1>don_padel</h1>
          <p>Swiss Playtomic availability monitor</p>
        </div>
        <label className="timeControl">
          Snapshot time
          <input
            type="datetime-local"
            value={atValue}
            onChange={(event) => setAtValue(event.target.value)}
          />
        </label>
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
              const freeRatio =
                venue.summary.total_slots > 0
                  ? venue.summary.free_slots / venue.summary.total_slots
                  : 0;
              return (
                <li key={venue.id}>
                  <button
                    className={`venueCard ${venue.id === selectedVenueId ? "active" : ""}`}
                    onClick={() => setSelectedVenueId(venue.id)}
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
          </div>
          <MapContainer center={mapCenter} zoom={8} scrollWheelZoom className="mapFrame">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {venues
              .filter((venue) => venue.latitude != null && venue.longitude != null)
              .map((venue) => (
                <Marker key={venue.id} position={[venue.latitude as number, venue.longitude as number]}>
                  <Popup>
                    <strong>{venue.name}</strong>
                    <div>{venue.city ?? "Unknown city"}</div>
                    <div>
                      Free slots: {venue.summary.free_slots}/{venue.summary.total_slots}
                    </div>
                  </Popup>
                </Marker>
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
    </main>
  );
}

export default App;
