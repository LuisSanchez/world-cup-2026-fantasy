import { render, screen } from "@testing-library/react";
import { BottomNav } from "../BottomNav";

const mockUseAuth = jest.fn();
const mockUsePathname = jest.fn();

jest.mock("@/lib/auth-context", () => ({
  useAuth: () => mockUseAuth(),
}));

jest.mock("next/navigation", () => ({
  usePathname: () => mockUsePathname(),
}));

jest.mock("next/link", () => {
  return ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  );
});

describe("BottomNav", () => {
  beforeEach(() => {
    mockUsePathname.mockReturnValue("/");
  });

  it("renders main links", () => {
    mockUseAuth.mockReturnValue({ user: { is_admin: false } });
    render(<BottomNav />);
    expect(screen.getByText("Partidos")).toBeInTheDocument();
    expect(screen.getByText("Ranking")).toBeInTheDocument();
    expect(screen.getByText("Stats")).toBeInTheDocument();
    expect(screen.queryByText("Admin")).not.toBeInTheDocument();
  });

  it("shows admin for admin users", () => {
    mockUseAuth.mockReturnValue({ user: { is_admin: true } });
    mockUsePathname.mockReturnValue("/admin");
    render(<BottomNav />);
    expect(screen.getByText("Admin")).toBeInTheDocument();
  });
});
