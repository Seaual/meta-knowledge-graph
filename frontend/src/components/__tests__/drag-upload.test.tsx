import { render, screen } from "@testing-library/react";
import { describe, it, vi } from "vitest";

// Mock lucide-react icons
vi.mock("lucide-react", () => ({
  Upload: () => <span data-testid="upload-icon" />,
  Loader2: () => <span data-testid="loader-icon" />,
}));

// Mock API
vi.mock("../../lib/api", () => ({
  papersApi: { upload: vi.fn() },
}));

// Import after mocking
const DragUploadZone = (await import("../DragUploadZone")).default;

describe("DragUploadZone", () => {
  it("renders without crashing", () => {
    const { container } = render(
      <DragUploadZone
        onUploadSuccess={() => {}}
        onUploadError={() => {}}
      />
    );
    // Component returns null when not dragging/uploading
    expect(container.firstChild).toBeNull();
  });

  it("accepts required props", () => {
    // Verify the component accepts the correct prop types without crashing
    expect(() =>
      render(
        <DragUploadZone
          onUploadSuccess={() => {}}
          onUploadError={() => {}}
        />
      )
    ).not.toThrow();
  });
});
