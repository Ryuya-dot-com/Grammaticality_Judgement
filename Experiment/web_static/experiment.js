/**
 * Grammaticality Judgment Task — RWL Web (Static)
 *
 * Pure HTML/JS implementation suitable for GitHub Pages.
 * Loads stimuli.json + audio files relative to this script.
 *
 * State machine:
 *   setup → instructions → running (fixation → prime → pause → target → iti)
 *           → inter-run-rest → ... → complete
 */

(() => {
  "use strict";

  // ============================
  // Constants (will be overridden by setup form)
  // ============================
  const TIMING = {
    FIXATION_MS: 500,
    PRIME_MAX_MS: 3500,
    PAUSE_MS: 500,
    TARGET_MAX_MS: 2500,
    RESPONSE_WINDOW_MS: 2500,
    ITI_MIN_MS: 500,
    ITI_MAX_MS: 2500,
    INITIAL_REST_MS: 2000,
    END_OF_RUN_REST_MS: 2000,
  };

  const AUDIO_BASE = "audio/";
  const STIMULI_URL = "stimuli.json";

  // ============================
  // State
  // ============================
  const state = {
    phase: "setup",
    participant: "",
    listForm: "A",
    presentationMode: "rwl",
    stimuli: [],
    runs: { 1: [], 2: [], 3: [], 4: [] },
    currentRun: 1,
    trialInRun: 0,
    sessionStartTime: null,
    trialPhaseStartTime: null,
    targetAudioEndTime: null,        // when target audio finished
    responseTimerActive: false,      // can participant respond now?
    currentResponse: null,
    currentResponseRT: null,
    currentItiMs: 1500,
    results: [],
    keyEvents: [],
    sessionTimestamp: "",
    paused: false,
    timerHandle: null,
    audioContext: null,
  };

  // ============================
  // DOM refs
  // ============================
  const $ = (sel) => document.querySelector(sel);
  const screens = {
    setup: $("#setup"),
    instructions: $("#instructions"),
    running: $("#running"),
    interRunRest: $("#inter-run-rest"),
    paused: $("#paused"),
    complete: $("#complete"),
    error: $("#error-screen"),
  };

  function showScreen(name) {
    Object.values(screens).forEach(s => s.classList.add("hidden"));
    if (screens[name]) screens[name].classList.remove("hidden");
    state.phase = name;
  }

  function setTrialText(text, options = {}) {
    const display = $("#trial-display");
    display.textContent = text;
    display.className = "";
    if (options.target) display.classList.add("target");
    if (options.fixation) display.classList.add("fixation");
  }

  function clearTrialText() {
    $("#trial-display").textContent = "";
    $("#trial-display").className = "";
  }

  function showResponseButtons(show) {
    const div = $("#response-buttons");
    if (show) div.classList.remove("hidden");
    else div.classList.add("hidden");
  }

  function showResponseProgress(show) {
    const div = $("#response-progress");
    const fill = $("#response-progress-fill");
    if (show) {
      div.classList.remove("hidden");
      // Reset fill (full width)
      fill.style.transition = "none";
      fill.classList.remove("active");
      // Force reflow to apply the reset before transition
      void fill.offsetWidth;
      // Apply transition over RESPONSE_WINDOW_MS
      fill.style.transition = `transform ${TIMING.RESPONSE_WINDOW_MS}ms linear`;
      fill.classList.add("active");
    } else {
      div.classList.add("hidden");
      fill.style.transition = "none";
      fill.classList.remove("active");
    }
  }

  /**
   * Derive Latin-square form (A or B) from Participant ID.
   * Rules:
   * - Numeric ID: odd → A, even → B
   * - Non-numeric: hash to A/B (deterministic per ID)
   */
  function deriveForm(participantId) {
    if (!participantId) return "A";
    const id = String(participantId).trim();
    // Try numeric
    const num = parseInt(id.replace(/[^\d]/g, ""), 10);
    if (Number.isFinite(num)) {
      return num % 2 === 1 ? "A" : "B";
    }
    // Hash for non-numeric: sum of char codes
    let h = 0;
    for (const c of id) h += c.charCodeAt(0);
    return h % 2 === 0 ? "A" : "B";
  }

  function nowMs() { return performance.now(); }
  function nowIso() {
    const d = new Date();
    return d.toISOString();
  }
  function sessionElapsedS() {
    if (!state.sessionStartTime) return null;
    return (nowMs() - state.sessionStartTime) / 1000;
  }

  function logKeyEvent(item_id, phase, keyLabel, source) {
    state.keyEvents.push({
      run: state.currentRun,
      trial: state.trialInRun,
      item_id: item_id || "",
      phase: phase,
      key_name: keyLabel,
      key_label: keyLabel,
      key_source: source,
      normalized_response: (keyLabel === "1" || keyLabel === "2") ? keyLabel : null,
      phase_time_ms: state.trialPhaseStartTime ? (nowMs() - state.trialPhaseStartTime) : null,
      time: nowIso(),
      onset_from_trigger_s: sessionElapsedS(),
    });
  }

  // ============================
  // Stimulus loading
  // ============================

  async function loadStimuli() {
    try {
      const res = await fetch(STIMULI_URL);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const all = await res.json();
      const form = state.listForm;
      const sub = all.filter(it => it.list_form === form || it.list_form === "AB");
      sub.forEach(it => {
        it.run_int = it[`run_assignment_${form}`];
        it.trial_int = it[`trial_index_${form}`];
      });
      const valid = sub.filter(it => it.run_int != null && it.trial_int != null);
      valid.sort((a, b) => (a.run_int - b.run_int) || (a.trial_int - b.trial_int));
      state.stimuli = valid;
      state.runs = { 1: [], 2: [], 3: [], 4: [] };
      valid.forEach(it => {
        if (state.runs[it.run_int]) state.runs[it.run_int].push(it);
      });
      console.log(`Loaded ${valid.length} items for Form ${form}`);
      console.log(`Per-run: R1=${state.runs[1].length} R2=${state.runs[2].length} R3=${state.runs[3].length} R4=${state.runs[4].length}`);
      return true;
    } catch (e) {
      console.error("Failed to load stimuli.json:", e);
      showError(`刺激ファイルの読み込みに失敗しました: ${e.message}<br>
        stimuli.json が同じディレクトリにあるか確認してください。`);
      return false;
    }
  }

  function showError(html) {
    $("#error-message").innerHTML = html;
    showScreen("error");
  }

  // ============================
  // Audio
  // ============================

  function getAudioUrl(item, kind) {
    let stem;
    if (kind === "prime") {
      stem = (item.item_type === "critical") ? item.pair_id : item.item_id;
      return `${AUDIO_BASE}prime/${stem}.wav`;
    } else {
      return `${AUDIO_BASE}target/${item.item_id}.wav`;
    }
  }

  async function loadAndPlayAudio(audioEl, url) {
    audioEl.pause();
    audioEl.currentTime = 0;
    audioEl.src = url;
    try {
      await audioEl.play();
      return true;
    } catch (e) {
      // Autoplay may be blocked; log but continue
      console.warn(`Audio playback failed for ${url}:`, e.message);
      return false;
    }
  }

  function fileExists(url) {
    return fetch(url, { method: "HEAD" })
      .then(r => r.ok)
      .catch(() => false);
  }

  // ============================
  // Trial loop
  // ============================

  function scheduleNext(callback, delayMs) {
    if (state.paused) {
      state.pendingCallback = callback;
      state.pendingDelay = delayMs;
      return;
    }
    state.timerHandle = setTimeout(callback, delayMs);
  }

  function clearTimer() {
    if (state.timerHandle) {
      clearTimeout(state.timerHandle);
      state.timerHandle = null;
    }
  }

  function startNextTrialOrEndOfRun() {
    const items = state.runs[state.currentRun];
    if (state.trialInRun >= items.length) {
      endOfRun();
    } else {
      state.trialInRun += 1;
      runTrial();
    }
  }

  function runTrial() {
    const item = state.runs[state.currentRun][state.trialInRun - 1];
    if (!item) {
      endOfRun();
      return;
    }
    state.currentResponse = null;
    state.currentResponseRT = null;
    state.currentItiMs =
      TIMING.ITI_MIN_MS +
      Math.floor(Math.random() * (TIMING.ITI_MAX_MS - TIMING.ITI_MIN_MS));

    // --- Fixation ---
    state.trialPhaseStartTime = nowMs();
    setTrialText("+", { fixation: true });
    showResponseButtons(false);

    scheduleNext(() => primePhase(item), TIMING.FIXATION_MS);
  }

  function primePhase(item) {
    state.trialPhaseStartTime = nowMs();
    if (state.presentationMode !== "audio_only") {
      setTrialText(item.prime_text);
    } else {
      clearTrialText();
    }
    if (state.presentationMode !== "text_only") {
      const audio = $("#audio-prime");
      loadAndPlayAudio(audio, getAudioUrl(item, "prime"));
    }
    scheduleNext(() => pausePhase(item), TIMING.PRIME_MAX_MS);
  }

  function pausePhase(item) {
    state.trialPhaseStartTime = nowMs();
    clearTrialText();
    $("#audio-prime").pause();
    scheduleNext(() => targetPhase(item), TIMING.PAUSE_MS);
  }

  function targetPhase(item) {
    state.trialPhaseStartTime = nowMs();
    state.targetAudioEndTime = null;
    state.responseTimerActive = false;

    if (state.presentationMode !== "audio_only") {
      setTrialText(item.target_text, { target: true });
    } else {
      clearTrialText();
    }
    // Buttons hidden until audio ends (so RT measured post-audio)
    showResponseButtons(false);
    showResponseProgress(false);

    const audio = $("#audio-target");

    // Schedule response window start once audio ends
    const onAudioEnd = () => {
      if (state.responseTimerActive) return;  // guard
      state.responseTimerActive = true;
      state.targetAudioEndTime = nowMs();
      showResponseButtons(true);
      showResponseProgress(true);
      scheduleNext(() => endTrialItem(item), TIMING.RESPONSE_WINDOW_MS);
    };

    if (state.presentationMode === "text_only") {
      // No audio: start response window after TARGET_MAX_MS (text reading time)
      scheduleNext(onAudioEnd, TIMING.TARGET_MAX_MS);
    } else {
      audio.onended = onAudioEnd;
      // Fallback: if audio fails to play or never fires `ended`, force end after TARGET_MAX_MS
      scheduleNext(() => {
        if (!state.responseTimerActive) {
          console.warn("Audio did not fire 'ended'; forcing response window start.");
          onAudioEnd();
        }
      }, TIMING.TARGET_MAX_MS);
      loadAndPlayAudio(audio, getAudioUrl(item, "target"));
    }
  }

  function endTrialItem(item) {
    clearTimer();
    $("#audio-target").pause();
    clearTrialText();
    showResponseButtons(false);
    showResponseProgress(false);

    // Save trial
    const responseNorm = state.currentResponse === "1" ? "yes"
                       : state.currentResponse === "2" ? "no"
                       : null;
    const correct = (responseNorm && item.expected_response)
      ? (responseNorm === item.expected_response ? 1 : 0)
      : null;

    state.results.push({
      run: state.currentRun,
      trial: state.trialInRun,
      item_id: item.item_id,
      pair_id: item.pair_id,
      version: item.version || "",
      item_type: item.item_type || "",
      family_id: item.family_id || "",
      construct: item.construct || "",
      q_vector: item.q_vector || "",
      prime_text: item.prime_text,
      target_text: item.target_text,
      target_lemma: item.target_lemma || "",
      critical_region: item.critical_region || "",
      expected_response: item.expected_response,
      response: responseNorm,
      response_correct: correct,
      rt_from_audio_end_ms: state.currentResponseRT,
      target_audio_end_time_ms: state.targetAudioEndTime
        ? state.targetAudioEndTime - state.sessionStartTime
        : null,
      iti_ms: state.currentItiMs,
      time: nowIso(),
      onset_from_session_s: sessionElapsedS(),
      list_form: state.listForm,
    });

    // ITI then next trial
    scheduleNext(() => startNextTrialOrEndOfRun(), state.currentItiMs);
  }

  function endOfRun() {
    clearTrialText();
    showResponseButtons(false);
    setTrialText("+", { fixation: true });
    scheduleNext(() => {
      clearTrialText();
      if (state.currentRun >= 4) {
        completeExperiment();
      } else {
        showInterRunRest();
      }
    }, TIMING.END_OF_RUN_REST_MS);
  }

  function showInterRunRest() {
    $("#completed-run").textContent = state.currentRun;
    // Show brief per-run summary
    const runResults = state.results.filter(r => r.run === state.currentRun);
    const valid = runResults.filter(r => r.response_correct !== null);
    if (valid.length > 0) {
      const acc = (valid.reduce((s, r) => s + r.response_correct, 0) / valid.length * 100).toFixed(1);
      const rts = valid.filter(r => r.response_correct === 1 && r.rt_from_target_onset_ms != null).map(r => r.rt_from_target_onset_ms);
      const meanRt = rts.length > 0 ? (rts.reduce((s, x) => s + x, 0) / rts.length).toFixed(0) : "—";
      $("#run-summary").textContent =
        `Run ${state.currentRun} 結果: 正解率 ${acc}% / 平均RT ${meanRt} ms (n=${valid.length})`;
    }
    showScreen("interRunRest");
    $("#next-run-btn").textContent = `▶ Begin Run ${state.currentRun + 1}`;
  }

  function startNextRun() {
    state.currentRun += 1;
    state.trialInRun = 0;
    state.currentResponse = null;
    state.currentResponseRT = null;
    showScreen("running");
    // Brief initial rest then first trial
    setTrialText("+", { fixation: true });
    scheduleNext(() => {
      clearTrialText();
      startNextTrialOrEndOfRun();
    }, TIMING.INITIAL_REST_MS);
  }

  function completeExperiment() {
    showScreen("complete");
    renderResultsPreview();
    renderSummary();
  }

  // ============================
  // Response handling
  // ============================

  function handleResponse(key, source) {
    if (state.phase !== "running") return;
    if (state.currentResponse !== null) return;
    if (!state.responseTimerActive) return;  // ignore responses before audio ends
    if (key !== "1" && key !== "2") return;

    state.currentResponse = key;
    // RT measured from audio end time (when participant could first respond)
    state.currentResponseRT = nowMs() - state.targetAudioEndTime;
    const item = state.runs[state.currentRun][state.trialInRun - 1];
    logKeyEvent(item ? item.item_id : "", "target", key, source);
  }

  document.addEventListener("keydown", (e) => {
    if (state.phase === "paused" || state.paused) return;
    if (e.key === "1") {
      handleResponse("1", "keyboard");
    } else if (e.key === "2") {
      handleResponse("2", "keyboard");
    } else if (e.key === "Escape") {
      if (confirm("実験を中断して結果を保存しますか？")) {
        clearTimer();
        completeExperiment();
      }
    }
  });

  // ============================
  // Pause / resume
  // ============================

  function pauseExperiment() {
    if (state.paused) return;
    state.paused = true;
    clearTimer();
    $("#audio-prime").pause();
    $("#audio-target").pause();
    showScreen("paused");
  }

  function resumeExperiment() {
    if (!state.paused) return;
    state.paused = false;
    showScreen("running");
    // Resume by re-entering current phase (simplification: restart trial)
    if (state.pendingCallback) {
      const cb = state.pendingCallback;
      const delay = state.pendingDelay || 100;
      state.pendingCallback = null;
      state.pendingDelay = null;
      state.timerHandle = setTimeout(cb, delay);
    }
  }

  // ============================
  // CSV download
  // ============================

  function toCSV(rows) {
    if (rows.length === 0) return "";
    const headers = Object.keys(rows[0]);
    const escape = (v) => {
      if (v === null || v === undefined) return "";
      const s = String(v);
      if (/[",\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
      return s;
    };
    const lines = [headers.join(",")];
    for (const r of rows) {
      lines.push(headers.map(h => escape(r[h])).join(","));
    }
    return lines.join("\n");
  }

  function downloadCSV(filename, csvText) {
    const blob = new Blob([csvText], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  function renderResultsPreview() {
    const preview = $("#results-preview");
    if (state.results.length === 0) {
      preview.innerHTML = "<p>結果なし</p>";
      return;
    }
    const cols = [
      "run", "trial", "item_id", "family_id", "expected_response",
      "response", "response_correct", "rt_from_target_onset_ms"
    ];
    const rows = state.results.slice(0, 20);
    let html = "<table><thead><tr>";
    cols.forEach(c => html += `<th>${c}</th>`);
    html += "</tr></thead><tbody>";
    rows.forEach(r => {
      html += "<tr>";
      cols.forEach(c => {
        const v = r[c];
        html += `<td>${v == null ? "" : v}</td>`;
      });
      html += "</tr>";
    });
    html += "</tbody></table>";
    preview.innerHTML = html;
  }

  function renderSummary() {
    const summary = {};
    state.results.forEach(r => {
      const fam = r.family_id || "FILLER";
      if (!summary[fam]) summary[fam] = { n: 0, correct: 0, rt_sum: 0, rt_n: 0 };
      summary[fam].n += 1;
      if (r.response_correct === 1) {
        summary[fam].correct += 1;
        if (r.rt_from_target_onset_ms != null) {
          summary[fam].rt_sum += r.rt_from_target_onset_ms;
          summary[fam].rt_n += 1;
        }
      } else if (r.response_correct === 0) {
        if (r.rt_from_target_onset_ms != null) {
          summary[fam].rt_sum += r.rt_from_target_onset_ms;
          summary[fam].rt_n += 1;
        }
      }
    });
    const fams = Object.keys(summary).sort();
    let html = "<table><thead><tr><th>family</th><th>n</th><th>accuracy</th><th>mean RT (correct, ms)</th></tr></thead><tbody>";
    fams.forEach(f => {
      const s = summary[f];
      const acc = s.n > 0 ? (s.correct / s.n * 100).toFixed(1) + "%" : "—";
      const rt = s.rt_n > 0 ? (s.rt_sum / s.rt_n).toFixed(0) : "—";
      html += `<tr><td>${f}</td><td>${s.n}</td><td>${acc}</td><td>${rt}</td></tr>`;
    });
    html += "</tbody></table>";
    $("#summary-table").innerHTML = html;
  }

  function downloadResults() {
    const fname = `sub-${state.participant}_form-${state.listForm}_${state.sessionTimestamp}_results.csv`;
    downloadCSV(fname, toCSV(state.results));
  }

  function downloadEvents() {
    const fname = `sub-${state.participant}_form-${state.listForm}_${state.sessionTimestamp}_key_events.csv`;
    downloadCSV(fname, toCSV(state.keyEvents));
  }

  // ============================
  // Wire up
  // ============================

  // Auto-derive form on participant ID change
  $("#participant_id").addEventListener("input", (e) => {
    const id = e.target.value.trim();
    const hint = $("#form-hint");
    if (id) {
      const form = deriveForm(id);
      hint.textContent = `→ Form ${form} (自動割当)`;
    } else {
      hint.textContent = "";
    }
  });

  $("#setup-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    state.participant = $("#participant_id").value.trim() ||
      new Date().toISOString().replace(/[-:T.Z]/g, "").slice(0, 14);
    state.listForm = deriveForm(state.participant);
    state.presentationMode = $("#presentation_mode").value;

    // Override timings if changed
    TIMING.FIXATION_MS = parseInt($("#fixation_ms").value, 10);
    TIMING.PRIME_MAX_MS = parseInt($("#prime_max_ms").value, 10);
    TIMING.PAUSE_MS = parseInt($("#pause_ms").value, 10);
    TIMING.TARGET_MAX_MS = parseInt($("#target_max_ms").value, 10);
    TIMING.RESPONSE_WINDOW_MS = parseInt($("#response_window_ms").value, 10);
    TIMING.ITI_MIN_MS = parseInt($("#iti_min_ms").value, 10);
    TIMING.ITI_MAX_MS = parseInt($("#iti_max_ms").value, 10);

    state.sessionTimestamp =
      new Date().toISOString().replace(/[-:T.Z]/g, "").slice(0, 14);

    const ok = await loadStimuli();
    if (!ok) return;
    showScreen("instructions");
  });

  $("#start-experiment").addEventListener("click", () => {
    state.sessionStartTime = nowMs();
    state.currentRun = 1;
    state.trialInRun = 0;
    showScreen("running");
    setTrialText("+", { fixation: true });
    scheduleNext(() => {
      clearTrialText();
      startNextTrialOrEndOfRun();
    }, TIMING.INITIAL_REST_MS);
  });

  $("#next-run-btn").addEventListener("click", () => startNextRun());

  $("#resume-btn").addEventListener("click", () => resumeExperiment());

  $("#btn-yes").addEventListener("click", () => handleResponse("1", "button"));
  $("#btn-no").addEventListener("click", () => handleResponse("2", "button"));

  $("#download-results").addEventListener("click", downloadResults);
  $("#download-events").addEventListener("click", downloadEvents);
  $("#new-session").addEventListener("click", () => location.reload());

  // Init
  showScreen("setup");
})();
