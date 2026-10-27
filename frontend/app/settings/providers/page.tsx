"use client";

import { useEffect, useState } from "react";
import {
  KeyRound,
  PlusCircle,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Trash2,
  Sliders,
  ShieldCheck,
  Zap,
  RotateCw,
  ExternalLink,
} from "lucide-react";
import { api } from "@/lib/api";
import { Provider, ProviderAccount } from "@/types";

export default function AIProvidersPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [accounts, setAccounts] = useState<ProviderAccount[]>([]);
  const [loading, setLoading] = useState(true);

  // Add Account Modal
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedProviderId, setSelectedProviderId] = useState("");
  const [accountName, setAccountName] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [priority, setPriority] = useState(1);
  const [allowPaid, setAllowPaid] = useState(false);
  const [dailyLimit, setDailyLimit] = useState("");
  const [testing, setTesting] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, any>>({});

  // Key Rotation Modal
  const [rotateAccountId, setRotateAccountId] = useState<string | null>(null);
  const [newKey, setNewKey] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [pList, aList] = await Promise.all([
        api.getProviders(),
        api.getProviderAccounts(),
      ]);
      setProviders(pList);
      setAccounts(aList);
      if (pList.length > 0 && !selectedProviderId) {
        setSelectedProviderId(pList[0].id);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function handleAddAccount(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedProviderId || !accountName.trim()) {
      alert("Please specify account name and provider.");
      return;
    }

    try {
      await api.createProviderAccount({
        provider_id: selectedProviderId,
        account_name: accountName.trim(),
        api_key: apiKey.trim() || undefined,
        priority: Number(priority),
        allow_paid_usage: allowPaid,
        daily_spend_limit: dailyLimit ? parseFloat(dailyLimit) : undefined,
      });

      setShowAddModal(false);
      setAccountName("");
      setApiKey("");
      setDailyLimit("");
      await loadData();
    } catch (err: any) {
      alert(`Failed to add account: ${err.message}`);
    }
  }

  async function handleTestConnection(accountId: string) {
    setTesting(accountId);
    try {
      const res = await api.testProviderAccount(accountId);
      setTestResults((prev) => ({ ...prev, [accountId]: res }));
      await loadData();
    } catch (err: any) {
      setTestResults((prev) => ({
        ...prev,
        [accountId]: { success: false, message: err.message },
      }));
    } finally {
      setTesting(null);
    }
  }

  async function handleDeleteAccount(accountId: string) {
    if (!confirm("Are you sure you want to remove this provider credential?")) return;
    try {
      await api.deleteProviderAccount(accountId);
      await loadData();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  }

  async function handleToggleActive(account: ProviderAccount) {
    try {
      await api.updateProviderAccount(account.id, {
        is_active: !account.is_active,
      });
      await loadData();
    } catch (err: any) {
      alert(`Update failed: ${err.message}`);
    }
  }

  async function handleRotateKey(e: React.FormEvent) {
    e.preventDefault();
    if (!rotateAccountId || !newKey.trim()) return;

    try {
      await api.updateProviderAccount(rotateAccountId, {
        api_key: newKey.trim(),
      });
      setRotateAccountId(null);
      setNewKey("");
      alert("Key rotated and encrypted successfully.");
      await loadData();
    } catch (err: any) {
      alert(`Rotation failed: ${err.message}`);
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-16">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 text-[11px] font-semibold mb-2">
            <ShieldCheck className="w-3.5 h-3.5 text-accent-emerald" />
            <span>Fernet Server-Side Encryption • At-Rest Security</span>
          </div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">
            AI Provider Credentials & Key Rotation
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Configure multiple accounts per provider (e.g. Gemini Personal vs Work). The router
            automatically rotates accounts upon rate limits (429) or quota exhaustion. Keys are never logged
            or exposed in the browser.
          </p>
        </div>

        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary hover:bg-primary-hover text-white text-xs font-bold shadow-lg shadow-primary/20 transition self-start"
        >
          <PlusCircle className="w-4 h-4" />
          <span>+ Add Provider Account</span>
        </button>
      </div>

      {/* Provider List grouped by Provider */}
      {loading ? (
        <div className="py-20 text-center text-slate-500 text-sm">
          Loading AI providers and encrypted credentials...
        </div>
      ) : (
        <div className="space-y-8">
          {providers.map((prov) => {
            const provAccounts = accounts.filter((a) => a.provider_id === prov.id);

            return (
              <div
                key={prov.id}
                className="rounded-2xl bg-surface border border-border overflow-hidden shadow-sm"
              >
                {/* Provider Card Header */}
                <div className="p-5 bg-surface-raised/60 border-b border-border flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-3">
                      <h3 className="text-base font-bold text-white">
                        {prov.display_name}
                      </h3>
                      <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                        {prov.provider_type}
                      </span>
                      {prov.supports_local ? (
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          100% Local Engine
                        </span>
                      ) : (
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-border">
                          Cloud API
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-400">
                      {prov.description}
                    </p>
                  </div>

                  <button
                    onClick={() => {
                      setSelectedProviderId(prov.id);
                      setShowAddModal(true);
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface border border-border hover:bg-surface-raised text-xs font-semibold text-slate-300 transition self-start"
                  >
                    <PlusCircle className="w-3.5 h-3.5 text-primary" />
                    <span>Add Key / Account</span>
                  </button>
                </div>

                {/* Accounts Table */}
                <div className="p-4">
                  {provAccounts.length === 0 ? (
                    <div className="py-6 text-center text-xs text-slate-500 italic">
                      No accounts configured. Click "+ Add Key / Account" to enable this provider.
                    </div>
                  ) : (
                    <div className="divide-y divide-border/60">
                      {provAccounts.map((acc) => {
                        const testRes = testResults[acc.id];
                        const isTesting = testing === acc.id;

                        return (
                          <div
                            key={acc.id}
                            className="py-4 flex flex-col lg:flex-row lg:items-center justify-between gap-4"
                          >
                            <div className="space-y-1.5">
                              <div className="flex items-center gap-3">
                                <span className="font-bold text-sm text-white">
                                  {acc.account_name}
                                </span>
                                <span className="font-mono text-xs px-2 py-0.5 rounded bg-background border border-border text-slate-400">
                                  {acc.key_hint || "************"}
                                </span>

                                {/* Status Tag */}
                                {acc.cooldown_until && new Date(acc.cooldown_until) > new Date() ? (
                                  <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center gap-1">
                                    <Clock className="w-3 h-3" />
                                    <span>Rate Limited (Cooldown)</span>
                                  </span>
                                ) : acc.is_healthy ? (
                                  <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                                    <CheckCircle2 className="w-3 h-3" />
                                    <span>Healthy</span>
                                  </span>
                                ) : (
                                  <span className="text-[10px] px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/30 flex items-center gap-1">
                                    <XCircle className="w-3 h-3" />
                                    <span>Error / Disabled</span>
                                  </span>
                                )}

                                <span className="text-xs text-slate-500">
                                  Priority: #{acc.priority}
                                </span>
                              </div>

                              <div className="flex items-center gap-4 text-xs text-slate-400">
                                <span>Requests Today: {acc.daily_request_count}</span>
                                <span>Success Count: {acc.success_count}</span>
                                {acc.last_error_message && (
                                  <span className="text-red-400 truncate max-w-md">
                                    Last error: {acc.last_error_message}
                                  </span>
                                )}
                              </div>

                              {testRes && (
                                <div
                                  className={`text-xs mt-1 font-medium ${
                                    testRes.success ? "text-emerald-400" : "text-red-400"
                                  }`}
                                >
                                  {testRes.message} {testRes.latency_ms ? `(${testRes.latency_ms}ms)` : ""}
                                </div>
                              )}
                            </div>

                            {/* Action Buttons */}
                            <div className="flex items-center gap-2 self-start lg:self-center">
                              <button
                                onClick={() => handleTestConnection(acc.id)}
                                disabled={isTesting}
                                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-raised hover:bg-background border border-border text-xs text-slate-300 font-medium transition"
                              >
                                <RefreshCw className={`w-3.5 h-3.5 ${isTesting ? "animate-spin" : ""}`} />
                                <span>{isTesting ? "Testing..." : "Test Connection"}</span>
                              </button>

                              {!prov.supports_local && (
                                <button
                                  onClick={() => setRotateAccountId(acc.id)}
                                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-raised hover:bg-background border border-border text-xs text-slate-300 font-medium transition"
                                >
                                  <RotateCw className="w-3.5 h-3.5 text-accent-cyan" />
                                  <span>Rotate Key</span>
                                </button>
                              )}

                              <button
                                onClick={() => handleToggleActive(acc)}
                                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                                  acc.is_active
                                    ? "bg-slate-800 text-slate-300 border-border hover:bg-slate-700"
                                    : "bg-emerald-600/10 text-emerald-400 border-emerald-500/30"
                                }`}
                              >
                                {acc.is_active ? "Disable" : "Enable"}
                              </button>

                              <button
                                onClick={() => handleDeleteAccount(acc.id)}
                                className="p-1.5 rounded-lg hover:bg-red-500/10 text-slate-500 hover:text-red-400 transition"
                                title="Delete account"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add Account Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface border border-border rounded-2xl max-w-md w-full p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="font-bold text-base text-white">
                Add AI Provider Credential
              </h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-slate-400 hover:text-white text-xs font-semibold"
              >
                Cancel
              </button>
            </div>

            <form onSubmit={handleAddAccount} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Target Provider</label>
                <select
                  value={selectedProviderId}
                  onChange={(e) => setSelectedProviderId(e.target.value)}
                  className="w-full rounded-lg bg-surface-raised border border-border px-3 py-2 text-slate-200"
                >
                  {providers.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.display_name} ({p.supports_local ? "Local" : "Cloud"})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Account Label</label>
                <input
                  type="text"
                  value={accountName}
                  onChange={(e) => setAccountName(e.target.value)}
                  placeholder="e.g. Gemini Personal or Groq Work"
                  className="w-full rounded-lg bg-surface-raised border border-border px-3 py-2 text-slate-200"
                  required
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">
                  API Key Secret (Encrypted Server-Side)
                </label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Enter provider API key"
                  className="w-full rounded-lg bg-surface-raised border border-border px-3 py-2 text-slate-200"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  Encrypted using Fernet 256-bit at rest. Only the last 4 characters are kept as a hint.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Priority (1 = Highest)</label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={priority}
                    onChange={(e) => setPriority(Number(e.target.value))}
                    className="w-full rounded-lg bg-surface-raised border border-border px-3 py-2 text-slate-200"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Daily Spend Limit ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={dailyLimit}
                    onChange={(e) => setDailyLimit(e.target.value)}
                    placeholder="Optional"
                    className="w-full rounded-lg bg-surface-raised border border-border px-3 py-2 text-slate-200"
                  />
                </div>
              </div>

              <label className="flex items-center gap-2 cursor-pointer pt-1">
                <input
                  type="checkbox"
                  checked={allowPaid}
                  onChange={(e) => setAllowPaid(e.target.checked)}
                  className="rounded bg-surface-raised border-border text-primary"
                />
                <span className="text-slate-300">Allow Paid API Usage</span>
              </label>

              <div className="pt-3 border-t border-border flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-lg bg-surface-raised text-slate-300 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-lg bg-primary hover:bg-primary-hover text-white font-bold"
                >
                  Save & Encrypt
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Rotate Key Modal */}
      {rotateAccountId && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface border border-border rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h3 className="font-bold text-base text-white">
              Rotate API Key
            </h3>
            <p className="text-xs text-slate-400">
              Enter your replacement API key. The new key will be encrypted and replace the previous credential immediately.
            </p>

            <form onSubmit={handleRotateKey} className="space-y-4 text-xs">
              <input
                type="password"
                value={newKey}
                onChange={(e) => setNewKey(e.target.value)}
                placeholder="New API key"
                className="w-full rounded-lg bg-surface-raised border border-border p-3 text-slate-200"
                required
              />
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setRotateAccountId(null)}
                  className="px-4 py-2 rounded-lg bg-surface-raised text-slate-300 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-lg bg-primary hover:bg-primary-hover text-white font-bold"
                >
                  Update Key
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
