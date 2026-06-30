import { render, screen, fireEvent } from "@testing-library/react";
import { ThemeProvider } from "@/lib/theme-context";
import { ThemeToggle } from "../ThemeToggle";

function renderToggle(compact = false) {
  return render(
    <ThemeProvider>
      <ThemeToggle compact={compact} />
    </ThemeProvider>
  );
}

describe("ThemeToggle", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
  });

  it("renders and toggles theme on click", () => {
    renderToggle();
    const btn = screen.getByRole("button");
    expect(btn).toBeInTheDocument();
    fireEvent.click(btn);
    const theme = document.documentElement.getAttribute("data-theme");
    expect(theme === "light" || theme === "dark").toBe(true);
  });

  it("compact mode has no text label Claro/Oscuro", () => {
    renderToggle(true);
    expect(screen.queryByText("Claro")).not.toBeInTheDocument();
    expect(screen.queryByText("Oscuro")).not.toBeInTheDocument();
  });
});
