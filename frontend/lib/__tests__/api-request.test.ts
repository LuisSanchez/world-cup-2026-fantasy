import { api, clearToken, setToken } from "../api";

describe("api request layer", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    localStorage.clear();
    global.fetch = jest.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("health sends GET", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ status: "ok" }),
    });
    const r = await api.health();
    expect(r.status).toBe("ok");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/health"),
      expect.objectContaining({ headers: expect.any(Object) })
    );
  });

  it("attaches Authorization when token set", async () => {
    setToken("jwt-1");
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ id: 1, email: "a@b.com", name: "", picture: "", is_admin: false, total_points: 0 }),
    });
    await api.me();
    const opts = (global.fetch as jest.Mock).mock.calls[0][1];
    expect(opts.headers.Authorization).toBe("Bearer jwt-1");
  });

  it("throws on non-ok with detail", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 403,
      statusText: "Forbidden",
      json: async () => ({ detail: "Cannot edit" }),
    });
    await expect(api.savePrediction(1, 1, 0)).rejects.toThrow("Cannot edit");
  });

  it("throws on non-ok without json body", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Server Error",
      json: async () => {
        throw new Error("no json");
      },
    });
    await expect(api.leaderboard()).rejects.toThrow(/Server Error|HTTP 500/);
  });

  it("devLogin posts email", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ access_token: "t", user: { id: 1, email: "a@b.com", name: "", picture: "", is_admin: false, total_points: 0 } }),
    });
    const r = await api.devLogin("a@b.com");
    expect(r.access_token).toBe("t");
    const [url, opts] = (global.fetch as jest.Mock).mock.calls[0];
    expect(url).toContain("/api/auth/dev-login");
    expect(opts.method).toBe("POST");
  });

  it("matches with stage query", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({ ok: true, json: async () => [] });
    await api.matches("group");
    expect((global.fetch as jest.Mock).mock.calls[0][0]).toContain("stage=group");
  });

  it("admin and dashboard helpers", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({ ok: true, json: async () => ({}) });
    await api.googleAuthUrl();
    await api.myPredictions();
    await api.adminUsers();
    await api.adminUserPredictions(2);
    await api.adminSetScore(1, 2, 1);
    await api.adminUpdateMatch(1, { home_team: "X" });
    await api.adminSyncResults();
    await api.adminSyncStatus();
    await api.adminSetCronJobs(false);
    await api.dashboard();
    expect((global.fetch as jest.Mock).mock.calls.length).toBeGreaterThanOrEqual(9);
  });

  it("clearToken removes auth", () => {
    setToken("x");
    clearToken();
    expect(localStorage.getItem("wc_token")).toBeNull();
  });
});
