import {
  Asset,
  Generation,
  HardwareInfo,
  Project,
  Provider,
  ProviderAccount,
  Scene,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
    if (typeof window !== "undefined") {
      localStorage.setItem("studio_token", token);
    }
  }

  getToken(): string | null {
    if (!this.token && typeof window !== "undefined") {
      this.token = localStorage.getItem("studio_token");
    }
    return this.token;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    const url = `${API_BASE}/api/v1${path}`;
    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let errDetail = `API error ${res.status}`;
      try {
        const data = await res.json();
        errDetail = data.detail || errDetail;
      } catch (e) {
        // ignore
      }
      throw new Error(errDetail);
    }

    if (res.status === 204) {
      return null as T;
    }

    return res.json();
  }

  // Auth
  async login(username: string = "admin", password: string = "admin123") {
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    const res = await fetch(`${API_BASE}/api/v1/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData.toString(),
    });

    if (res.ok) {
      const data = await res.json();
      this.setToken(data.access_token);
      return data;
    }
    return null;
  }

  // Projects
  async getProjects(): Promise<{ items: Project[]; total: number }> {
    try {
      return await this.request<{ items: Project[]; total: number }>("/projects/");
    } catch {
      return { items: [], total: 0 };
    }
  }

  async getProject(id: string): Promise<Project> {
    return this.request<Project>(`/projects/${id}`);
  }

  async createProject(data: Partial<Project>): Promise<Project> {
    return this.request<Project>("/projects/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updateProject(id: string, data: Partial<Project>): Promise<Project> {
    return this.request<Project>(`/projects/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async deleteProject(id: string): Promise<void> {
    return this.request<void>(`/projects/${id}`, { method: "DELETE" });
  }

  async generateStoryboard(projectId: string): Promise<{ scenes: Scene[]; script: string }> {
    return this.request(`/projects/${projectId}/generate-storyboard`, {
      method: "POST",
    });
  }

  // Generations
  async createGeneration(
    projectId: string,
    qualityMode: string = "balanced"
  ): Promise<Generation> {
    return this.request<Generation>("/generations/", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, quality_mode: qualityMode }),
    });
  }

  async getGeneration(id: string): Promise<Generation> {
    return this.request<Generation>(`/generations/${id}`);
  }

  async resumeGeneration(id: string): Promise<Generation> {
    return this.request<Generation>(`/generations/${id}/resume`, {
      method: "POST",
    });
  }

  async cancelGeneration(id: string): Promise<{ status: string }> {
    return this.request<{ status: string }>(`/generations/${id}/cancel`, {
      method: "POST",
    });
  }

  // Providers & Multi-Account Management
  async getProviders(): Promise<Provider[]> {
    try {
      return await this.request<Provider[]>("/providers/");
    } catch {
      return [];
    }
  }

  async getProviderAccounts(): Promise<ProviderAccount[]> {
    try {
      return await this.request<ProviderAccount[]>("/providers/accounts");
    } catch {
      return [];
    }
  }

  async createProviderAccount(data: {
    provider_id: string;
    account_name: string;
    api_key?: string;
    priority?: number;
    allow_paid_usage?: boolean;
    daily_spend_limit?: number;
    monthly_spend_limit?: number;
  }): Promise<ProviderAccount> {
    return this.request<ProviderAccount>("/providers/accounts", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updateProviderAccount(
    id: string,
    data: Partial<ProviderAccount> & { api_key?: string }
  ): Promise<ProviderAccount> {
    return this.request<ProviderAccount>(`/providers/accounts/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async deleteProviderAccount(id: string): Promise<void> {
    return this.request<void>(`/providers/accounts/${id}`, {
      method: "DELETE",
    });
  }

  async testProviderAccount(id: string): Promise<{
    success: boolean;
    latency_ms?: number;
    quota_status: string;
    message: string;
  }> {
    return this.request(`/providers/accounts/${id}/test`, {
      method: "POST",
    });
  }

  async getProviderUsageSummary(): Promise<any[]> {
    try {
      return await this.request<any[]>("/providers/usage-summary");
    } catch {
      return [];
    }
  }

  // System & Hardware
  async getHardware(): Promise<HardwareInfo> {
    try {
      return await this.request<HardwareInfo>("/system/hardware");
    } catch {
      return {
        os_name: "Darwin",
        os_version: "macOS",
        arch: "arm64",
        cpu_model: "Apple Silicon",
        cpu_cores: 8,
        ram_gb: 16.0,
        is_apple_silicon: true,
        gpu_name: "Apple Silicon Unified Memory",
        has_cuda: false,
        has_mps: true,
        available_disk_gb: 50.0,
        python_version: "3.11+",
        ffmpeg_available: true,
        comfyui_running: false,
        recommended_config: "Balanced Mode with API providers recommended.",
      };
    }
  }

  async getSystemStats(): Promise<any> {
    try {
      return await this.request<any>("/system/stats");
    } catch {
      return { total_projects: 0, total_generations: 0 };
    }
  }

  // Assets
  async uploadAsset(formData: FormData): Promise<Asset> {
    return this.request<Asset>("/assets/upload", {
      method: "POST",
      body: formData,
    });
  }

  async getAssets(projectId?: string): Promise<Asset[]> {
    try {
      const q = projectId ? `?project_id=${projectId}` : "";
      return await this.request<Asset[]>(`/assets/${q}`);
    } catch {
      return [];
    }
  }

  // Voice Studio
  async getLanguages(): Promise<any[]> {
    try {
      return await this.request<any[]>("/voice/languages");
    } catch {
      return [];
    }
  }

  async getVoices(): Promise<any[]> {
    try {
      return await this.request<any[]>("/voice/voices");
    } catch {
      return [];
    }
  }

  async previewVoice(text: string, language: string = "en"): Promise<any> {
    return this.request("/voice/preview", {
      method: "POST",
      body: JSON.stringify({ text, language }),
    });
  }
}

export const api = new ApiClient();
