import React from 'react';
import { render, act } from '@testing-library/react';
import App from './App';
import { ThemeProvider } from './contexts/ThemeContext';
import axios from 'axios';

// Mock modules
jest.mock('axios', () => ({
  get: jest.fn(),
  post: jest.fn(),
}));
jest.mock('react-markdown', () => (props) => <div data-testid="markdown">{props.children}</div>);

// Mock ResizableLayout to spy on renders
const mockRenderSpy = jest.fn();
jest.mock('./components/ResizableLayout', () => ({
  ResizableLayout: ({ children }) => {
    mockRenderSpy();
    return <div data-testid="resizable-layout">{children}</div>;
  }
}));

// Mock URL APIs
global.URL.createObjectURL = jest.fn(() => 'mock-url');
global.URL.revokeObjectURL = jest.fn();

// Mock env
process.env.REACT_APP_BACKEND_URL = 'http://localhost:8000';

describe('App Performance Re-renders', () => {
  let originalConsoleLog;
  let originalConsoleError;

  beforeAll(() => {
     originalConsoleLog = console.log;
     originalConsoleError = console.error;
     console.log = jest.fn(); // Silence logs
     console.error = jest.fn();
  });

  afterAll(() => {
     console.log = originalConsoleLog;
     console.error = originalConsoleError;
  });

  beforeEach(() => {
    mockRenderSpy.mockClear();
    jest.useFakeTimers();
    axios.get.mockClear();
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  test('should verify re-render behavior on polling', async () => {
    const mockData = {
      blocks: { 1: { tool_type: 'test', block: 'code', feedback: 'ok', success: true } },
      done: false,
      answer: "Initial answer",
      agent_name: "Agent",
      status: "Idle",
      uid: "123"
    };

    // Setup axios mocks
    axios.get.mockImplementation((url) => {
      if (url.includes('latest_answer')) {
        return Promise.resolve({ data: mockData });
      }
      if (url.includes('health')) {
        return Promise.resolve({ status: 200 });
      }
      if (url.includes('screenshots')) {
        // Return a promise that never resolves to avoid state update from screenshot fetch
        return new Promise(() => {});
      }
      return Promise.resolve({ data: {} });
    });

    await act(async () => {
      render(
        <ThemeProvider>
          <App />
        </ThemeProvider>
      );
    });

    // Initial renders. React 18 strict mode might double render, but we can check the count.
    // Let's assume some initial renders happened.
    const initialRenderCount = mockRenderSpy.mock.calls.length;
    console.log(`Initial render count: ${initialRenderCount}`);

    // Advance time by 3000ms (one interval tick)
    await act(async () => {
      jest.advanceTimersByTime(3000);
    });

    // Advance time again to clear promises
    await act(async () => {
      // Need to wait for promises to resolve
      // We can use a small delay or loop
      // jest.advanceTimersByTime doesn't flush promises automatically
    });

    // In current implementation (without optimization), updateData is called -> setState -> Re-render.
    // So render count should increase.

    const countAfterFirstTick = mockRenderSpy.mock.calls.length;
    console.log(`Render count after 3s: ${countAfterFirstTick}`);

    // Advance another 3s
    await act(async () => {
      jest.advanceTimersByTime(3000);
    });

    const countAfterSecondTick = mockRenderSpy.mock.calls.length;
    console.log(`Render count after 6s: ${countAfterSecondTick}`);

    // If optimized, countAfterFirstTick should equal countAfterSecondTick (approximately, barring other effects).
    // If not optimized, it should increase by at least 1 per tick.

    // For the baseline test, we assert that it DOES increase (showing the problem).
    // Later we will change assertion to expect equality.

    // Just logging for now to inspect in the next step.
    // But to make the test "fail" on baseline if I were to assert optimization:
    // expect(countAfterSecondTick).toBe(countAfterFirstTick);

    // However, I want to use this test file for both baseline and verification.
    // I will write it to check the delta.

    const delta = countAfterSecondTick - countAfterFirstTick;
    console.log(`Delta per tick: ${delta}`);

    // Return the delta so I can see it in output?
    // Tests don't return values. I will rely on console logs or expect failure.

    // To confirm baseline failure, I will expect delta to be 0, so it fails if it's > 0.
    // This way I confirm the issue exists.
    expect(delta).toBe(0);
  });
});
