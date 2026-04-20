"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { X, Monitor, Save, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

type Status = "connecting" | "started" | "saving" | "auth_saved" | "cancelled" | "error" | "closed";

interface RemoteLoginModalProps {
  open: boolean;
  onClose: () => void;
  onAuthSaved?: () => void;
}

/** Build a WebSocket URL pointing at the backend's remote-login endpoint. */
function getWsUrl(): string {
  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "/api";
  // Convert http(s) to ws(s)
  if (apiBase.startsWith("http")) {
    const url = new URL(apiBase);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    // remote-login is mounted directly on /api/auth/remote-login
    url.pathname = "/api/auth/remote-login";
    // Add user_id from localStorage for WebSocket auth
    const userId = typeof window !== "undefined" ? localStorage.getItem("user_id") : null;
    if (userId) url.searchParams.set("user_id", userId);
    return url.toString();
  }
  // Relative path — derive from current window location
  const loc = typeof window !== "undefined" ? window.location : null;
  if (!loc) return "ws://localhost:8000/api/auth/remote-login";
  const proto = loc.protocol === "https:" ? "wss:" : "ws:";
  const userId = localStorage.getItem("user_id") ?? "";
  return `${proto}//${loc.host}/api/auth/remote-login?user_id=${userId}`;
}

const KEY_MAP: Record<string, string> = {
  Enter: "Enter",
  Tab: "Tab",
  Backspace: "Backspace",
  Delete: "Delete",
  Escape: "Escape",
  ArrowUp: "ArrowUp",
  ArrowDown: "ArrowDown",
  ArrowLeft: "ArrowLeft",
  ArrowRight: "ArrowRight",
  Home: "Home",
  End: "End",
  PageUp: "PageUp",
  PageDown: "PageDown",
};

