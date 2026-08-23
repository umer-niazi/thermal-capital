import { beforeEach, describe, expect, it } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  TEMPERATURE_STORAGE_KEY,
  TemperatureProvider,
  useTemperature,
} from "../context/TemperatureContext";

const TestConsumer: React.FC = () => {
  const { unit, setUnit, toggleUnit, formatTemp, formatDelta, formatRange } =
    useTemperature();
  return (
    <div>
      <span data-testid="unit">{unit}</span>
      <span data-testid="temp">{formatTemp(41.2)}</span>
      <span data-testid="delta">{formatDelta(2.2)}</span>
      <span data-testid="range">{formatRange(33.0, 41.0)}</span>
      <button onClick={() => setUnit("C")}>Set C</button>
      <button onClick={() => setUnit("F")}>Set F</button>
      <button onClick={toggleUnit}>Toggle</button>
    </div>
  );
};

describe("TemperatureContext & Provider", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("defaults to Fahrenheit ('F') when no preference is saved", () => {
    render(
      <TemperatureProvider>
        <TestConsumer />
      </TemperatureProvider>
    );

    expect(screen.getByTestId("unit").textContent).toBe("F");
    expect(screen.getByTestId("temp").textContent).toBe("106.2°F");
    expect(screen.getByTestId("delta").textContent).toBe("-4.0°F");
    expect(screen.getByTestId("range").textContent).toBe("91.4–105.8°F");
  });

  it("loads existing saved preference from localStorage", () => {
    localStorage.setItem(TEMPERATURE_STORAGE_KEY, "C");

    render(
      <TemperatureProvider>
        <TestConsumer />
      </TemperatureProvider>
    );

    expect(screen.getByTestId("unit").textContent).toBe("C");
    expect(screen.getByTestId("temp").textContent).toBe("41.2°C");
    expect(screen.getByTestId("delta").textContent).toBe("-2.2°C");
    expect(screen.getByTestId("range").textContent).toBe("33.0–41.0°C");
  });

  it("switches to Celsius on setUnit('C') and persists to localStorage", () => {
    render(
      <TemperatureProvider>
        <TestConsumer />
      </TemperatureProvider>
    );

    expect(screen.getByTestId("unit").textContent).toBe("F");

    fireEvent.click(screen.getByText("Set C"));

    expect(screen.getByTestId("unit").textContent).toBe("C");
    expect(screen.getByTestId("temp").textContent).toBe("41.2°C");
    expect(screen.getByTestId("delta").textContent).toBe("-2.2°C");
    expect(localStorage.getItem(TEMPERATURE_STORAGE_KEY)).toBe("C");
  });

  it("toggles between F and C and back to F", () => {
    render(
      <TemperatureProvider>
        <TestConsumer />
      </TemperatureProvider>
    );

    expect(screen.getByTestId("unit").textContent).toBe("F");

    fireEvent.click(screen.getByText("Toggle"));
    expect(screen.getByTestId("unit").textContent).toBe("C");
    expect(localStorage.getItem(TEMPERATURE_STORAGE_KEY)).toBe("C");

    fireEvent.click(screen.getByText("Toggle"));
    expect(screen.getByTestId("unit").textContent).toBe("F");
    expect(localStorage.getItem(TEMPERATURE_STORAGE_KEY)).toBe("F");
  });
});
