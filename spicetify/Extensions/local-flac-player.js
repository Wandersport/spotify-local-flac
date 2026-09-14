// Spotify Local FLAC - Global Player & Playback Extension
// production-quality FLAC playback integration for Spotify

(function initLocalFlacPlayer() {
  // Configuration defaults (updated by install.sh or UI)
  window.LocalFlacConfig = window.LocalFlacConfig || {
    host: "127.0.0.1",
    port: 18492,
    token: ""
  };

  // Load saved token from localStorage if available
  const savedToken = localStorage.getItem("local_flac_token");
  if (savedToken) {
    window.LocalFlacConfig.token = savedToken;
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

  // Player singleton
  class FlacPlayer {
    constructor() {
      this.audio = new Audio();
      this.audio.preload = "auto";
      this.currentTrack = null;
      this.queue = [];
      this.queueIndex = -1;
      this.isPlaying = false;
      this.currentTime = 0;
      this.duration = 0;
      this.volume = parseFloat(localStorage.getItem("local_flac_volume") || "0.8");
      this.isMuted = localStorage.getItem("local_flac_muted") === "true";
      this.shuffle = localStorage.getItem("local_flac_shuffle") === "true";
      this.repeat = localStorage.getItem("local_flac_repeat") || "off"; // 'off' | 'all' | 'one'
      this.listeners = new Set();
      this.audio.volume = this.isMuted ? 0 : this.volume;

      this._setupAudioListeners();
      this._setupMediaSession();
      this._setupSpotifySync();
      this._setupKeyboardShortcuts();
      this._setupBottomBar();
    }

    subscribe(fn) {
      this.listeners.add(fn);
      return () => this.listeners.delete(fn);
    }

    _notify() {
      const state = this.getState();
      for (const fn of this.listeners) {
        try {
          fn(state);
        } catch (e) {
          console.error("[LocalFLAC] Listener error:", e);
        }
      }
      this._updateBottomBar();
    }

    getState() {
      return {
        currentTrack: this.currentTrack,
        queue: this.queue,
        queueIndex: this.queueIndex,
        isPlaying: this.isPlaying,
        currentTime: this.currentTime,
        duration: this.duration,
        volume: this.volume,
        isMuted: this.isMuted,
        shuffle: this.shuffle,
        repeat: this.repeat
      };
    }

    _setupAudioListeners() {
      this.audio.addEventListener("timeupdate", () => {
        this.currentTime = this.audio.currentTime || 0;
        this._notify();
      });

      this.audio.addEventListener("loadedmetadata", () => {
        this.duration = this.audio.duration || (this.currentTrack ? this.currentTrack.duration : 0);
        this._notify();
      });

      this.audio.addEventListener("play", () => {
        this.isPlaying = true;
        this._notify();
      });

      this.audio.addEventListener("pause", () => {
        this.isPlaying = false;
        this._notify();
      });

      this.audio.addEventListener("ended", () => {
        this._handleTrackEnded();
      });

      this.audio.addEventListener("error", (e) => {
        console.error("[LocalFLAC] Audio error:", this.audio.error, e);
        this.isPlaying = false;
        this._notify();
        if (window.Spicetify?.showNotification) {
          window.Spicetify.showNotification("Local FLAC playback error: " + (this.audio.error?.message || "unreachable file"));
        }
      });
    }

    _setupMediaSession() {
      if (!("mediaSession" in navigator)) return;

      navigator.mediaSession.setActionHandler("play", () => this.play());
      navigator.mediaSession.setActionHandler("pause", () => this.pause());
      navigator.mediaSession.setActionHandler("previoustrack", () => this.previous());
      navigator.mediaSession.setActionHandler("nexttrack", () => this.next());
      navigator.mediaSession.setActionHandler("seekto", (details) => {
        if (details.seekTime !== undefined) {
          this.seek(details.seekTime);
        }
      });
    }

    _updateMediaSession() {
      if (!("mediaSession" in navigator) || !this.currentTrack) return;
      const track = this.currentTrack;
      const artUrl = track.has_artwork ? getArtworkUrl(track.id) : "";

      navigator.mediaSession.metadata = new MediaMetadata({
        title: track.title || "Unknown Title",
        artist: track.artist || "Unknown Artist",
        album: track.album || "Unknown Album",
        artwork: artUrl ? [
          { src: artUrl, sizes: "512x512", type: "image/jpeg" }
        ] : []
      });
      navigator.mediaSession.playbackState = this.isPlaying ? "playing" : "paused";
    }

    _setupSpotifySync() {
      // Pause local audio when Spotify starts playing
      const checkInterval = setInterval(() => {
        if (window.Spicetify?.Player) {
          clearInterval(checkInterval);
          window.Spicetify.Player.addEventListener("songchange", () => {
            if (window.Spicetify.Player.isPlaying() && this.isPlaying) {
              this.pause();
            }
          });
        }
      }, 500);
    }

    _setupKeyboardShortcuts() {
      document.addEventListener("keydown", (e) => {
        // Ignore keydowns in form inputs
        const tag = e.target?.tagName?.toLowerCase();
        if (tag === "input" || tag === "textarea" || e.target?.isContentEditable) return;

        if (e.code === "Space" && this.currentTrack) {
          e.preventDefault();
          this.togglePlay();
        } else if (e.ctrlKey && e.code === "ArrowRight") {
          e.preventDefault();
          this.next();
        } else if (e.ctrlKey && e.code === "ArrowLeft") {
          e.preventDefault();
          this.previous();
        } else if (e.shiftKey && e.code === "ArrowRight") {
          e.preventDefault();
          this.seek(this.currentTime + 5);
        } else if (e.shiftKey && e.code === "ArrowLeft") {
          e.preventDefault();
          this.seek(this.currentTime - 5);
        }
      });
    }

    playTrack(track, queue = null, index = -1) {
      if (!track) return;

      // Pause Spotify native player
      if (window.Spicetify?.Player?.isPlaying && window.Spicetify.Player.isPlaying()) {
        try {
          window.Spicetify.Player.pause();
        } catch (e) {}
      }

      if (queue && Array.isArray(queue)) {
        this.queue = [...queue];
        this.queueIndex = index >= 0 ? index : this.queue.findIndex(t => t.id === track.id);
      } else if (!this.queue.some(t => t.id === track.id)) {
        this.queue = [track];
        this.queueIndex = 0;
      } else {
        this.queueIndex = this.queue.findIndex(t => t.id === track.id);
      }

      this.currentTrack = track;
      this.duration = track.duration || 0;
      this.currentTime = 0;

      const streamUrl = getStreamUrl(track.id);
      this.audio.src = streamUrl;
      this.audio.currentTime = 0;
      this.audio.play().then(() => {
        this.isPlaying = true;
        this._updateMediaSession();
        this._notify();
        this._recordRecentlyPlayed(track.id);
      }).catch(err => {
        console.error("[LocalFLAC] Play error:", err);
      });
    }

    play() {
      if (this.currentTrack && !this.isPlaying) {
        if (window.Spicetify?.Player?.isPlaying && window.Spicetify.Player.isPlaying()) {
          try { window.Spicetify.Player.pause(); } catch (e) {}
        }
        this.audio.play().then(() => {
          this.isPlaying = true;
          this._updateMediaSession();
          this._notify();
        }).catch(err => console.error("[LocalFLAC] Resume error:", err));
      }
    }

    pause() {
      if (this.isPlaying) {
        this.audio.pause();
        this.isPlaying = false;
        this._updateMediaSession();
        this._notify();
      }
    }

    togglePlay() {
      if (this.isPlaying) {
        this.pause();
      } else {
        this.play();
      }
    }

    seek(seconds) {
      const target = Math.max(0, Math.min(seconds, this.duration || this.audio.duration || 0));
      this.audio.currentTime = target;
      this.currentTime = target;
      this._notify();
    }

    next() {
      if (!this.queue.length) return;

      if (this.repeat === "one") {
        this.seek(0);
        this.play();
        return;
      }

      let nextIndex = this.queueIndex + 1;
      if (this.shuffle && this.queue.length > 1) {
        nextIndex = Math.floor(Math.random() * this.queue.length);
        if (nextIndex === this.queueIndex) {
          nextIndex = (this.queueIndex + 1) % this.queue.length;
        }
      }

      if (nextIndex < this.queue.length) {
        this.playTrack(this.queue[nextIndex], this.queue, nextIndex);
      } else if (this.repeat === "all") {
        this.playTrack(this.queue[0], this.queue, 0);
      } else {
        this.pause();
        this.seek(0);
      }
    }

    previous() {
      if (!this.queue.length) return;

      // If more than 3 seconds in, restart current track
      if (this.currentTime > 3) {
        this.seek(0);
        return;
      }

      let prevIndex = this.queueIndex - 1;
      if (prevIndex >= 0) {
        this.playTrack(this.queue[prevIndex], this.queue, prevIndex);
      } else if (this.repeat === "all") {
        this.playTrack(this.queue[this.queue.length - 1], this.queue, this.queue.length - 1);
      } else {
        this.seek(0);
      }
    }

    _handleTrackEnded() {
      if (this.repeat === "one") {
        this.seek(0);
        this.play();
      } else {
        this.next();
      }
    }

    setVolume(vol) {
      const v = Math.max(0, Math.min(1, vol));
      this.volume = v;
      this.isMuted = false;
      this.audio.volume = v;
      localStorage.setItem("local_flac_volume", v.toString());
      localStorage.setItem("local_flac_muted", "false");
      this._notify();
    }

    toggleMute() {
      this.isMuted = !this.isMuted;
      this.audio.volume = this.isMuted ? 0 : this.volume;
      localStorage.setItem("local_flac_muted", this.isMuted.toString());
      this._notify();
    }

    toggleShuffle() {
      this.shuffle = !this.shuffle;
      localStorage.setItem("local_flac_shuffle", this.shuffle.toString());
      this._notify();
    }

    cycleRepeat() {
      const modes = ["off", "all", "one"];
      const currentIdx = modes.indexOf(this.repeat);
      this.repeat = modes[(currentIdx + 1) % modes.length];
      localStorage.setItem("local_flac_repeat", this.repeat);
      this._notify();
    }

    addToQueue(track) {
      this.queue.push(track);
      if (!this.currentTrack) {
        this.playTrack(track, this.queue, 0);
      } else {
        this._notify();
        if (window.Spicetify?.showNotification) {
          window.Spicetify.showNotification(`Added "${track.title}" to queue`);
        }
      }
    }

    _recordRecentlyPlayed(trackId) {
      fetch(`${getBaseUrl()}/api/recent`, {
        method: "POST",
        headers: getApiHeaders(),
        body: JSON.stringify({ track_id: trackId })
      }).catch(() => {});
    }

    // Integrated Bottom Bar UI
    _setupBottomBar() {
      if (document.getElementById("local-flac-bottom-bar")) return;

      const bar = document.createElement("div");
      bar.id = "local-flac-bottom-bar";
      bar.className = "local-flac-bottom-bar hidden";
      bar.innerHTML = `
        <div class="lfb-left">
          <div class="lfb-art-container">
            <img class="lfb-art" src="" alt="" />
            <div class="lfb-art-fallback">♪</div>
          </div>
          <div class="lfb-info">
            <div class="lfb-title-row">
              <span class="lfb-title">No Track</span>
              <span class="lfb-badge">FLAC</span>
            </div>
            <div class="lfb-sub">
              <span class="lfb-artist">-</span> • <span class="lfb-album">-</span>
            </div>
          </div>
        </div>

        <div class="lfb-center">
          <div class="lfb-controls">
            <button class="lfb-btn lfb-shuffle" title="Shuffle">
              <svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor">
                <path d="M13.151.922a.75.75 0 1 0-1.06 1.06L13.109 3H11.16a3.75 3.75 0 0 0-2.873 1.34l-6.173 7.356A2.25 2.25 0 0 1 .39 12.5H0V14h.391a3.75 3.75 0 0 0 2.873-1.34l6.173-7.356a2.25 2.25 0 0 1 1.724-.804h1.947l-1.017 1.018a.75.75 0 0 0 1.06 1.06L15.98 3.75 13.15.922zM.391 3.5H0V2h.391c1.109 0 2.16.49 2.873 1.34L4.89 5.277l-.979 1.167-1.796-2.14A2.25 2.25 0 0 0 .39 3.5z"/>
                <path d="m7.5 10.723.98-1.167 1.795 2.14a2.25 2.25 0 0 0 1.725.804h1.948l-1.018-1.018a.75.75 0 0 1 1.06-1.06l2.829 2.828-2.829 2.828a.75.75 0 1 1-1.06-1.06L13.109 15H11.16a3.75 3.75 0 0 1-2.873-1.34l-1.623-1.933a.75.75 0 0 1 .836-1.004z"/>
              </svg>
            </button>
            <button class="lfb-btn lfb-prev" title="Previous">
              <svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor">
                <path d="M3.3 1a.7.7 0 0 1 .7.7v5.15l9.95-5.744a.7.7 0 0 1 1.05.606v12.576a.7.7 0 0 1-1.05.607L4 9.149V14.3a.7.7 0 0 1-1.4 0V1.7a.7.7 0 0 1 .7-.7z"/>
              </svg>
            </button>
            <button class="lfb-btn-play lfb-play" title="Play/Pause">
              <svg class="lfb-icon-play" viewBox="0 0 16 16" width="18" height="18" fill="currentColor">
                <path d="M3 1.713a.7.7 0 0 1 1.05-.607l10.89 6.288a.7.7 0 0 1 0 1.212L4.05 14.894A.7.7 0 0 1 3 14.288V1.713z"/>
              </svg>
              <svg class="lfb-icon-pause" viewBox="0 0 16 16" width="18" height="18" fill="currentColor" style="display:none">
                <path d="M2.7 1a.7.7 0 0 0-.7.7v12.6a.7.7 0 0 0 .7.7h2.6a.7.7 0 0 0 .7-.7V1.7a.7.7 0 0 0-.7-.7H2.7zm8 0a.7.7 0 0 0-.7.7v12.6a.7.7 0 0 0 .7.7h2.6a.7.7 0 0 0 .7-.7V1.7a.7.7 0 0 0-.7-.7h-2.6z"/>
              </svg>
            </button>
            <button class="lfb-btn lfb-next" title="Next">
              <svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor">
                <path d="M12.7 1a.7.7 0 0 0-.7.7v5.15L2.05 1.106A.7.7 0 0 0 1 1.712v12.576a.7.7 0 0 0 1.05.607L12 9.149V14.3a.7.7 0 0 0 1.4 0V1.7a.7.7 0 0 0-.7-.7z"/>
              </svg>
            </button>
            <button class="lfb-btn lfb-repeat" title="Repeat">
              <svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor">
                <path d="M0 4.75A3.75 3.75 0 0 1 3.75 1h8.5A3.75 3.75 0 0 1 16 4.75v5a3.75 3.75 0 0 1-3.75 3.75H9.81l1.018 1.018a.75.75 0 1 1-1.06 1.06L6.939 12.75l2.829-2.828a.75.75 0 1 1 1.06 1.06L9.811 12h2.439a2.25 2.25 0 0 0 2.25-2.25v-5a2.25 2.25 0 0 0-2.25-2.25h-8.5A2.25 2.25 0 0 0 1.5 4.75v5A2.25 2.25 0 0 0 3.75 12H5v1.5H3.75A3.75 3.75 0 0 1 0 9.75v-5z"/>
              </svg>
            </button>
          </div>
          <div class="lfb-progress-row">
            <span class="lfb-time lfb-cur-time">0:00</span>
            <div class="lfb-bar lfb-seek-bar">
              <div class="lfb-bar-fill lfb-seek-fill"></div>
            </div>
            <span class="lfb-time lfb-tot-time">0:00</span>
          </div>
        </div>

        <div class="lfb-right">
          <button class="lfb-btn lfb-vol-btn" title="Mute/Unmute">
            <svg class="lfb-vol-icon" viewBox="0 0 16 16" width="16" height="16" fill="currentColor">
              <path d="M9.741.85a.75.75 0 0 1 .375.65v13a.75.75 0 0 1-1.125.65l-6.925-4H0V4.85h2.066l6.925-4a.75.75 0 0 1 .75 0zM11.5 4.5a.75.75 0 0 1 .75.75 3.75 3.75 0 0 1 0 5.5.75.75 0 1 1-1.06-1.06 2.25 2.25 0 0 0 0-3.38.75.75 0 0 1 .31-.81z"/>
            </svg>
          </button>
          <div class="lfb-bar lfb-vol-bar" style="width:90px">
            <div class="lfb-bar-fill lfb-vol-fill" style="width:80%"></div>
          </div>
        </div>
      `;
      document.body.appendChild(bar);

      // Event listeners on bottom bar buttons
      bar.querySelector(".lfb-play").addEventListener("click", () => this.togglePlay());
      bar.querySelector(".lfb-prev").addEventListener("click", () => this.previous());
      bar.querySelector(".lfb-next").addEventListener("click", () => this.next());
      bar.querySelector(".lfb-shuffle").addEventListener("click", () => this.toggleShuffle());
      bar.querySelector(".lfb-repeat").addEventListener("click", () => this.cycleRepeat());
      bar.querySelector(".lfb-vol-btn").addEventListener("click", () => this.toggleMute());

      // Seek bar click & scrub
      const seekBar = bar.querySelector(".lfb-seek-bar");
      seekBar.addEventListener("click", (e) => {
        const rect = seekBar.getBoundingClientRect();
        const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        this.seek(ratio * (this.duration || 0));
      });

      // Volume bar click & scrub
      const volBar = bar.querySelector(".lfb-vol-bar");
      volBar.addEventListener("click", (e) => {
        const rect = volBar.getBoundingClientRect();
        const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        this.setVolume(ratio);
      });
    }

    _formatTime(seconds) {
      if (isNaN(seconds) || seconds < 0) return "0:00";
      const m = Math.floor(seconds / 60);
      const s = Math.floor(seconds % 60);
      return `${m}:${s < 10 ? "0" : ""}${s}`;
    }

    _updateBottomBar() {
      const bar = document.getElementById("local-flac-bottom-bar");
      if (!bar) return;

      if (!this.currentTrack) {
        bar.classList.add("hidden");
        return;
      }
      bar.classList.remove("hidden");

      // Info
      const track = this.currentTrack;
      bar.querySelector(".lfb-title").textContent = track.title || "Unknown Title";
      bar.querySelector(".lfb-artist").textContent = track.artist || "Unknown Artist";
      bar.querySelector(".lfb-album").textContent = track.album || "Unknown Album";

      // Audiophile Badge (FLAC 24-bit / 48 kHz)
      const badge = bar.querySelector(".lfb-badge");
      let badgeText = track.codec || "FLAC";
      if (track.bit_depth && track.sample_rate) {
        const khz = (track.sample_rate / 1000).toFixed(track.sample_rate % 1000 === 0 ? 0 : 1);
        badgeText = `${track.codec} ${track.bit_depth}-bit · ${khz} kHz`;
      }
      badge.textContent = badgeText;

      // Artwork
      const artImg = bar.querySelector(".lfb-art");
      const artFallback = bar.querySelector(".lfb-art-fallback");
      if (track.has_artwork) {
        artImg.src = getArtworkUrl(track.id);
        artImg.style.display = "block";
        artFallback.style.display = "none";
      } else {
        artImg.style.display = "none";
        artFallback.style.display = "flex";
      }

      // Play/Pause Icons
      const playIcon = bar.querySelector(".lfb-icon-play");
      const pauseIcon = bar.querySelector(".lfb-icon-pause");
      if (this.isPlaying) {
        playIcon.style.display = "none";
        pauseIcon.style.display = "block";
      } else {
        playIcon.style.display = "block";
        pauseIcon.style.display = "none";
      }

      // Shuffle and Repeat active states
      const shuffleBtn = bar.querySelector(".lfb-shuffle");
      shuffleBtn.classList.toggle("active", this.shuffle);

      const repeatBtn = bar.querySelector(".lfb-repeat");
      repeatBtn.classList.toggle("active", this.repeat !== "off");
      if (this.repeat === "one") {
        repeatBtn.setAttribute("title", "Repeat One");
      } else if (this.repeat === "all") {
        repeatBtn.setAttribute("title", "Repeat All");
      } else {
        repeatBtn.setAttribute("title", "Repeat Off");
      }

      // Progress
      const curTime = bar.querySelector(".lfb-cur-time");
      const totTime = bar.querySelector(".lfb-tot-time");
      const seekFill = bar.querySelector(".lfb-seek-fill");

      curTime.textContent = this._formatTime(this.currentTime);
      totTime.textContent = this._formatTime(this.duration);

      const progressRatio = this.duration > 0 ? (this.currentTime / this.duration) : 0;
      seekFill.style.width = `${Math.min(100, Math.max(0, progressRatio * 100))}%`;

      // Volume
      const volFill = bar.querySelector(".lfb-vol-fill");
      const volPercent = this.isMuted ? 0 : (this.volume * 100);
      volFill.style.width = `${volPercent}%`;
    }
  }

  // Instantiate singleton
  window.LocalFlacPlayer = new FlacPlayer();
  console.log("[LocalFLAC] Global player initialized successfully");
})();