export default function RemoteLoginModal({ open, onClose, onAuthSaved }: RemoteLoginModalProps) {
  const [status, setStatus] = useState<Status>("connecting");
  const [statusMsg, setStatusMsg] = useState("接続中...");
  const [imgSrc, setImgSrc] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const viewportRef = useRef({ width: 1280, height: 800 });
  const containerRef = useRef<HTMLDivElement>(null);
  const statusRef = useRef<Status>("connecting");

  // Connect WebSocket
  useEffect(() => {
    if (!open) return;

    const updateStatus = (s: Status) => {
      statusRef.current = s;
      setStatus(s);
    };

    updateStatus("connecting");
    setStatusMsg("ブラウザに接続中...");
    setImgSrc(null);

    const wsUrl = getWsUrl();
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      updateStatus("connecting");
      setStatusMsg("ブラウザを起動中...");
    };

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "screenshot") {
          setImgSrc(`data:image/png;base64,${msg.data}`);
          if (statusRef.current === "connecting") updateStatus("started");
        } else if (msg.type === "viewport") {
          viewportRef.current = { width: msg.width, height: msg.height };
        } else if (msg.type === "status") {
          setStatusMsg(msg.message ?? msg.status);
          if (msg.status === "started") updateStatus("started");
          else if (msg.status === "saving") updateStatus("saving");
          else if (msg.status === "auth_saved") {
            updateStatus("auth_saved");
            onAuthSaved?.();
          } else if (msg.status === "cancelled") updateStatus("cancelled");
          else if (msg.status === "error") updateStatus("error");
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onerror = () => {
      console.warn("[RemoteLogin] WebSocket error", { url: wsUrl });
      updateStatus("error");
      setStatusMsg("WebSocket接続エラー");
    };

    ws.onclose = (ev) => {
      console.warn("[RemoteLogin] WebSocket closed", {
        url: wsUrl,
        code: ev.code,
        reason: ev.reason,
      });
      const cur = statusRef.current;
      if (cur !== "auth_saved" && cur !== "cancelled" && cur !== "error") {
        updateStatus("closed");
        setStatusMsg("接続が切断されました");
      }
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
      wsRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  /** Send a JSON message over WebSocket */
  const send = useCallback((msg: Record<string, unknown>) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
    }
  }, []);

  /** Convert mouse event coords to browser viewport coords */
  const toViewportCoords = useCallback(
    (e: React.MouseEvent<HTMLImageElement>) => {
      const img = imgRef.current;
      if (!img) return null;
      const rect = img.getBoundingClientRect();
      const scaleX = viewportRef.current.width / rect.width;
      const scaleY = viewportRef.current.height / rect.height;
      return {
        x: (e.clientX - rect.left) * scaleX,
        y: (e.clientY - rect.top) * scaleY,
      };
    },
    [],
  );

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLImageElement>) => {
      const coords = toViewportCoords(e);
      if (!coords) return;
      send({ action: "click", x: coords.x, y: coords.y, button: e.button === 2 ? "right" : "left" });
    },
    [send, toViewportCoords],
  );


  /** Capture keyboard events on the container */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      e.preventDefault();
      e.stopPropagation();

      const mapped = KEY_MAP[e.key];
      if (mapped) {
        send({ action: "keypress", key: mapped });
      } else if (e.key.length === 1) {
        send({ action: "type", text: e.key });
      }
    },
    [send],
  );

  const handleSave = useCallback(() => {
    send({ action: "save" });
    setStatus("saving");
    setStatusMsg("認証情報を保存中...");
  }, [send]);

  const handleCancel = useCallback(() => {
    send({ action: "cancel" });
    onClose();
  }, [send, onClose]);

  if (!open) return null;

  const isActive = status === "started" || status === "connecting";
  const isDone = status === "auth_saved" || status === "cancelled";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative flex flex-col bg-background rounded-2xl shadow-2xl border border-border w-[95vw] max-w-[1360px] max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-muted/30">
          <div className="flex items-center gap-2">
            <Monitor className="size-4 text-primary" />
            <span className="text-sm font-semibold text-foreground">Remote NotebookLM Login</span>
            <span className="text-xs text-muted-foreground ml-2">— {statusMsg}</span>
          </div>
          <button
            onClick={handleCancel}
            className="size-8 rounded-lg flex items-center justify-center hover:bg-muted transition-colors"
            aria-label="Close"
          >
            <X className="size-4" />
          </button>
        </div>

        {/* Browser viewport */}
        <div
          ref={containerRef}
          className="flex-1 overflow-auto bg-white flex items-center justify-center focus:outline-none"
          tabIndex={0}
          onKeyDown={handleKeyDown}
        >
          {imgSrc ? (
            <img
              ref={imgRef}
              src={imgSrc}
              alt="Remote browser"
              className="max-w-full max-h-[70vh] object-contain cursor-pointer select-none"
              onClick={handleClick}
              onContextMenu={(e) => {
                e.preventDefault();
                handleClick(e);
              }}
              draggable={false}
            />
          ) : (
            <div className="flex flex-col items-center gap-3 py-20 text-muted-foreground">
              <Loader2 className="size-8 animate-spin" />
              <p className="text-sm">{statusMsg}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-3 border-t border-border bg-muted/30">
          <p className="text-xs text-muted-foreground max-w-[60%]">
            Googleにログインしたら「保存」を押してください。画面をクリック・キー入力でブラウザを操作できます。
          </p>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={handleCancel}
              disabled={status === "saving"}
            >
              {isDone ? "閉じる" : "キャンセル"}
            </Button>
            {isActive && (
              <Button
                size="sm"
                onClick={handleSave}
                disabled={status === "connecting"}
                className="gap-1.5"
              >
                <Save className="size-3.5" />
                保存
              </Button>
            )}
            {status === "saving" && (
              <Button size="sm" disabled className="gap-1.5">
                <Loader2 className="size-3.5 animate-spin" />
                保存中...
              </Button>
            )}
            {status === "auth_saved" && (
              <Button size="sm" onClick={onClose} className="gap-1.5">
                完了
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
