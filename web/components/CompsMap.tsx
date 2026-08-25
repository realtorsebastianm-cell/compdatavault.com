"use client";

import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import type { LeaseComp, SaleComp } from "@/lib/api";

// Colored dots instead of Leaflet's default pin images -- sidesteps the
// usual bundler headache of Leaflet's default marker icon paths not
// resolving correctly through webpack/Next, and doubles as the sale/lease
// legend color.
const SALE_COLOR = "#2563eb";
const LEASE_COLOR = "#16a34a";

function dotIcon(color: string) {
  return L.divIcon({
    className: "",
    html: `<span style="display:block;width:14px;height:14px;border-radius:9999px;background:${color};border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.45);"></span>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

const saleIcon = dotIcon(SALE_COLOR);
const leaseIcon = dotIcon(LEASE_COLOR);

// Phoenix, AZ -- reasonable fallback center when there's nothing geocoded
// yet, since every comp this app has seen so far is Maricopa County.
const FALLBACK_CENTER: [number, number] = [33.4484, -112.074];

export interface MapPoint {
  dealType: "sale" | "lease";
  lat: number;
  lng: number;
  comp: SaleComp | LeaseComp;
}

export default function CompsMap({ points }: { points: MapPoint[] }) {
  const center: [number, number] =
    points.length > 0 ? [points[0].lat, points[0].lng] : FALLBACK_CENTER;

  return (
    <MapContainer
      center={center}
      zoom={points.length > 0 ? 10 : 9}
      scrollWheelZoom
      style={{ height: "70vh", width: "100%" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {points.map((p) => (
        <Marker
          key={`${p.dealType}-${p.comp.id}`}
          position={[p.lat, p.lng]}
          icon={p.dealType === "sale" ? saleIcon : leaseIcon}
        >
          <Popup>
            <div style={{ fontSize: "13px", lineHeight: 1.4 }}>
              <strong>{p.comp.address}</strong>
              <br />
              {p.comp.submarket ?? "—"} &middot;{" "}
              <span style={{ textTransform: "capitalize" }}>
                {p.comp.property_type}
              </span>
              {p.comp.building_sf
                ? ` · ${p.comp.building_sf.toLocaleString()} SF`
                : ""}
              <br />
              <a href={`/comps?type=${p.dealType}&id=${p.comp.id}`}>
                view comp &rarr;
              </a>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
