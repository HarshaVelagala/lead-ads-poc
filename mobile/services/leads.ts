import { API_URL, WS_URL } from "../config/backend";
import { Lead } from "../types/lead";

type ApiLead = Partial<Lead> & {
  id?: string | number;
  mobile_id?: string;
  meta_lead_id?: string | null;
  name?: string;
  createdAt?: string | null;
  created_at?: string | null;
  received_at?: string | null;
};

function normalizeLead(value: ApiLead): Lead {
  return {
    id: value.mobile_id || value.meta_lead_id || String(value.id || ""),
    fullName: value.fullName || value.name || "Unknown lead",
    email: value.email || "",
    phone: value.phone || "",
    createdAt: value.createdAt || value.created_at || value.received_at || null,
  };
}

export async function fetchLeads(): Promise<Lead[]> {
  const response = await fetch(`${API_URL}/leads`);
  if (!response.ok) {
    throw new Error(`Backend returned HTTP ${response.status}`);
  }
  const data = (await response.json()) as ApiLead[];
  return data.map(normalizeLead);
}

export function connectToLeadUpdates(
  onLead: (lead: Lead) => void,
  onState: (connected: boolean) => void,
): () => void {
  let active = true;
  let socket: WebSocket | undefined;
  let retryTimer: ReturnType<typeof setTimeout> | undefined;
  let retryDelay = 1000;

  const connect = () => {
    if (!active) return;
    socket = new WebSocket(WS_URL);
    socket.onopen = () => {
      retryDelay = 1000;
      onState(true);
    };
    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(String(event.data)) as {
          type?: string;
          data?: ApiLead;
        };
        if (message.type === "new_lead" && message.data?.id != null) {
          onLead(normalizeLead(message.data));
        }
      } catch {
        // Ignore malformed frames and keep the live connection available.
      }
    };
    socket.onerror = () => socket?.close();
    socket.onclose = () => {
      if (active) {
        onState(false);
        retryTimer = setTimeout(connect, retryDelay);
        retryDelay = Math.min(retryDelay * 2, 15000);
      }
    };
  };

  connect();
  return () => {
    active = false;
    if (retryTimer) clearTimeout(retryTimer);
    socket?.close();
  };
}