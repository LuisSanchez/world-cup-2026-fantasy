import { render, screen } from "@testing-library/react";
import { Flag } from "../Flag";

describe("Flag", () => {
  it("renders placeholder without code", () => {
    render(<Flag code="" team="TBD" />);
    expect(screen.getByTitle("TBD")).toBeInTheDocument();
  });

  it("renders image with code", () => {
    render(<Flag code="mx" team="México" />);
    const img = screen.getByAltText("México");
    expect(img).toHaveAttribute("src", expect.stringContaining("flagcdn.com"));
    expect(img).toHaveAttribute("src", expect.stringContaining("mx"));
  });
});
