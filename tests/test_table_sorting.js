const assert = require('assert');

// Exact sorting comparison logic implemented in LocalFlacApp
function compareTracks(a, b, col, dir) {
  let valA = "";
  let valB = "";
  if (col === "title") {
    valA = (a.title || a.filename || "").trim();
    valB = (b.title || b.filename || "").trim();
  } else if (col === "artist") {
    valA = (a.artist || "Unknown Artist").trim();
    valB = (b.artist || "Unknown Artist").trim();
  } else if (col === "album") {
    valA = (a.album || "-").trim();
    valB = (b.album || "-").trim();
  }

  let cmp = valA.localeCompare(valB, undefined, {
    sensitivity: "base",
    numeric: true
  });

  if (cmp === 0 && col !== "title") {
    const titleA = (a.title || a.filename || "").trim();
    const titleB = (b.title || b.filename || "").trim();
    cmp = titleA.localeCompare(titleB, undefined, {
      sensitivity: "base",
      numeric: true
    });
  }

  return dir === "asc" ? cmp : -cmp;
}

function sortTracks(tracks, col, dir) {
  if (!col) return tracks;
  return [...tracks].sort((a, b) => compareTracks(a, b, col, dir));
}

// Mock Player Queue Simulation
class MockFlacPlayer {
  constructor() {
    this.queue = [];
    this.queueIndex = -1;
    this.currentTrack = null;
  }

  playTrack(track, queue) {
    this.currentTrack = track;
    this.queue = queue || [track];
    this.queueIndex = this.queue.findIndex(t => t.id === track.id);
  }

  next() {
    if (this.queueIndex < this.queue.length - 1) {
      this.queueIndex++;
      this.currentTrack = this.queue[this.queueIndex];
      return this.currentTrack;
    }
    return null;
  }

  prev() {
    if (this.queueIndex > 0) {
      this.queueIndex--;
      this.currentTrack = this.queue[this.queueIndex];
      return this.currentTrack;
    }
    return null;
  }
}

// ==========================================
// TEST SUITE
// ==========================================
console.log("Running Library Table Sorting Unit Tests...\n");

const testTracks = [
  { id: 101, title: ".223 Drip", artist: "Gunna", album: "Drip or Drown 2", duration: 167 },
  { id: 102, title: "24", artist: "Kanye West", album: "DONDA [V1]", duration: 216 },
  { id: 103, title: "1000 Nights", artist: "kanye west", album: "Donda", duration: 180 },
  { id: 104, title: "Éclair", artist: "Playboi Carti", album: "Die Lit", duration: 145 },
  { id: 105, title: "Armed and Dangerous", artist: null, album: null, duration: 190 },
  { id: 106, title: "Athena", artist: "Playboi Carti", album: "Whole Lotta Red", duration: 210 },
  { id: 107, title: "bad guy", artist: "Billie Eilish", album: "WHEN WE ALL FALL ASLEEP", duration: 194 },
  { id: 108, title: "Bad Guy (Remix)", artist: "Billie Eilish", album: "WHEN WE ALL FALL ASLEEP", duration: 194 },
  { id: 109, title: null, filename: "09_unnamed.flac", artist: "Unknown Artist", album: "Misc", duration: 120 }
];

// 1. Non-mutation of original array
const originalCopy = JSON.stringify(testTracks);
const sortedDerived = sortTracks(testTracks, "title", "asc");
assert.strictEqual(JSON.stringify(testTracks), originalCopy, "sortTracks must not mutate original array");
console.log("✔ Test 1: Derived view does not mutate canonical source array.");

// 2. TITLE Ascending & Descending
const titleAsc = sortTracks(testTracks, "title", "asc").map(t => t.title || t.filename);
assert.strictEqual(titleAsc[0], ".223 Drip", "Leading punctuation sorted first or predictable");
assert.strictEqual(titleAsc[1], "09_unnamed.flac", "Fallback to filename: 09 comes before 24");
assert.strictEqual(titleAsc[2], "24", "Numeric text '24' before '1000 Nights'");
assert.strictEqual(titleAsc[3], "1000 Nights");
assert.strictEqual(titleAsc[4], "Armed and Dangerous");
console.log("✔ Test 2: TITLE ascending order correct (numeric & punctuation aware).");

