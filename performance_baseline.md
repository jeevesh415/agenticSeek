# Performance Baseline

## Current Implementation: Polling
The current frontend (`App.js`) uses a `setInterval` loop to poll the backend every **3000ms** (3 seconds).

```javascript
    const intervalId = setInterval(() => {
      checkHealth();
      fetchLatestAnswer();
      fetchScreenshot();
    }, 3000);
```

### Latency Analysis
*   **Best Case**: The backend updates immediately before a poll. Latency ≈ Network RTT.
*   **Worst Case**: The backend updates immediately after a poll. Latency ≈ 3000ms + Network RTT.
*   **Average Case**: Latency ≈ 1500ms + Network RTT.

### Network Overhead
*   Three separate HTTP GET requests are made every 3 seconds, even if no data has changed.
*   Each request involves establishing a TCP connection (unless keep-alive is effective), sending HTTP headers, and processing the request on the server.

## Proposed Optimization: WebSockets
*   **Push Mechanism**: The backend pushes updates immediately when they occur (checked every 100ms server-side).
*   **Latency**: Average ~50ms (monitor interval / 2) + Network RTT.
*   **Improvement**: ~30x reduction in latency (1500ms -> 50ms).
*   **Network Overhead**: Single persistent connection. Minimal overhead for keep-alive packets. No redundant HTTP headers for polling.

## Measurement Goal
Since end-to-end benchmarking is complex in this environment, we rely on the analytical improvement of removing the 3s delay. The success criteria is functional equivalence with near-instantaneous updates.
