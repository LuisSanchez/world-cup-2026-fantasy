import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ThemeProvider, useTheme } from "../theme-context";

function Probe() {
  const { theme, toggle, setTheme } = useTheme();
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <button type="button" onClick={toggle}>
        toggle
      </button>
      <button type="button" onClick={() => setTheme("light")}>
        light
      </button>
    </div>
  );
}

describe("ThemeProvider", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
  });

  it("provides theme and toggles", async () => {
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>
    );
    await waitFor(() => {
      expect(screen.getByTestId("theme")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("light"));
    await waitFor(() => {
      expect(screen.getByTestId("theme").textContent).toBe("light");
    });
    expect(localStorage.getItem("wc_theme")).toBe("light");
  });

  it("toggle switches dark to light", async () => {
    localStorage.setItem("wc_theme", "dark");
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>
    );
    await waitFor(() => expect(screen.getByTestId("theme").textContent).toBe("dark"));
    fireEvent.click(screen.getByText("toggle"));
    await waitFor(() => expect(screen.getByTestId("theme").textContent).toBe("light"));
  });

  it("reads stored light theme", async () => {
    localStorage.setItem("wc_theme", "light");
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>
    );
    await waitFor(() => expect(screen.getByTestId("theme").textContent).toBe("light"));
  });

  it("useTheme throws outside provider", () => {
    const spy = jest.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Probe />)).toThrow(/useTheme outside ThemeProvider/);
    spy.mockRestore();
  });
});
