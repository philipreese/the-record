export type SyncEventType = 'sync_started' | 'sync_complete' | 'sync_error';

export interface SyncEvent {
  type: SyncEventType;
  mode?: string;
  inserted?: number;
  deleted?: number;
  message?: string;
}

type SyncEventHandler = (event: SyncEvent) => void;

const BACKOFF_MS = [1_000, 2_000, 4_000, 8_000, 16_000, 30_000];

export class SyncSocket {
  private ws: WebSocket | null = null;
  private _attempt = 0;
  private _closed = false;
  private _onEvent: SyncEventHandler;
  private _onOpen: (() => void) | null;

  constructor(onEvent: SyncEventHandler, onOpen?: () => void) {
    this._onEvent = onEvent;
    this._onOpen = onOpen ?? null;
  }

  connect(): void {
    this._closed = false;
    this._attempt = 0;
    this._open();
  }

  close(): void {
    this._closed = true;
    this.ws?.close();
    this.ws = null;
  }

  private _open(): void {
    if (this._closed) return;
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${proto}//${window.location.host}/api/ws/sync`;
    const ws = new WebSocket(url);
    this.ws = ws;

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as SyncEvent;
        this._onEvent(data);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      if (this._closed) return;
      const delay = BACKOFF_MS[Math.min(this._attempt, BACKOFF_MS.length - 1)];
      this._attempt++;
      setTimeout(() => this._open(), delay);
    };

    ws.onopen = () => {
      this._attempt = 0;
      this._onOpen?.();
    };
  }
}
