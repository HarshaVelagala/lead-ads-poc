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

interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}

export class UnauthorizedError extends Error {
  constructor() {
    super("Unauthorized");
    this.name = "UnauthorizedError";
  }
}

function normalizeLead(value: ApiLead): Lead {
  return {
    id: value.mobile_id || value.meta_lead_id || String(value.id || ""),
    fullName: value.fullName || value.name || "Unknown lead",
    email: value.email || "",
    phone: value.phone || "",
    createdAt: value.createdAt || value.created_at || value.received_at || null,
  };
}

export async function login(email: string, password: string): Promise<string> {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Invalid email or password");
    }
    throw new Error(`Sign in failed (HTTP ${response.status})`);
  }
  const data = (await response.json()) as LoginResponse;
  if (!data.access_token || data.token_type !== "bearer") {
    throw new Error("The backend returned an invalid sign-in response");
  }
  return data.access_token;
}

export async function fetchLeads(token: string): Promise<Lead[]> {
  const response = await fetch(`${API_URL}/leads`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (response.status === 401) {
    throw new UnauthorizedError();
  }
  if (!response.ok) {
    throw new Error(`Backend returned HTTP ${response.status}`);
  }
  const data = (await response.json()) as ApiLead[];
  return data.map(normalizeLead);
}

async function fetchWebSocketTicket(token: string): Promise<string> {
  const response = await fetch(`${API_URL}/auth/ws-ticket`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (response.status === 401) {
    throw new UnauthorizedError();
  }
  if (!response.ok) {
    throw new Error(`Could not authorize live connection (HTTP ${response.status})`);
  }
  const data = (await response.json()) as LoginResponse;
  if (!data.access_token || data.token_type !== "bearer") {
    throw new Error("The backend returned an invalid live-connection ticket");
  }
  return data.access_token;
}

export function connectToLeadUpdates(
  token: string,
  onLead: (lead: Lead) => void,
  onState: (connected: boolean) => void,
  onUnauthorized: () => void,
): () => void {
  let active = true;
  let socket: WebSocket | undefined;
  let retryTimer: ReturnType<typeof setTimeout> | undefined;
  let retryDelay = 1000;
  let connecting = false;

  const connect = async () => {
    if (!active || connecting) return;
    connecting = true;
    let ticket: string;
    try {
      ticket = await fetchWebSocketTicket(token);
    } catch (error) {
      connecting = false;
      if (!active) return;
      if (error instanceof UnauthorizedError) {
        onUnauthorized();
        return;
      }
      onState(false);
      retryTimer = setTimeout(connect, retryDelay);
      retryDelay = Math.min(retryDelay * 2, 15000);
      return;
    }
    if (!active) {
      connecting = false;
      return;
    }
    socket = new WebSocket(`${WS_URL}?ticket=${encodeURIComponent(ticket)}`);
    socket.onopen = () => {
      connecting = false;
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
    socket.onclose = (event) => {
      connecting = false;
      if (active && event.code === 4401) {
        onUnauthorized();
      } else if (active) {
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