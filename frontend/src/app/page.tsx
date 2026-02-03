'use client';

import { useState } from 'react';
import SearchForm from '@/components/SearchForm';
import FlightList from '@/components/FlightList';
import ExplanationModal from '@/components/ExplanationModal';
import ScraperSettingsModal from '@/components/ScraperSettingsModal';

export default function Home() {
  const [offers, setOffers] = useState<any[]>([]);
  const [latency, setLatency] = useState(0);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [exchangeRate, setExchangeRate] = useState(162); // Default EUR->JPY

  // Settings State
  const [settingsOpen, setSettingsOpen] = useState(false);

  // Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [modalText, setModalText] = useState("");
  const [modalMeta, setModalMeta] = useState<any>(null); // New state for cost/tokens
  const [modalLoading, setModalLoading] = useState(false);
  const [warningMsg, setWarningMsg] = useState<string | null>(null);

  // Constants
  const API_BASE = "http://127.0.0.1:8001";

  const handleSearch = async (params: any) => {
    setLoading(true);
    setHasSearched(false);
    setOffers([]);
    setLatency(0);
    setWarningMsg(null);
    try {
      const res = await fetch(`${API_BASE}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      });
      if (!res.ok) throw new Error('Search failed');
      const data = await res.json();

      // Handle warning if present
      if (data.warning) {
        setWarningMsg(data.warning);
      }

      // Handle new structure { offers: [], latency_seconds: 0.123 }
      if (Array.isArray(data)) {
        setOffers(data);
      } else {
        setOffers(data.offers || []);
        setLatency(data.latency_seconds || 0);
      }
    } catch (e) {
      console.error(e);
      alert("Failed to fetch flight offers.");
    } finally {
      setLoading(false);
      setHasSearched(true);
    }
  };

  const handleAnalyze = async () => {
    if (offers.length === 0) return;
    setModalOpen(true);
    setModalLoading(true);
    setModalText("");
    setModalMeta(null); // Clear previous

    try {
      // Analyze current offers
      const res = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ offers: offers }),
      });
      const data = await res.json();
      setModalText(data.text || data.explanation || "No analysis returned");
      setModalMeta(data.usage);
    } catch (e) {
      console.error(e);
      setModalText("Failed to analyze flights.");
    } finally {
      setModalLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 p-8 font-sans">
      <div className="max-w-4xl mx-auto">
        <header className="mb-8 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-extrabold text-blue-900">✈️ AI エージェント航空券</h1>
            <p className="text-gray-600">ルールエンジンと AI を活用した ANA 航空券スマート検索</p>
          </div>
          <button
            onClick={() => setSettingsOpen(true)}
            className="text-gray-400 hover:text-gray-600 hover:rotate-90 transition transform p-2"
            title="Scraper Settings"
          >
            ⚙️
          </button>
        </header>

        {warningMsg && (
          <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-6 rounded shadow-sm">
            <div className="flex">
              <div className="flex-shrink-0">
                ⚠️
              </div>
              <div className="ml-3">
                <p className="text-sm text-yellow-700 font-bold">
                  AI Fallback Triggered (System Alert)
                </p>
                <div className="text-sm text-yellow-600">
                  {warningMsg}
                  <button
                    onClick={() => setSettingsOpen(true)}
                    className="block mt-2 font-bold underline hover:text-yellow-800"
                  >
                    👉 Click here to Review & Apply Fix
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="bg-white p-4 rounded-lg shadow-sm mb-6 flex items-center justify-between">
          <div className="text-sm font-bold text-gray-600">💱 汇率设定 (1 EUR = ? JPY)</div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={exchangeRate}
              onChange={(e) => setExchangeRate(Number(e.target.value))}
              className="border p-1 rounded w-20 text-right"
            />
            <span className="text-gray-500">JPY</span>
          </div>
        </div>

        <SearchForm onSearch={handleSearch} />

        {loading && (
          <div className="text-center mt-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-900 mx-auto"></div>
            <p className="mt-4 text-gray-500">世界のフライトシステムをスキャン中...</p>
          </div>
        )}

        {/* Action Bar & Stats */}
        {offers.length > 0 && !loading && (
          <div className="flex justify-between items-center mt-8 mb-2">
            {/* ... existing buttons ... */}
            <button
              onClick={handleAnalyze}
              className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-6 py-2 rounded-full shadow-lg hover:shadow-xl hover:scale-105 transition flex items-center gap-2 font-bold"
            >
              🤖 AI 全局分析 (Top 5)
            </button>

            {latency > 0 && (
              <div className="text-right text-xs text-gray-400">
                ⏱️ 検索完了: {latency}秒
              </div>
            )}
          </div>
        )}

        <FlightList offers={offers} exchangeRate={exchangeRate} />

        {/* Empty State */}
        {!loading && hasSearched && offers.length === 0 && (
          <div className="text-center mt-12 text-gray-400 bg-white p-8 rounded-lg border border-dashed border-gray-300">
            <div className="text-4xl mb-2">🤔</div>
            <p className="font-bold">条件に合うフライトが見つかりませんでした</p>
            <p className="text-sm mt-1">日付を変更するか、別の目的地を試してみてください。</p>
          </div>
        )}

        <ExplanationModal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          text={modalText}
          usage={modalMeta}
          isLoading={modalLoading}
        />

        {/* Settings Modal */}
        <ScraperSettingsModal
          isOpen={settingsOpen}
          onClose={() => setSettingsOpen(false)}
          apiBase={API_BASE}
        />
      </div>
    </main>
  );
}