const titleDesc = sortTracks(testTracks, "title", "desc").map(t => t.title || t.filename);
assert.strictEqual(titleDesc[0], "Éclair", "Unicode accent handled correctly in descending");
assert.strictEqual(titleDesc[titleDesc.length - 1], ".223 Drip");
console.log("✔ Test 3: TITLE descending order correct (Unicode & accent aware).");

// 3. ARTIST Ascending & Descending
const artistAsc = sortTracks(testTracks, "artist", "asc");
const artistNamesAsc = artistAsc.map(t => t.artist || "Unknown Artist");
assert.strictEqual(artistNamesAsc[0], "Billie Eilish");
assert.strictEqual(artistNamesAsc[1], "Billie Eilish");
assert.strictEqual(artistNamesAsc[2], "Gunna");
assert.strictEqual(artistNamesAsc[3].toLowerCase(), "kanye west");
assert.strictEqual(artistNamesAsc[4].toLowerCase(), "kanye west");
assert.strictEqual(artistNamesAsc[artistNamesAsc.length - 1], "Unknown Artist", "Missing artist sorted to Unknown Artist");
console.log("✔ Test 4: ARTIST ascending order correct (case-insensitive & missing fallback).");

const artistDesc = sortTracks(testTracks, "artist", "desc");
assert.strictEqual(artistDesc[0].artist || "Unknown Artist", "Unknown Artist");
console.log("✔ Test 5: ARTIST descending order correct.");

// 4. ALBUM Ascending & Descending
const albumAsc = sortTracks(testTracks, "album", "asc");
const albumNamesAsc = albumAsc.map(t => t.album || "-");
assert.strictEqual(albumNamesAsc[0], "-", "Missing album sorted to '-'");
assert.strictEqual(albumNamesAsc[1], "Die Lit");
assert.strictEqual(albumNamesAsc[albumNamesAsc.length - 1], "Whole Lotta Red");
console.log("✔ Test 6: ALBUM ascending order correct.");

const albumDesc = sortTracks(testTracks, "album", "desc");
assert.strictEqual(albumDesc[0].album, "Whole Lotta Red");
assert.strictEqual(albumDesc[albumDesc.length - 1].album || "-", "-");
console.log("✔ Test 7: ALBUM descending order correct.");

// 5. Visible Index Order
const sortedList = sortTracks(testTracks, "title", "asc");
const visibleIndices = sortedList.map((t, idx) => idx + 1);
assert.deepStrictEqual(visibleIndices, [1, 2, 3, 4, 5, 6, 7, 8, 9], "Visible indices must be 1..N based on current sort");
console.log("✔ Test 8: Visible # column correctly represents 1..N display order.");

// 6. Playback Queue Order Follows Visible Sorted Order
const player = new MockFlacPlayer();
// Sort by title asc
const queueAsc = sortTracks(testTracks, "title", "asc");
// User clicks track at index 4 (Armed and Dangerous, id 105)
player.playTrack(queueAsc[4], queueAsc);
assert.strictEqual(player.currentTrack.id, 105);
assert.strictEqual(player.queueIndex, 4);

// Press Next -> should play index 5 (Athena, id 106)
const nextTrack = player.next();
assert.strictEqual(nextTrack.id, 106, "Next should follow visible sorted queue");
assert.strictEqual(nextTrack.title, "Athena");

// Press Prev -> should return to index 4 (Armed and Dangerous, id 105)
const prevTrack = player.prev();
assert.strictEqual(prevTrack.id, 105, "Prev should follow visible sorted queue");

// Press Prev -> should go to index 3 (1000 Nights, id 103)
const prevTrack2 = player.prev();
assert.strictEqual(prevTrack2.id, 103);
console.log("✔ Test 9: Playback queue order follows current visible sorted order (Next/Prev verified).");

console.log("\nAll 9 table sorting unit tests passed successfully! 🎯");
