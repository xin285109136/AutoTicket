'use client';

import { useState } from 'react';

interface SearchParams {
    origin: string;
    destination: string;
    date: string;
    adults: number;
    searchMode: 'scraper' | 'api';
}

export default function SearchForm({ onSearch }: { onSearch: (params: SearchParams) => void }) {
    const [params, setParams] = useState<SearchParams>({
        origin: '',
        destination: '',
        date: '',
        adults: 1,
        searchMode: 'scraper'
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

                {/* 日付 */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">日付</label>
                    <input
                        type="date"
                        value={params.date}
                        onChange={(e) => setParams({ ...params, date: e.target.value })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        required
                    />
                </div>

                {/* 検索ボタン */}
                <div className="flex items-end">
                    <button type="submit" className="w-full bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition font-medium">
                        検索
                    </button>
                </div>
            </div>

            {/* スクレイピングモード説明 */}
            {params.searchMode === 'scraper' && (
                <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
                    ℹ️ <strong>Webスクレイピングモード</strong>：ブラウザ画面が表示され、リアルタイムでデータ取得の様子を確認できます（5-10秒程度かかります）
                </div>
            )}
        </form>
    );
}
