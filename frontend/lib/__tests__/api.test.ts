import {
  clearToken,
  flagUrl,
  formatCountdown,
  formatKickoff,
  parseApiUtc,
  setToken,
  stageLabel,
} from "../api";

describe("parseApiUtc", () => {
  it("returns null for empty", () => {
    expect(parseApiUtc(null)).toBeNull();
    expect(parseApiUtc("")).toBeNull();
  });

  it("parses naive UTC as UTC", () => {
    const d = parseApiUtc("2026-06-21T18:00:00");
    expect(d).toBeInstanceOf(Date);
    expect(d!.getUTCFullYear()).toBe(2026);
  });

  it("accepts Z suffix", () => {
    const d = parseApiUtc("2026-06-21T18:00:00Z");
    expect(d).toBeInstanceOf(Date);
  });
});

describe("formatCountdown", () => {
  it("formats seconds only", () => {
    expect(formatCountdown(65)).toBe("1:05");
  });

  it("formats hours", () => {
    expect(formatCountdown(3661)).toBe("1:01:01");
  });

  it("formats days", () => {
    expect(formatCountdown(90000)).toMatch(/1d/);
  });

  it("zero when non-positive", () => {
    expect(formatCountdown(0)).toBe("0:00");
    expect(formatCountdown(-5)).toBe("0:00");
  });
});

describe("formatKickoff", () => {
  it("returns TBD for null", () => {
    expect(formatKickoff(null)).toBe("TBD");
  });

  it("returns a locale string for valid iso", () => {
    const s = formatKickoff("2026-06-21T18:00:00");
    expect(typeof s).toBe("string");
    expect(s.length).toBeGreaterThan(3);
  });
});

describe("parseApiUtc edge", () => {
  it("returns null for invalid date", () => {
    expect(parseApiUtc("not-a-date")).toBeNull();
  });

  it("accepts offset suffix", () => {
    const d = parseApiUtc("2026-06-21T18:00:00+00:00");
    expect(d).toBeInstanceOf(Date);
  });
});

describe("stageLabel", () => {
  it("maps known stages", () => {
    expect(stageLabel("group")).toBe("Fase de grupos");
    expect(stageLabel("final")).toBe("Final");
  });

  it("returns original for unknown", () => {
    expect(stageLabel("custom_stage")).toBe("custom_stage");
  });
});

describe("flagUrl", () => {
  it("builds cdn url", () => {
    expect(flagUrl("mx", 40)).toContain("mx");
  });

  it("empty for missing code", () => {
    expect(flagUrl("")).toBe("");
  });
});

describe("stageLabel", () => {
  it("maps known stages", () => {
    expect(stageLabel("group")).toBe("Fase de grupos");
    expect(stageLabel("final")).toBe("Final");
  });

  it("passthrough unknown", () => {
    expect(stageLabel("custom")).toBe("custom");
  });
});

describe("token storage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("setToken and clearToken", () => {
    setToken("abc");
    expect(localStorage.getItem("wc_token")).toBe("abc");
    clearToken();
    expect(localStorage.getItem("wc_token")).toBeNull();
  });
});
