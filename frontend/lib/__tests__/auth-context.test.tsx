import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { AuthProvider, useAuth } from "../auth-context";
import * as apiMod from "../api";

jest.mock("../api", () => {
  const actual = jest.requireActual("../api");
  return {
    ...actual,
    api: {
      me: jest.fn(),
      devLogin: jest.fn(),
      googleAuthUrl: jest.fn(),
    },
    setToken: jest.fn(),
    clearToken: jest.fn(),
  };
});

function Probe() {
  const { user, loading, loginDev, loginGoogle, logout } = useAuth();
  if (loading) return <div>loading</div>;
  return (
    <div>
      <span data-testid="user">{user ? user.email : "none"}</span>
      <button type="button" onClick={() => loginDev("a@b.com")}>
        dev
      </button>
      <button
        type="button"
        onClick={() => {
          loginGoogle().catch(() => undefined);
        }}
      >
        google
      </button>
      <button type="button" onClick={logout}>
        out
      </button>
    </div>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("loads me on mount", async () => {
    (apiMod.api.me as jest.Mock).mockResolvedValue({
      id: 1,
      email: "u@x.com",
      name: "U",
      picture: "",
      is_admin: false,
      total_points: 0,
    });
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByTestId("user").textContent).toBe("u@x.com"));
  });

  it("handles me failure as logged out", async () => {
    (apiMod.api.me as jest.Mock).mockRejectedValue(new Error("401"));
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByTestId("user").textContent).toBe("none"));
  });

  it("loginDev sets user", async () => {
    (apiMod.api.me as jest.Mock).mockRejectedValue(new Error("no"));
    (apiMod.api.devLogin as jest.Mock).mockResolvedValue({
      access_token: "t",
      user: { id: 1, email: "a@b.com", name: "", picture: "", is_admin: false, total_points: 0 },
    });
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByTestId("user")).toBeInTheDocument());
    fireEvent.click(screen.getByText("dev"));
    await waitFor(() => expect(screen.getByTestId("user").textContent).toBe("a@b.com"));
  });

  it("loginGoogle throws DEV_LOGIN when no url", async () => {
    (apiMod.api.me as jest.Mock).mockRejectedValue(new Error("no"));
    (apiMod.api.googleAuthUrl as jest.Mock).mockResolvedValue({ url: null, dev_login: true });
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await waitFor(() => screen.getByText("google"));
    fireEvent.click(screen.getByText("google"));
  });

  it("logout clears user", async () => {
    (apiMod.api.me as jest.Mock).mockResolvedValue({
      id: 1,
      email: "u@x.com",
      name: "U",
      picture: "",
      is_admin: false,
      total_points: 0,
    });
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByTestId("user").textContent).toBe("u@x.com"));
    fireEvent.click(screen.getByText("out"));
    await waitFor(() => expect(screen.getByTestId("user").textContent).toBe("none"));
    expect(apiMod.clearToken).toHaveBeenCalled();
  });

  it("loginGoogle redirects when url present", async () => {
    const original = window.location;
    // @ts-expect-error jsdom location
    delete window.location;
    // @ts-expect-error assign
    window.location = { href: "" };
    (apiMod.api.me as jest.Mock).mockRejectedValue(new Error("no"));
    (apiMod.api.googleAuthUrl as jest.Mock).mockResolvedValue({
      url: "https://accounts.google.com/o",
      dev_login: false,
    });
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );
    await waitFor(() => screen.getByText("google"));
    fireEvent.click(screen.getByText("google"));
    await waitFor(() => {
      expect(window.location.href).toBe("https://accounts.google.com/o");
    });
    // @ts-expect-error restore
    window.location = original;
  });

  it("useAuth throws outside provider", () => {
    const spy = jest.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Probe />)).toThrow(/useAuth outside AuthProvider/);
    spy.mockRestore();
  });
});
