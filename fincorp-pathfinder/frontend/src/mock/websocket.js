// MockWebSocket mimics browser WebSocket API for liveness/consent/qa flows.
// When VITE_USE_MOCK is "false" and VITE_WS_BASE_URL is set, returns a real
// WebSocket instead. Otherwise the mock implementation runs as normal.
export class MockWebSocket {
  constructor(url) {
    const useMock = import.meta.env.VITE_USE_MOCK !== "false";
    const wsBase = import.meta.env.VITE_WS_BASE_URL;

    // Delegate to a real WebSocket when mock mode is off and a WS URL is set
    if (!useMock && wsBase) {
      const realUrl = url.replace(/^ws:\/\/[^/]+/, wsBase);
      return new WebSocket(realUrl);
    }

    this.url = url;
    this.readyState = 0;
    this._timers = [];
    this.onopen = null;
    this.onmessage = null;
    this.onclose = null;
    this.onerror = null;

    this._timers.push(
      setTimeout(() => {
        this.readyState = 1;
        this.onopen && this.onopen();
        this._run();
      }, 300),
    );
  }

  _emit(msg) {
    if (this.readyState !== 1) return;
    this.onmessage && this.onmessage({ data: JSON.stringify(msg) });
  }

  _at(t, fn) {
    this._timers.push(setTimeout(fn, t));
  }

  _close() {
    this.readyState = 3;
    this.onclose && this.onclose();
  }

  send(_data) {
    // no-op for mock
  }

  close() {
    this.readyState = 3;
    this._timers.forEach(clearTimeout);
    this._timers = [];
  }

  _run() {
    if (this.url.includes("liveness")) return this._runLiveness();
    if (this.url.includes("consent")) return this._runConsent();
    if (this.url.includes("qa")) return this._runQa();
  }

  _runLiveness() {
    for (let i = 0; i < 15; i++) {
      this._at(400 + i * 200, () =>
        this._emit({
          type: "frame_result",
          frame_index: i,
          face_detected: true,
          face_confidence: 0.93,
        }),
      );
    }
    this._at(4000, () =>
      this._emit({
        type: "liveness_result",
        liveness_score: 0.91,
        is_live: true,
        spoof_type: null,
        face_detected: true,
        face_confidence: 0.96,
        frames_analyzed: 15,
        estimated_age: 34,
        age_range: [29, 39],
        age_consistency_score: 0.88,
        active_challenge_required: false,
        hitl_required: false,
        challenge_passed: null,
        blinks_detected: null,
      }),
    );
    this._at(4200, () => this._close());
  }

  _runConsent() {
    this._at(200, () =>
      this._emit({
        type: "ready",
        consent_text:
          "I give my consent to Poonawalla Fincorp to record this video session, use my personal information for loan assessment, and verify my identity. I confirm I am providing this consent voluntarily.",
        instruction: "Please say 'I agree' or 'Yes, I consent' clearly.",
      }),
    );
    this._at(3500, () =>
      this._emit({ type: "transcript", text: "Yes I agree to give my consent", attempt: 1 }),
    );
    this._at(4800, () =>
      this._emit({
        type: "consent_result",
        is_valid: true,
        consent_confidence: 0.97,
        consent_hash: "a3f82b9c",
        timestamp: "2026-04-30T10:15:00.123456Z",
        replay_required: false,
        helpline_required: false,
      }),
    );
    this._at(5200, () => this._close());
  }

  _runQa() {
    const questions = [
      "Please state your full name and date of birth.",
      "What is your current home address including your PIN code?",
      "Are you salaried, self-employed, or a business owner?",
      "What is your approximate monthly take-home income or revenue?",
      "What is the name of your employer or business?",
      "What is the purpose of this loan?",
      "How much loan do you need, and for how long?",
      "Do you have any existing loan EMIs? How much per month?",
    ];
    const mockAnswers = [
      "My name is Ramesh Kumar, date of birth 15th March 1990",
      "42 Shivaji Nagar Pune Maharashtra PIN code 411005",
      "I am salaried working full time",
      "My monthly take-home is around 58 thousand rupees",
      "I work at TCS Tata Consultancy Services",
      "I need this loan for home renovation",
      "I am looking for 4 lakh rupees for 24 months",
      "I have one existing EMI of about 8 thousand per month",
    ];

    // Demo timing: 5s display + 8s answer = 13s/question -> 8 * 13 = 104s total
    const DISPLAY = 5000;
    const ANSWER = 8000;
    const CYCLE = DISPLAY + ANSWER;
    for (let n = 0; n < 8; n++) {
      const base = n * CYCLE;
      this._at(base + 0, () =>
        this._emit({
          type: "question",
          index: n,
          text: questions[n],
          phase: "display",
          display_seconds: DISPLAY / 1000,
          total_questions: 8,
        }),
      );
      this._at(base + DISPLAY, () =>
        this._emit({
          type: "question",
          index: n,
          text: questions[n],
          phase: "answer",
          timer_seconds: ANSWER / 1000,
        }),
      );
      this._at(base + DISPLAY + 800, () =>
        this._emit({
          type: "transcript_chunk",
          question_index: n,
          text: mockAnswers[n].slice(0, 15),
          is_final: false,
        }),
      );
      this._at(base + DISPLAY + 2000, () =>
        this._emit({
          type: "transcript_chunk",
          question_index: n,
          text: mockAnswers[n],
          is_final: true,
        }),
      );
      this._at(base + DISPLAY + ANSWER - 500, () =>
        this._emit({
          type: "extraction_result",
          index: n,
          fields: {},
          avg_confidence: 0.94,
          confidence_tier: "green",
        }),
      );
    }
    const t = 8 * CYCLE;
    this._at(t + 0, () => this._emit({ type: "processing", message: "Reading your answers..." }));
    this._at(t + 800, () =>
      this._emit({
        type: "pipeline_started",
        extraction_confidence_avg: 0.944,
        message: "Checking your eligibility...",
      }),
    );
    this._at(t + 1200, () => this._close());
  }
}
