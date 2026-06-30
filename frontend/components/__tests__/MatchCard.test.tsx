import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MatchCard } from "../MatchCard";
import * as apiMod from "@/lib/api";

jest.mock("@/lib/api", () => {
  const actual = jest.requireActual("@/lib/api");
  return {
    ...actual,
    api: {
      savePrediction: jest.fn(),
      adminSetScore: jest.fn(),
    },
  };
});

jest.mock("../Flag", () => ({
  Flag: ({ team }: { team: string }) => <span>{team}</span>,
}));

jest.mock("../LockCountdown", () => ({
  LockCountdown: () => <div>countdown</div>,
}));

const baseMatch = {
  id: 1,
  match_number: 1,
  home_team: "México",
  away_team: "Sudáfrica",
  home_flag: "mx",
  away_flag: "za",
  kickoff: "2026-07-01T18:00:00",
  lock_at: "2026-07-01T17:50:00",
  stage: "group",
  group_name: "",
  home_score: null as number | null,
  away_score: null as number | null,
  is_finished: false,
  is_placeholder: false,
  status: "upcoming" as const,
  can_edit: true,
};

describe("MatchCard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders teams and save when editable", async () => {
    (apiMod.api.savePrediction as jest.Mock).mockResolvedValue({
      id: 1,
      match_id: 1,
      home_score: 1,
      away_score: 0,
      points_goals: 0,
      points_result: 0,
      points_total: 0,
    });
    render(<MatchCard match={baseMatch} prediction={null} />);
    expect(screen.getAllByText("México").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByText(/Guardar pronóstico/i));
    await waitFor(() => expect(apiMod.api.savePrediction).toHaveBeenCalled());
  });

  it("shows real score when finished", () => {
    render(
      <MatchCard
        match={{
          ...baseMatch,
          is_finished: true,
          home_score: 2,
          away_score: 0,
          status: "finished",
          can_edit: false,
        }}
        prediction={{
          id: 1,
          match_id: 1,
          home_score: 1,
          away_score: 0,
          points_goals: 0,
          points_result: 1,
          points_total: 1,
        }}
        readOnly
      />
    );
    expect(screen.getByText("2 – 0")).toBeInTheDocument();
  });

  it("admin mode publishes score", async () => {
    (apiMod.api.adminSetScore as jest.Mock).mockResolvedValue({ ...baseMatch, home_score: 1, away_score: 1 });
    render(<MatchCard match={baseMatch} readOnly adminMode />);
    fireEvent.click(screen.getByText(/Publicar resultado/i));
    await waitFor(() => expect(apiMod.api.adminSetScore).toHaveBeenCalled());
  });

  it("shows locked notice when not editable", () => {
    render(
      <MatchCard
        match={{ ...baseMatch, can_edit: false, status: "locked" }}
        prediction={{
          id: 1,
          match_id: 1,
          home_score: 0,
          away_score: 0,
          points_goals: 0,
          points_result: 0,
          points_total: 0,
        }}
      />
    );
    expect(screen.getByText(/Pronósticos cerrados/i)).toBeInTheDocument();
  });

  it("shows save error message", async () => {
    (apiMod.api.savePrediction as jest.Mock).mockRejectedValue(new Error("locked"));
    render(<MatchCard match={baseMatch} prediction={null} />);
    fireEvent.click(screen.getByText(/Guardar pronóstico/i));
    await waitFor(() => expect(screen.getByText("locked")).toBeInTheDocument());
  });

  it("shows non-Error save failure as Error", async () => {
    (apiMod.api.savePrediction as jest.Mock).mockRejectedValue("boom");
    render(<MatchCard match={baseMatch} prediction={null} />);
    fireEvent.click(screen.getByText(/Guardar pronóstico/i));
    await waitFor(() => expect(screen.getByText("Error")).toBeInTheDocument());
  });

  it("admin mode shows error on publish failure", async () => {
    (apiMod.api.adminSetScore as jest.Mock).mockRejectedValue(new Error("fail"));
    render(<MatchCard match={baseMatch} readOnly adminMode />);
    fireEvent.click(screen.getByText(/Publicar resultado/i));
    await waitFor(() => expect(screen.getByText("fail")).toBeInTheDocument());
  });

  it("updates score inputs", () => {
    render(<MatchCard match={baseMatch} prediction={null} />);
    const inputs = screen.getAllByRole("spinbutton");
    fireEvent.change(inputs[0], { target: { value: "3" } });
    fireEvent.change(inputs[1], { target: { value: "1" } });
    expect((inputs[0] as HTMLInputElement).value).toBe("3");
  });

  it("hides real score when showRealScore is false", () => {
    render(
      <MatchCard
        match={{
          ...baseMatch,
          is_finished: true,
          home_score: 2,
          away_score: 1,
          status: "finished",
          can_edit: false,
        }}
        prediction={null}
        showRealScore={false}
      />
    );
    expect(screen.queryByText("2 – 1")).not.toBeInTheDocument();
  });

  it("shows placeholder badge", () => {
    render(
      <MatchCard
        match={{ ...baseMatch, is_placeholder: true, home_team: "1A", away_team: "2B" }}
        prediction={null}
      />
    );
    expect(screen.getAllByText("1A").length).toBeGreaterThan(0);
  });

  it("renders live status label", () => {
    render(
      <MatchCard
        match={{ ...baseMatch, status: "live", can_edit: false }}
        prediction={null}
        readOnly
      />
    );
    expect(screen.getByText("En vivo")).toBeInTheDocument();
  });

  it("shows prediction points when finished", () => {
    render(
      <MatchCard
        match={{
          ...baseMatch,
          is_finished: true,
          home_score: 1,
          away_score: 0,
          status: "finished",
          can_edit: false,
        }}
        prediction={{
          id: 1,
          match_id: 1,
          home_score: 1,
          away_score: 0,
          points_goals: 2,
          points_result: 1,
          points_total: 3,
        }}
        readOnly
      />
    );
    expect(screen.getByText(/\+3 pts/i)).toBeInTheDocument();
  });

  it("calls onSaved after successful save", async () => {
    const onSaved = jest.fn();
    (apiMod.api.savePrediction as jest.Mock).mockResolvedValue({
      id: 1,
      match_id: 1,
      home_score: 0,
      away_score: 0,
      points_goals: 0,
      points_result: 0,
      points_total: 0,
    });
    render(<MatchCard match={baseMatch} prediction={null} onSaved={onSaved} />);
    fireEvent.click(screen.getByText(/Guardar pronóstico/i));
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
  });
});
