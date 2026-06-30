import { render, screen, waitFor } from "@testing-library/react";
import { AppShell } from "../AppShell";

const mockPush = jest.fn();
const mockReplace = jest.fn();
const mockUseAuth = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  usePathname: () => "/",
}));

jest.mock("@/lib/auth-context", () => ({
  useAuth: () => mockUseAuth(),
}));

jest.mock("../BottomNav", () => ({
  BottomNav: () => <nav data-testid="nav">nav</nav>,
}));

jest.mock("../ThemeToggle", () => ({
  ThemeToggle: () => <button type="button">theme</button>,
}));

describe("AppShell", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("shows loading", () => {
    mockUseAuth.mockReturnValue({ user: null, loading: true, logout: jest.fn() });
    render(
      <AppShell>
        <div>child</div>
      </AppShell>
    );
    expect(screen.getByText(/Cargando/i)).toBeInTheDocument();
  });

  it("redirects when unauthenticated", async () => {
    mockUseAuth.mockReturnValue({ user: null, loading: false, logout: jest.fn() });
    render(
      <AppShell>
        <div>child</div>
      </AppShell>
    );
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/login"));
  });

  it("renders children when authenticated", () => {
    mockUseAuth.mockReturnValue({
      user: { id: 1, email: "a@b.com", name: "A", picture: "", is_admin: true, total_points: 0 },
      loading: false,
      logout: jest.fn(),
    });
    render(
      <AppShell>
        <div>child-content</div>
      </AppShell>
    );
    expect(screen.getByText("child-content")).toBeInTheDocument();
    expect(screen.getByText("Admin")).toBeInTheDocument();
  });
});
