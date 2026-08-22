/**
 * SAFECAM AI — Live Session Audio Alert Service
 * Manages MP3 alarm sound playback for confirmed bullying events.
 * 
 * STRICT RULES:
 * 1. Sound plays ONLY during an active Live Monitoring session (activeSessionId != null).
 * 2. Sound plays ONLY for NEW live bullying incidents created AFTER the live session started.
 * 3. Sound plays ONCE on state transition (NORMAL -> BULLYING_CONFIRMED) and loops while incident continues.
 * 4. Sound STOPS immediately when user leaves Live Monitoring, live session ends, or incident ends.
 * 5. Historical database alerts or alerts from other pages NEVER trigger sound.
 */

class AudioAlertService {
  constructor() {
    this.audioElement = null;
    this.sirenOscillator = null;
    this.sirenGain = null;
    this.sirenTimer = null;
    this.audioContext = null;

    this.activeSessionId = null;
    this.liveSessionStartTime = 0;
    this.lastPlayedIncidentId = null;
    this.isPlaying = false;

    this.initAudioElement();
    this.setupGlobalUnlockListener();
  }

  initAudioElement() {
    try {
      this.audioElement = new Audio("/sounds/bullying-alert.mp3");
      this.audioElement.loop = true;
    } catch (e) {
      console.warn("[AUDIO SERVICE] Could not initialize HTML5 audio element:", e);
    }
  }

  setupGlobalUnlockListener() {
    const unlock = () => {
      try {
        if (!this.audioContext) {
          const AudioCtx = window.AudioContext || window.webkitAudioContext;
          this.audioContext = new AudioCtx();
        }
        if (this.audioContext && this.audioContext.state === "suspended") {
          this.audioContext.resume();
        }
      } catch (e) {}

      window.removeEventListener("click", unlock);
      window.removeEventListener("keydown", unlock);
      window.removeEventListener("touchstart", unlock);
    };

    window.addEventListener("click", unlock, { once: true });
    window.addEventListener("keydown", unlock, { once: true });
    window.addEventListener("touchstart", unlock, { once: true });
  }

  /**
   * Starts a new active live monitoring session.
   * Called when LiveMonitoring page mounts or CCTV live stream starts.
   */
  startLiveSession(sessionId) {
    this.activeSessionId = sessionId || `SESSION-${Date.now()}`;
    this.liveSessionStartTime = Date.now() - 3000; // 3s margin for network clocks
    this.lastPlayedIncidentId = null;
    console.log(`[AUDIO SERVICE] Live Monitoring session STARTED: ${this.activeSessionId}`);
    return this.activeSessionId;
  }

  /**
   * Ends current live monitoring session and immediately stops any sound.
   * Called when user leaves Live Monitoring, disconnects stream, or unmounts.
   */
  endLiveSession() {
    if (this.activeSessionId) {
      console.log(`[AUDIO SERVICE] Live Monitoring session ENDED: ${this.activeSessionId}`);
    }
    this.activeSessionId = null;
    this.liveSessionStartTime = 0;
    this.lastPlayedIncidentId = null;
    this.stopAlarmSound();
  }

  /**
   * Triggers MP3 alarm ONLY if all strict live conditions are met:
   * 1. Live Monitoring is active (activeSessionId != null)
   * 2. Incident started AFTER the live session started
   * 3. Incident is NEW (has not already started playing sound)
   */
  playBullyingAlarm(incidentId, startedAtIso, sessionId) {
    // Rule 1: Must be inside an active live session
    if (!this.activeSessionId) {
      return;
    }

    // Rule 2: Session ID must match
    if (sessionId && sessionId !== this.activeSessionId) {
      return;
    }

    // Rule 3: Must be a NEW incident during this live session (Do NOT restart every frame)
    if (incidentId && incidentId === this.lastPlayedIncidentId && this.isPlaying) {
      return;
    }

    // Rule 4: Must be created DURING current live session or recent live incident (Ignore old historical database alerts)
    if (startedAtIso) {
      try {
        let incidentTime = new Date(startedAtIso).getTime();
        const now = Date.now();
        // If parsed without timezone offset, check difference from now
        const isRecentLiveAlert = !isNaN(incidentTime) && (
          incidentTime >= (this.liveSessionStartTime - 10000) ||
          Math.abs(now - incidentTime) < 120000
        );

        if (!isRecentLiveAlert) {
          console.log(`[AUDIO SERVICE] Ignored historical alert created before session start: ${incidentId}`);
          return;
        }
      } catch (e) {}
    }

    this.lastPlayedIncidentId = incidentId;
    this.isPlaying = true;

    console.log(`[AUDIO SERVICE] 🚨 TRIGGERING MP3 ALARM for new live incident: ${incidentId}`);

    // Play HTML5 Audio element
    if (this.audioElement) {
      this.audioElement.currentTime = 0;
      const playPromise = this.audioElement.play();
      if (playPromise !== undefined) {
        playPromise
          .then(() => {
            console.log("[AUDIO SERVICE] Playing /sounds/bullying-alert.mp3 successfully.");
          })
          .catch((err) => {
            console.warn("[AUDIO SERVICE] Audio play blocked by browser policy, falling back to Web Audio siren:", err.message);
            this.playWebAudioSiren();
          });
      }
    } else {
      this.playWebAudioSiren();
    }
  }

  playWebAudioSiren() {
    try {
      if (!this.audioContext) {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        this.audioContext = new AudioCtx();
      }
      if (this.audioContext.state === "suspended") {
        this.audioContext.resume().catch(() => {});
      }

      this.stopWebAudioSiren();

      this.sirenOscillator = this.audioContext.createOscillator();
      this.sirenGain = this.audioContext.createGain();

      this.sirenOscillator.type = "sawtooth";
      this.sirenOscillator.frequency.setValueAtTime(880, this.audioContext.currentTime);

      this.sirenGain.gain.setValueAtTime(0.20, this.audioContext.currentTime);
      this.sirenOscillator.connect(this.sirenGain);
      this.sirenGain.connect(this.audioContext.destination);

      this.sirenOscillator.start();

      let toggle = false;
      this.sirenTimer = setInterval(() => {
        if (!this.sirenOscillator || !this.audioContext) return;
        const now = this.audioContext.currentTime;
        const targetFreq = toggle ? 880 : 660;
        this.sirenOscillator.frequency.setTargetAtTime(targetFreq, now, 0.05);
        toggle = !toggle;
      }, 350);
    } catch (err) {
      console.warn("[AUDIO SERVICE] Web Audio siren error:", err);
    }
  }

  stopWebAudioSiren() {
    if (this.sirenTimer) {
      clearInterval(this.sirenTimer);
      this.sirenTimer = null;
    }
    if (this.sirenOscillator) {
      try {
        this.sirenOscillator.stop();
        this.sirenOscillator.disconnect();
      } catch (e) {}
      this.sirenOscillator = null;
    }
  }

  stopAlarmSound() {
    this.isPlaying = false;
    if (this.audioElement) {
      try {
        this.audioElement.pause();
        this.audioElement.currentTime = 0;
      } catch (e) {}
    }
    this.stopWebAudioSiren();
    console.log("[AUDIO SERVICE] Alarm sound STOPPED.");
  }
}

export const audioAlertService = new AudioAlertService();
export default audioAlertService;
