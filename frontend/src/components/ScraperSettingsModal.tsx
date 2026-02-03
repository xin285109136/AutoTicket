'use client';

import { useState, useEffect } from 'react';

interface ScraperSettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
    apiBase: string;
}

export default function ScraperSettingsModal({ isOpen, onClose, apiBase }: ScraperSettingsModalProps) {
    const [config, setConfig] = useState<any>(null);
    const [suggestion, setSuggestion] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (isOpen) {
            fetchConfig();
        }
    }, [isOpen]);

    const fetchConfig = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${apiBase}/scraper/config`);
            const data = await res.json();
            setConfig(data.config);
            setSuggestion(data.suggestion);
        } catch (e) {
            console.error(e);
            alert("Failed to load settings");
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async (newConfig: any) => {
        setSaving(true);
        try {
            const res = await fetch(`${apiBase}/scraper/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newConfig),
            });
            if (res.ok) {
                alert("Settings updated successfully!");
                onClose();
                // Refresh local data
                fetchConfig();
            } else {
                throw new Error("Update failed");
            }
        } catch (e) {
            alert("Failed to save settings");
        } finally {
            setSaving(false);
        }
    };

    const applySuggestion = () => {
        if (!config || !suggestion) return;
        const newConfig = {
            ...config,
            selectors: {
                ...config.selectors,
                ...suggestion
            }
        };
        handleSave(newConfig);
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                <div className="p-6 border-b flex justify-between items-center">
                    <h2 className="text-xl font-bold text-gray-800">🛠️ 爬虫高级设置 (Scraper Config)</h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
                </div>

                <div className="p-6">
                    {loading ? (
                        <p>Loading...</p>
                    ) : (
                        <div className="space-y-6">

                            {/* AI Suggestion Alert */}
                            {suggestion && (
                                <div className="bg-green-50 border border-green-200 rounded-lg p-4 animate-pulse">
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <h3 className="text-green-800 font-bold flex items-center gap-2">
                                                🧠 AI 自动修复建议可用 (Auto-Fix Available)
                                            </h3>
                                            <p className="text-sm text-green-700 mt-1">
                                                AI 检测到网页结构变化，并生成了新的 CSS 选择器。
                                            </p>
                                        </div>
                                        <button
                                            onClick={applySuggestion}
                                            disabled={saving}
                                            className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-bold shadow hover:bg-green-700 transition"
                                        >
                                            {saving ? "Applying..." : "✅ 一键应用 (Apply Fix)"}
                                        </button>
                                    </div>

                                    <div className="mt-3 bg-white p-3 rounded border text-xs font-mono overflow-x-auto">
                                        <pre>{JSON.stringify(suggestion, null, 2)}</pre>
                                    </div>
                                </div>
                            )}

                            {/* Current Settings Form */}
                            <div>
                                <h3 className="font-bold text-gray-700 mb-3">当前 CSS 选择器 (Current Selectors)</h3>
                                {config && config.selectors && (
                                    <div className="grid gap-4">
                                        {Object.entries(config.selectors).map(([key, value]) => (
                                            <div key={key}>
                                                <label className="block text-xs font-bold text-gray-500 uppercase mb-1">{key}</label>
                                                <input
                                                    type="text"
                                                    value={value as string}
                                                    onChange={(e) => setConfig({
                                                        ...config,
                                                        selectors: { ...config.selectors, [key]: e.target.value }
                                                    })}
                                                    className="w-full border rounded p-2 text-sm font-mono focus:ring-2 focus:ring-blue-500 outline-none"
                                                />
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div className="text-xs text-gray-400">
                                Last Updated: {config?.last_updated || 'Never'}
                            </div>
                        </div>
                    )}
                </div>

                <div className="p-6 border-t bg-gray-50 flex justify-end gap-3 rounded-b-xl">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-gray-600 hover:bg-gray-200 rounded-lg transition"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={() => handleSave(config)}
                        disabled={saving}
                        className="px-6 py-2 bg-blue-600 text-white font-bold rounded-lg shadow hover:bg-blue-700 transition"
                    >
                        {saving ? "Saving..." : "Save Changes"}
                    </button>
                </div>
            </div>
        </div>
    );
}
