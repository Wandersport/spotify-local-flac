// Spotify Local FLAC - Shared API & Utility Layer

window.LocalFlacConfig = window.LocalFlacConfig || {
  host: "127.0.0.1",
  port: 18492,
  token: ""
};

const savedToken = localStorage.getItem("local_flac_token");
if (savedToken) {
  window.LocalFlacConfig.token = savedToken;
}

function isLocalFlacEnabled() {
  return localStorage.getItem("local_flac_enabled") !== "false";
}

function getBaseUrl() {
  return `http://${window.LocalFlacConfig.host}:${window.LocalFlacConfig.port}`;
}

function getApiHeaders() {
  const headers = { "Content-Type": "application/json" };
  if (window.LocalFlacConfig.token) {
    headers["Authorization"] = `Bearer ${window.LocalFlacConfig.token}`;
  }
  return headers;
}

function getStreamUrl(trackId) {
  let url = `${getBaseUrl()}/api/stream/${trackId}`;
  if (window.LocalFlacConfig.token) {
    url += `?token=${encodeURIComponent(window.LocalFlacConfig.token)}`;
  }
  return url;
}

function getArtworkUrl(trackId) {
  let url = `${getBaseUrl()}/api/artwork/${trackId}`;
  if (window.LocalFlacConfig.token) {
    url += `?token=${encodeURIComponent(window.LocalFlacConfig.token)}`;
  }
  return url;
}

function formatTime(seconds) {
  if (isNaN(seconds) || seconds < 0) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s < 10 ? "0" : ""}${s}`;
}

function formatBadge(track) {
  const codec = (track.codec || "FLAC").toUpperCase();
  if (track.bit_depth && track.sample_rate) {
    const khz = (track.sample_rate / 1000).toFixed(track.sample_rate % 1000 === 0 ? 0 : 1);
    return `${codec} ${track.bit_depth}-BIT · ${khz} KHZ`;
  }
  return codec;
}
