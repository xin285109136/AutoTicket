'use client';

import { useState } from 'react';

interface SearchParams {
    origin: string;
    destination: string;
    date: string;
    return_date?: string; // For round-trip
    adults: number;
    searchMode: 'scraper' | 'api';
    trip_type?: 'oneway' | 'roundtrip'; // 单程 or 往返
    time_range?: string;
    flexible_ticket?: boolean;
}

export default function SearchForm({ onSearch }: { onSearch: (params: SearchParams) => void }) {
    const [params, setParams] = useState<SearchParams>({
        origin: '',
        destination: '',
        date: '',
        return_date: undefined,
        adults: 1,
        searchMode: 'scraper',
        trip_type: 'oneway',
        time_range: undefined,
        flexible_ticket: false
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSearch(params);
    };

    return (
        <form onSubmit={handleSubmit} className="flex flex-wrap gap-4 p-4 bg-white shadow rounded-lg">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                {/* 検索モード */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">🔍 検索方式</label>
                    <select
                        value={params.searchMode}
                        onChange={(e) => setParams({ ...params, searchMode: e.target.value as 'scraper' | 'api' })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
                    >
                        <option value="scraper">🕷️ Webスクレイピング (可視化)</option>
                        <option value="api">🔌 API検索</option>
                    </select>
                </div>

                {/* 旅程类型 */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">✈️ 旅程タイプ</label>
                    <select
                        value={params.trip_type || 'oneway'}
                        onChange={(e) => setParams({ ...params, trip_type: e.target.value as 'oneway' | 'roundtrip' })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
                    >
                        <option value="oneway">片道 (One-way)</option>
                        <option value="roundtrip">往復 (Round-trip)</option>
                    </select>
                </div>

                {/* 出発地 */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">出発地</label>
                    <input
                        type="text"
                        placeholder="例: 東京, TYO"
                        value={params.origin}
                        onChange={(e) => setParams({ ...params, origin: e.target.value })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                </div>

                {/* 目的地 */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">目的地</label>
                    <input
                        type="text"
                        placeholder="例: 大阪, OSA"
                        value={params.destination}
                        onChange={(e) => setParams({ ...params, destination: e.target.value })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                </div>

                {/* 日付 (出発) */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        {params.trip_type === 'roundtrip' ? '出発日' : '日付'}
                    </label>
                    <input
                        type="date"
                        value={params.date}
                        onChange={(e) => setParams({ ...params, date: e.target.value })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        required
                    />
                </div>

                {/* 返回日期 (仅往返时显示) */}
                {params.trip_type === 'roundtrip' && (
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">復路日 (帰り)</label>
                        <input
                            type="date"
                            value={params.return_date || ''}
                            onChange={(e) => setParams({ ...params, return_date: e.target.value })}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            required={params.trip_type === 'roundtrip'}
                        />
                    </div>
                )}

                {/* 搜索按钮 */}
                <div className="flex items-end">
                    <button type="submit" className="w-full bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition font-medium">
                        検索
                    </button>
                </div>
            </div>

            {/* Scraper Advanced Options */}
            {params.searchMode === 'scraper' && (
                <div className="mt-3 pt-3 border-t border-gray-100 grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Time Range */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">⏱️ 時間帯 (Time)</label>
                        <select
                            value={params.time_range || ''}
                            onChange={(e) => setParams({ ...params, time_range: e.target.value || undefined })}
                            className="w-full px-4 py-2 border border-blue-200 rounded-lg bg-blue-50 text-sm"
                        >
                            <option value="">指定なし (Anytime)</option>
                            <option value="morning">午前 (Morning: ~12:00)</option>
                            <option value="afternoon">午後 (Afternoon: 12:00~18:00)</option>
                            <option value="evening">夜 (Evening: 18:00~)</option>
                        </select>
                    </div>

                    {/* Ticket Type */}
                    <div className="flex items-center pt-6">
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={params.flexible_ticket}
                                onChange={(e) => setParams({ ...params, flexible_ticket: e.target.checked })}
                                className="w-5 h-5 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                            />
                            <span className="text-sm font-medium text-gray-700">🎫 変更可能運賃 (Flexible Ticket)</span>
                        </label>
                    </div>
                </div>
            )}

            {/* Scraper Mode Explanation */}
            {params.searchMode === 'scraper' && (
                <div className="mt-2 text-xs text-gray-500">
                    ℹ️ ANA公式サイトからリアルタイムで検索します
                </div>
            )}
        </form>
    );
}
