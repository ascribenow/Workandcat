import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import App from "./App";

// TEMPORARY: Unregister service workers to force cache clear
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then(regs => regs.forEach(r => r.unregister()));
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
