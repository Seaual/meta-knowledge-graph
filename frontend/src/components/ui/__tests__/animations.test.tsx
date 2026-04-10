import { render, screen } from "@testing-library/react";
import { FadeContent } from "../animations";

// Mock IntersectionObserver for jsdom
class MockIntersectionObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
window.IntersectionObserver = MockIntersectionObserver;

describe("FadeContent", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders children", () => {
    render(<FadeContent>Test Content</FadeContent>);
    expect(screen.getByText("Test Content")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    render(<FadeContent className="custom-class">Styled</FadeContent>);
    expect(screen.getByText("Styled")).toHaveClass("custom-class");
  });
});
