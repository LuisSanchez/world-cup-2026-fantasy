import { render, screen } from "@testing-library/react";
import { LockCountdown } from "../LockCountdown";

describe("LockCountdown", () => {
  it("shows TBD message when no lockAt and upcoming", () => {
    render(
      <LockCountdown lockAt={null} kickoff={null} status="upcoming" canEdit={true} />
    );
    expect(screen.getByText(/Sin hora de cierre/i)).toBeInTheDocument();
  });

  it("shows live message", () => {
    render(
      <LockCountdown
        lockAt="2026-06-21T17:50:00Z"
        kickoff="2026-06-21T18:00:00Z"
        status="live"
        canEdit={false}
      />
    );
    expect(screen.getByText(/En vivo/i)).toBeInTheDocument();
  });

  it("shows Cierra en when lock is in the future", () => {
    const future = new Date(Date.now() + 3600_000).toISOString();
    const kick = new Date(Date.now() + 4200_000).toISOString();
    render(
      <LockCountdown lockAt={future} kickoff={kick} status="upcoming" canEdit={true} />
    );
    expect(screen.getByText(/Cierra en/i)).toBeInTheDocument();
  });

  it("renders nothing for finished (countdown not shown)", () => {
    const { container } = render(
      <LockCountdown
        lockAt="2026-06-21T17:50:00Z"
        kickoff="2026-06-21T18:00:00Z"
        status="finished"
        canEdit={false}
      />
    );
    expect(container.textContent).toBe("");
  });

  it("shows locked status", () => {
    // kickoff still in future so locked branch is hit
    const kick = new Date(Date.now() + 3600_000).toISOString();
    const lock = new Date(Date.now() - 60_000).toISOString();
    render(
      <LockCountdown lockAt={lock} kickoff={kick} status="locked" canEdit={false} />
    );
    expect(screen.getByText(/Cerrado/i)).toBeInTheDocument();
  });

  it("calls onLockReached when lock time passed", () => {
    const onLock = jest.fn();
    const lock = new Date(Date.now() - 1000).toISOString();
    const kick = new Date(Date.now() + 3600_000).toISOString();
    render(
      <LockCountdown
        lockAt={lock}
        kickoff={kick}
        status="upcoming"
        canEdit={true}
        onLockReached={onLock}
      />
    );
    // lock already in the past; effect fires on mount
    expect(onLock).toHaveBeenCalled();
  });
});
