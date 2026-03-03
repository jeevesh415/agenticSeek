import React from 'react';
import { render, act, screen } from '@testing-library/react';
import App from './App';
import { ThemeProvider } from './contexts/ThemeContext';
import axios from 'axios';

jest.mock('axios', () => ({
  get: jest.fn(),
  post: jest.fn(),
}));
jest.mock('react-markdown', () => (props) => {
  return <>{props.children}</>;
});

describe('App Performance Benchmark', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    global.URL.createObjectURL = jest.fn(() => 'mock-url');
    global.URL.revokeObjectURL = jest.fn();

    axios.get.mockImplementation((url) => {
      if (url.includes('/latest_answer')) {
        return Promise.resolve({ data: { answer: '', status: 'idle', done: false, blocks: {} } });
      }
      if (url.includes('/health')) {
        return Promise.resolve({ data: 'ok' });
      }
      if (url.includes('/screenshots')) {
         return Promise.resolve({ data: new Blob(['fake image'], { type: 'image/png' }) });
      }
      return Promise.resolve({ data: {} });
    });
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  test('Optimization Verified: does not fetch screenshot when in blocks view', async () => {
    render(
      <ThemeProvider>
        <App />
      </ThemeProvider>
    );

    // Advance time by 3100ms to trigger the first interval tick
    await act(async () => {
      jest.advanceTimersByTime(3100);
    });

    // Check if screenshot endpoint was called
    const screenshotCalls = axios.get.mock.calls.filter(call =>
      call[0].includes('/screenshots/updated_screen.png')
    );

    // Expect 0 calls (Optimization Success)
    expect(screenshotCalls.length).toBe(0);
  });

  test('Fetches screenshot when in screenshot view', async () => {
    render(
      <ThemeProvider>
        <App />
      </ThemeProvider>
    );

    // Switch to screenshot view
    const browserButton = screen.getByText('Browser View');
    await act(async () => {
      browserButton.click();
    });

    // Advance time by 3100ms
    await act(async () => {
      jest.advanceTimersByTime(3100);
    });

    const screenshotCalls = axios.get.mock.calls.filter(call =>
      call[0].includes('/screenshots/updated_screen.png')
    );

    expect(screenshotCalls.length).toBeGreaterThan(0);
  });
});
