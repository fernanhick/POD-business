import { useState, useEffect } from "react";
import "./pinterest.css";
import PinterestSetup from "./PinterestSetup";
import PinFactory from "./PinFactory";
import PinSchedule from "./PinSchedule";
import PinAnalytics from "./PinAnalytics";
import AppMode from "./AppMode";
import { api } from "../api";

const SUBTABS = [
  { key: "setup", label: "Setup" },
  { key: "factory", label: "Pin Factory" },
  { key: "schedule", label: "Schedule" },
  { key: "analytics", label: "Analytics" },
  { key: "appmode", label: "App Mode" },
];

export default function PinterestTab() {
  const [subtab, setSubtab] = useState("factory");
  const [setupChecked, setSetupChecked] = useState(false);

  useEffect(() => {
    api.pinterestSetupStatus()
      .then((data) => {
        if (!data.is_connected) {
          setSubtab("setup");
        }
      })
      .catch(() => {})
      .finally(() => setSetupChecked(true));
  }, []);

  const handleSetupStatusChange = (status) => {
    if (status?.setup_complete && subtab === "setup") {
      setSubtab("factory");
    }
  };

  if (!setupChecked) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <div className="pinterest-tab">
      <nav className="pinterest-tab__nav">
        {SUBTABS.map((s) => (
          <button
            key={s.key}
            className={`subtab ${subtab === s.key ? "active" : ""}`}
            onClick={() => setSubtab(s.key)}
          >
            {s.label}
          </button>
        ))}
      </nav>

      {subtab === "setup" && <PinterestSetup onStatusChange={handleSetupStatusChange} />}
      {subtab === "factory" && <PinFactory />}
      {subtab === "schedule" && <PinSchedule />}
      {subtab === "analytics" && <PinAnalytics />}
      {subtab === "appmode" && <AppMode />}
    </div>
  );
}
