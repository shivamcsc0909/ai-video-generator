"use client";

import { useEffect, useState } from "react";
import { FolderOpen, Upload, Trash2, Tag, Image as ImageIcon } from "lucide-react";
import { api } from "@/lib/api";
import { Asset } from "@/types";

export default function AssetsPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [purpose, setPurpose] = useState("general");

  useEffect(() => {
    loadAssets();
  }, []);

  async function loadAssets() {
    try {
      const data = await api.getAssets();
      setAssets(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("purpose", purpose);
    formData.append("asset_type", "reference_image");

    try {
      await api.uploadAsset(formData);
      await loadAssets();
    } catch (err: any) {
      alert(`Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-16">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Reference Assets & Media Library
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Upload character sheets, product CADs/photos, architectural concepts, style guides, and brand logos.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={purpose}
            onChange={(e) => setPurpose(e.target.value)}
            className="rounded-lg bg-surface border border-border px-3 py-2 text-xs text-slate-200"
          >
            <option value="character_reference">Character Reference</option>
            <option value="product_reference">Product Reference</option>
            <option value="architecture_reference">Architecture Reference</option>
            <option value="style_reference">Style Reference</option>
            <option value="general">General Media</option>
          </select>

          <label className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary hover:bg-primary-hover text-white text-xs font-bold cursor-pointer transition shadow-md shadow-primary/20">
            <Upload className="w-4 h-4" />
            <span>{uploading ? "Uploading..." : "Upload Image"}</span>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={handleFileUpload}
              disabled={uploading}
              className="hidden"
            />
          </label>
        </div>
      </div>

      {loading ? (
        <div className="py-20 text-center text-slate-500 text-sm">
          Loading media assets...
        </div>
      ) : assets.length === 0 ? (
        <div className="py-16 text-center text-slate-500 text-xs border border-dashed border-border rounded-2xl">
          No reference media uploaded yet. Upload reference images above for consistent character and product generations.
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {assets.map((asset) => (
            <div
              key={asset.id}
              className="group rounded-xl bg-surface border border-border overflow-hidden hover:border-blue-500/50 transition flex flex-col justify-between"
            >
              <div className="aspect-square bg-background flex items-center justify-center overflow-hidden relative">
                <img
                  src={asset.file_path.replace("./storage/assets", "/assets")}
                  alt={asset.original_filename}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  onError={(e) => {
                    (e.target as HTMLElement).style.display = "none";
                  }}
                />
              </div>
              <div className="p-3 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase font-bold text-accent-cyan tracking-wider truncate max-w-[120px]">
                    {asset.purpose.replace("_", " ")}
                  </span>
                  <span className="text-[10px] text-slate-500">
                    {Math.round(asset.file_size / 1024)} KB
                  </span>
                </div>
                <p className="text-xs font-semibold text-white truncate">
                  {asset.original_filename}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
