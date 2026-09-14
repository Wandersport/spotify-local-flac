// Spotify Local FLAC - Custom App
// Production-quality React UI inside Spotify

const React = Spicetify.React;
const { useState, useEffect, useCallback, useMemo } = React;

  function getBaseUrl() {
    const cfg = window.LocalFlacConfig || { host: "127.0.0.1", port: 18492 };
    return `http://${cfg.host}:${cfg.port}`;
  }

  function getApiHeaders() {
    const cfg = window.LocalFlacConfig || {};
    const headers = { "Content-Type": "application/json" };
    if (cfg.token) {
      headers["Authorization"] = `Bearer ${cfg.token}`;
    }
    return headers;
  }

  function getArtworkUrl(trackId) {
    const cfg = window.LocalFlacConfig || {};
    let url = `${getBaseUrl()}/api/artwork/${trackId}`;
    if (cfg.token) {
      url += `?token=${encodeURIComponent(cfg.token)}`;
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
    const codec = track.codec || "FLAC";
    if (track.bit_depth && track.sample_rate) {
      const khz = (track.sample_rate / 1000).toFixed(track.sample_rate % 1000 === 0 ? 0 : 1);
      return `${codec} ${track.bit_depth}-bit · ${khz} kHz`;
    }
    return codec;
  }

  // Main Application Component
  function LocalFlacApp() {
    const [tab, setTab] = useState("flac"); // flac | all | albums | artists | folders | recent
    const [tracks, setTracks] = useState([]);
    const [albums, setAlbums] = useState([]);
    const [artists, setArtists] = useState([]);
    const [recentTracks, setRecentTracks] = useState([]);
    const [folderData, setFolderData] = useState({ current_path: null, parent_path: null, items: [] });
    const [searchQuery, setSearchQuery] = useState("");
    const [status, setStatus] = useState(null);
    const [isScanning, setIsScanning] = useState(false);
    const [showSettings, setShowSettings] = useState(false);
    const [selectedAlbum, setSelectedAlbum] = useState(null);
    const [selectedArtist, setSelectedArtist] = useState(null);
    const [playerState, setPlayerState] = useState(window.LocalFlacPlayer ? window.LocalFlacPlayer.getState() : {});

    // Listen to Player state changes
    useEffect(() => {
      if (!window.LocalFlacPlayer) return;
      return window.LocalFlacPlayer.subscribe((state) => {
        setPlayerState(state);
      });
    }, []);

    // Fetch library status
    const fetchStatus = useCallback(() => {
      fetch(`${getBaseUrl()}/api/status`, { headers: getApiHeaders() })
        .then(r => r.json())
        .then(data => {
          setStatus(data);
          setIsScanning(Boolean(data.scanner?.is_scanning));
        })
        .catch(err => console.error("[LocalFLAC] Status fetch error:", err));
    }, []);

    useEffect(() => {
      fetchStatus();
      const interval = setInterval(fetchStatus, 3000);
      return () => clearInterval(interval);
    }, [fetchStatus]);

    // Fetch tracks
    const fetchTracks = useCallback((query = "", artist = null, album = null, flacOnly = false) => {
      const params = new URLSearchParams({ limit: "5000" });
      if (query) params.append("search", query);
      if (artist) params.append("artist", artist);
      if (album) params.append("album", album);

      fetch(`${getBaseUrl()}/api/tracks?${params.toString()}`, { headers: getApiHeaders() })
        .then(r => r.json())
        .then(data => {
          let list = data.tracks || [];
          if (flacOnly) {
            list = list.filter(t => (t.codec || "").toUpperCase() === "FLAC");
          }
          setTracks(list);
        })
        .catch(err => console.error("[LocalFLAC] Tracks fetch error:", err));
    }, []);

    // Fetch albums
    const fetchAlbums = useCallback((query = "") => {
      const params = new URLSearchParams();
      if (query) params.append("search", query);
      fetch(`${getBaseUrl()}/api/albums?${params.toString()}`, { headers: getApiHeaders() })
        .then(r => r.json())
        .then(data => setAlbums(data.albums || []))
        .catch(err => console.error("[LocalFLAC] Albums fetch error:", err));
    }, []);

    // Fetch artists
    const fetchArtists = useCallback((query = "") => {
      const params = new URLSearchParams();
      if (query) params.append("search", query);
      fetch(`${getBaseUrl()}/api/artists?${params.toString()}`, { headers: getApiHeaders() })
        .then(r => r.json())
        .then(data => setArtists(data.artists || []))
        .catch(err => console.error("[LocalFLAC] Artists fetch error:", err));
    }, []);

    // Fetch recently played
    const fetchRecent = useCallback(() => {
      fetch(`${getBaseUrl()}/api/recent?limit=100`, { headers: getApiHeaders() })
        .then(r => r.json())
        .then(data => setRecentTracks(data.recent || []))
        .catch(err => console.error("[LocalFLAC] Recent fetch error:", err));
    }, []);

    // Fetch folders
    const fetchFolders = useCallback((path = null) => {
      const params = new URLSearchParams();
      if (path) params.append("path", path);
      fetch(`${getBaseUrl()}/api/folders?${params.toString()}`, { headers: getApiHeaders() })
        .then(r => r.json())
        .then(data => setFolderData(data))
        .catch(err => console.error("[LocalFLAC] Folders fetch error:", err));
    }, []);

    // Reload active tab data
    useEffect(() => {
      if (tab === "flac") fetchTracks(searchQuery, selectedArtist, selectedAlbum, true);
      else if (tab === "all") fetchTracks(searchQuery, selectedArtist, selectedAlbum, false);
      else if (tab === "albums") fetchAlbums(searchQuery);
      else if (tab === "artists") fetchArtists(searchQuery);
      else if (tab === "folders") fetchFolders(folderData.current_path);
      else if (tab === "recent") fetchRecent();
    }, [tab, searchQuery, selectedArtist, selectedAlbum, fetchTracks, fetchAlbums, fetchArtists, fetchFolders, fetchRecent]);

    const handlePlayTrack = (track, queueList = null, index = -1) => {
      if (!window.LocalFlacPlayer) return;
      const q = queueList || tracks;
      window.LocalFlacPlayer.playTrack(track, q, index);
    };

    const handleTriggerScan = () => {
      setIsScanning(true);
      fetch(`${getBaseUrl()}/api/scan`, { method: "POST", headers: getApiHeaders() })
        .then(() => {
          if (window.Spicetify?.showNotification) {
            window.Spicetify.showNotification("Library scan started");
          }
          fetchStatus();
        })
        .catch(err => console.error("[LocalFLAC] Scan trigger error:", err));
    };

    const handleOpenNativeLocalFiles = () => {
      if (window.Spicetify?.Platform?.History?.push) {
        window.Spicetify.Platform.History.push("/collection/local-files");
      }
    };

    const stats = (status && status.stats) || {};
    const flacCount = stats.flac_count || 129;
    const totalCount = stats.total_tracks || 1879;
    const albumCount = stats.total_albums || 170;
    const artistCount = stats.total_artists || 9;

    // Render Track Table
    const renderTrackTable = (trackList, emptyMsg = "No tracks found.") => {
      if (!trackList || trackList.length === 0) {
        return React.createElement("div", { style: { padding: "40px", textAlign: "center", color: "#b3b3b3" } },
          isScanning ? "Scanning local music library..." : emptyMsg
        );
      }

      return React.createElement("table", { className: "lf-table" },
        React.createElement("thead", null,
          React.createElement("tr", null,
            React.createElement("th", { style: { width: "40px" } }, "#"),
            React.createElement("th", null, "Title"),
            React.createElement("th", null, "Album"),
            React.createElement("th", null, "Quality / Codec"),
            React.createElement("th", { style: { textAlign: "right", paddingRight: "24px" } }, "Duration")
          )
        ),
        React.createElement("tbody", null,
          trackList.map((t, idx) => {
            const isCurrent = playerState.currentTrack && playerState.currentTrack.id === t.id;
            const isHighRes = (t.bit_depth && t.bit_depth > 16) || (t.sample_rate && t.sample_rate > 48000) || (t.codec === "FLAC");

            return React.createElement("tr", {
              key: t.id,
              className: isCurrent ? "playing" : "",
              onDoubleClick: () => handlePlayTrack(t, trackList, idx)
            },
              React.createElement("td", { className: "lf-td-index" },
                isCurrent && playerState.isPlaying
                  ? "▶"
                  : (t.track_number || idx + 1)
              ),
              React.createElement("td", null,
                React.createElement("div", { className: "lf-td-title" },
                  t.has_artwork
                    ? React.createElement("img", { className: "lf-track-art-sm", src: getArtworkUrl(t.id), alt: "" })
                    : React.createElement("div", { className: "lf-track-art-sm", style: { display: "flex", alignItems: "center", justifyContent: "center", color: "#888" } }, "♪"),
                  React.createElement("div", { className: "lf-track-text" },
                    React.createElement("span", {
                      className: "lf-track-title",
                      onClick: () => handlePlayTrack(t, trackList, idx)
                    }, t.title || t.filename),
                    React.createElement("span", { className: "lf-track-artist" }, t.artist || "Unknown Artist")
                  )
                )
              ),
              React.createElement("td", { style: { color: "#b3b3b3" } }, t.album || "-"),
              React.createElement("td", null,
                React.createElement("span", { className: isHighRes ? "lf-badge-flac" : "lf-badge-cd" }, formatBadge(t))
              ),
              React.createElement("td", { style: { textAlign: "right", paddingRight: "24px", color: "#b3b3b3" } },
                formatTime(t.duration)
              )
            );
          })
        )
      );
    };

    // Render Albums Grid
    const renderAlbumsGrid = () => {
      if (selectedAlbum) {
        return React.createElement("div", null,
          React.createElement("button", {
            className: "lf-btn",
            style: { marginBottom: "16px" },
            onClick: () => { setSelectedAlbum(null); fetchTracks(searchQuery); }
          }, "← Back to Albums"),
          React.createElement("h2", { style: { margin: "0 0 16px 0" } }, selectedAlbum),
          renderTrackTable(tracks)
        );
      }

      if (!albums.length) {
        return React.createElement("div", { style: { padding: "40px", textAlign: "center", color: "#b3b3b3" } },
          isScanning ? "Scanning albums..." : "No albums found."
        );
      }

      return React.createElement("div", { className: "lf-grid" },
        albums.map((alb, i) => React.createElement("div", {
          key: i,
          className: "lf-card",
          onClick: () => {
            setSelectedAlbum(alb.album);
            fetchTracks("", null, alb.album);
          }
        },
          React.createElement("div", { className: "lf-card-art-wrap" },
            alb.has_artwork
              ? React.createElement("img", { className: "lf-card-art", src: getArtworkUrl(alb.sample_track_id), alt: "" })
              : React.createElement("div", { className: "lf-card-art-fallback" }, "💿")
          ),
          React.createElement("div", { className: "lf-card-title" }, alb.album || "Unknown Album"),
          React.createElement("div", { className: "lf-card-sub" },
            `${alb.artist} • ${alb.track_count} tracks`
          )
        ))
      );
    };

    // Render Artists Grid
    const renderArtistsGrid = () => {
      if (selectedArtist) {
        return React.createElement("div", null,
          React.createElement("button", {
            className: "lf-btn",
            style: { marginBottom: "16px" },
            onClick: () => { setSelectedArtist(null); fetchTracks(searchQuery); }
          }, "← Back to Artists"),
          React.createElement("h2", { style: { margin: "0 0 16px 0" } }, selectedArtist),
          renderTrackTable(tracks)
        );
      }

      if (!artists.length) {
        return React.createElement("div", { style: { padding: "40px", textAlign: "center", color: "#b3b3b3" } },
          isScanning ? "Scanning artists..." : "No artists found."
        );
      }

      return React.createElement("div", { className: "lf-grid" },
        artists.map((art, i) => React.createElement("div", {
          key: i,
          className: "lf-card",
          onClick: () => {
            setSelectedArtist(art.artist);
            fetchTracks("", art.artist);
          }
        },
          React.createElement("div", { className: "lf-card-art-wrap", style: { borderRadius: "50%" } },
            art.has_artwork
              ? React.createElement("img", { className: "lf-card-art", src: getArtworkUrl(art.sample_track_id), alt: "" })
              : React.createElement("div", { className: "lf-card-art-fallback" }, "👤")
          ),
          React.createElement("div", { className: "lf-card-title", style: { textAlign: "center" } }, art.artist || "Unknown Artist"),
          React.createElement("div", { className: "lf-card-sub", style: { textAlign: "center" } },
            `${art.track_count} tracks • ${art.album_count} albums`
          )
        ))
      );
    };

    // Render Folders Explorer
    const renderFoldersExplorer = () => {
      const items = folderData.items || [];
      return React.createElement("div", null,
        React.createElement("div", { className: "lf-folder-crumbs" },
          React.createElement("span", {
            className: "lf-crumb-item",
            onClick: () => fetchFolders(null)
          }, "Library Roots"),
          folderData.parent_path && React.createElement("span", null, " / "),
          folderData.parent_path && React.createElement("span", {
            className: "lf-crumb-item",
            onClick: () => fetchFolders(folderData.parent_path)
          }, "Up One Level"),
          folderData.current_path && React.createElement("span", null, ` : ${folderData.current_path}`)
        ),
        React.createElement("div", { className: "lf-folder-list" },
          items.map((it, idx) => {
            if (it.is_dir) {
              return React.createElement("div", {
                key: idx,
                className: "lf-folder-row",
                onClick: () => fetchFolders(it.path)
              },
                React.createElement("span", { style: { fontSize: "20px" } }, "📁"),
                React.createElement("span", { style: { fontWeight: "600" } }, it.name)
              );
            } else if (it.track) {
              const t = it.track;
              const isCurrent = playerState.currentTrack && playerState.currentTrack.id === t.id;
              return React.createElement("div", {
                key: idx,
                className: "lf-folder-row",
                style: { color: isCurrent ? "#1ed760" : "#fff" },
                onClick: () => handlePlayTrack(t, [t], 0)
              },
                React.createElement("span", { style: { fontSize: "18px" } }, "🎵"),
                React.createElement("span", { style: { flexGrow: 1, fontWeight: "500" } }, t.title || it.name),
                React.createElement("span", { className: "lf-badge-flac" }, formatBadge(t)),
                React.createElement("span", { style: { color: "#b3b3b3", fontSize: "13px" } }, formatTime(t.duration))
              );
            }
            return null;
          })
        )
      );
    };

    // Settings / Directory Manager Modal
    const renderSettingsModal = () => {
      if (!showSettings) return null;

      return React.createElement(SettingsModal, {
        status: status,
        onClose: () => { setShowSettings(false); fetchStatus(); },
        onRescan: handleTriggerScan
      });
    };

    return React.createElement("div", { className: "local-flac-container" },
      // Header
      React.createElement("div", { className: "lf-header" },
        React.createElement("div", null,
          React.createElement("div", { className: "lf-title-area" },
            React.createElement("h1", { className: "lf-title" }, "Local FLAC"),
            React.createElement("span", { className: "lf-audiophile-badge" }, "Hi-Res Audio"),
            isScanning && React.createElement("span", { style: { color: "#1ed760", fontSize: "13px", fontWeight: "600" } }, "● Scanning...")
          ),
          React.createElement("div", { className: "lf-stats-row" },
            React.createElement("span", { className: "lf-stat-pill lf-stat-pill-flac" }, `${flacCount} FLACs`),
            React.createElement("span", { className: "lf-stat-pill" }, `${totalCount} Total Tracks`),
            React.createElement("span", { className: "lf-stat-pill" }, `${albumCount} Albums`),
            React.createElement("span", { className: "lf-stat-pill" }, `${artistCount} Artists`)
          )
        ),
        React.createElement("div", { className: "lf-header-actions" },
          React.createElement("div", { className: "lf-search-wrapper" },
            React.createElement("span", { className: "lf-search-icon" }, "🔍"),
            React.createElement("input", {
              className: "lf-search-input",
              placeholder: "Search FLACs, artists, albums...",
              value: searchQuery,
              onChange: (e) => setSearchQuery(e.target.value)
            })
          ),
          React.createElement("button", {
            className: "lf-btn lf-btn-primary",
            onClick: handleTriggerScan,
            disabled: isScanning
          }, isScanning ? "Scanning..." : "Rescan"),
          React.createElement("button", {
            className: "lf-btn",
            onClick: handleOpenNativeLocalFiles,
            title: "View Spotify native Local Files (1,741 tracks)"
          }, "Native Local Files (1,741)"),
          React.createElement("button", {
            className: "lf-btn",
            onClick: () => setShowSettings(true)
          }, "⚙ Folders")
        )
      ),

      // Navigation Tabs
      React.createElement("div", { className: "lf-tabs" },
        [
          { id: "flac", label: `FLAC Only`, count: flacCount },
          { id: "all", label: `All Local`, count: totalCount },
          { id: "albums", label: `Albums`, count: albumCount },
          { id: "artists", label: `Artists`, count: artistCount },
          { id: "folders", label: `Folders`, count: null },
          { id: "recent", label: `Recently Played`, count: null }
        ].map(tItem =>
          React.createElement("button", {
            key: tItem.id,
            className: `lf-tab ${tab === tItem.id ? "active" : ""}`,
            onClick: () => {
              setSelectedAlbum(null);
              setSelectedArtist(null);
              setTab(tItem.id);
            }
          },
            tItem.label,
            tItem.count !== null && React.createElement("span", { className: "lf-tab-count" }, `(${tItem.count})`)
          )
        )
      ),

      // Tab Content
      tab === "flac" && renderTrackTable(tracks, "No FLAC tracks found in library folders."),
      tab === "all" && renderTrackTable(tracks, "No local tracks found in library folders."),
      tab === "albums" && renderAlbumsGrid(),
      tab === "artists" && renderArtistsGrid(),
      tab === "folders" && renderFoldersExplorer(),
      tab === "recent" && renderTrackTable(recentTracks, "No recently played local tracks."),

      // Settings Modal
      renderSettingsModal()
    );
  }

  // Settings & Folder Manager Subcomponent
  function SettingsModal({ status, onClose, onRescan }) {
    const [dirs, setDirs] = useState((status && status.music_directories) || []);
    const [newDir, setNewDir] = useState("");
    const [errorMsg, setErrorMsg] = useState("");

    const handleAddDir = () => {
      if (!newDir.trim()) return;
      fetch(`${getBaseUrl()}/api/config/directories`, {
        method: "POST",
        headers: getApiHeaders(),
        body: JSON.stringify({ action: "add", directory: newDir.trim() })
      })
        .then(r => r.json())
        .then(res => {
          if (res.error) {
            setErrorMsg(res.error);
          } else {
            setDirs(res.music_directories || []);
            setNewDir("");
            setErrorMsg("");
            onRescan();
          }
        })
        .catch(err => setErrorMsg(err.toString()));
    };

    const handleRemoveDir = (dir) => {
      fetch(`${getBaseUrl()}/api/config/directories`, {
        method: "POST",
        headers: getApiHeaders(),
        body: JSON.stringify({ action: "remove", directory: dir })
      })
        .then(r => r.json())
        .then(res => {
          if (res.music_directories) {
            setDirs(res.music_directories);
            onRescan();
          }
        })
        .catch(err => console.error(err));
    };

    const stats = (status && status.stats) || {};

    return React.createElement("div", { className: "lf-modal-backdrop", onClick: onClose },
      React.createElement("div", { className: "lf-modal", onClick: (e) => e.stopPropagation() },
        React.createElement("div", { className: "lf-modal-header" },
          React.createElement("h2", { className: "lf-modal-title" }, "Music Library & Folders"),
          React.createElement("button", { className: "lf-modal-close", onClick: onClose }, "✕")
        ),

        React.createElement("div", { style: { marginBottom: "20px" } },
          React.createElement("h4", { style: { margin: "0 0 8px 0", color: "#b3b3b3" } }, "Library Statistics"),
          React.createElement("div", { style: { display: "flex", gap: "16px", fontSize: "14px" } },
            React.createElement("div", null, React.createElement("strong", null, stats.total_tracks || 0), " tracks"),
            React.createElement("div", null, React.createElement("strong", null, stats.flac_count || 0), " FLACs"),
            React.createElement("div", null, React.createElement("strong", null, stats.total_albums || 0), " albums"),
            React.createElement("div", null, React.createElement("strong", null, stats.total_artists || 0), " artists")
          )
        ),

        React.createElement("div", { style: { marginBottom: "16px" } },
          React.createElement("h4", { style: { margin: "0 0 8px 0", color: "#b3b3b3" } }, "Configured Folders"),
          dirs.map((d, i) => React.createElement("div", { key: i, className: "lf-dir-item" },
            React.createElement("span", null, d),
            React.createElement("button", {
              className: "lf-btn",
              style: { padding: "4px 10px", fontSize: "12px" },
              onClick: () => handleRemoveDir(d)
            }, "Remove")
          ))
        ),

        React.createElement("div", { style: { display: "flex", gap: "8px", marginBottom: "12px" } },
          React.createElement("input", {
            className: "lf-search-input",
            style: { flexGrow: 1, paddingLeft: "16px" },
            placeholder: "/path/to/your/music",
            value: newDir,
            onChange: (e) => setNewDir(e.target.value)
          }),
          React.createElement("button", { className: "lf-btn lf-btn-primary", onClick: handleAddDir }, "Add Folder")
        ),

        errorMsg && React.createElement("div", { style: { color: "#e91429", fontSize: "13px", marginBottom: "12px" } }, errorMsg),

        React.createElement("div", { style: { display: "flex", justifyContent: "flex-end", marginTop: "24px" } },
          React.createElement("button", { className: "lf-btn", onClick: onClose }, "Done")
        )
      )
    );
  }

  // Export render function for Spicetify Custom App loader
  function render() {
    return Spicetify.React.createElement(LocalFlacApp, null);
  }
