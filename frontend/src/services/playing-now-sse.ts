import type { PlayingNowInfo } from './api';

type PlayingNowEventHandler = (data: PlayingNowInfo) => void;

export class PlayingNowSSE {
  private _es: EventSource | null = null;
  private _onEvent: PlayingNowEventHandler;

  constructor(onEvent: PlayingNowEventHandler) {
    this._onEvent = onEvent;
  }

  connect(): void {
    // EventSource reconnects automatically on network errors — no manual backoff needed.
    this._es = new EventSource('/api/playing-now/stream');
    this._es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as PlayingNowInfo;
        this._onEvent(data);
      } catch {
        // ignore malformed messages
      }
    };
  }

  close(): void {
    this._es?.close();
    this._es = null;
  }
}
