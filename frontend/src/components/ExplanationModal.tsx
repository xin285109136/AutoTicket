'use client';

export default function ExplanationModal({ isOpen, onClose, text, usage, isLoading }: { isOpen: boolean; onClose: () => void; text: string; usage?: any; isLoading: boolean }) {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 animate-in fade-in zoom-in duration-200">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-bold flex items-center gap-2">
                        <span className="text-2xl">🤖</span> AI 分析
                    </h3>
                    {usage && (
                        <div className="text-xs text-right bg-blue-50 text-blue-700 px-2 py-1 rounded">
                            <div>消耗: {usage.total_tokens} Tokens</div>
                            <div className="font-bold">費用: ¥{usage.cost_jpy}</div>
                        </div>
                    )}
                </div>

                <div className="bg-gray-50 p-4 rounded-lg text-gray-700 min-h-[100px] leading-relaxed">
                    {isLoading ? (
                        <div className="space-y-2 animate-pulse">
                            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                            <div className="h-4 bg-gray-200 rounded w-full"></div>
                            <div className="h-4 bg-gray-200 rounded w-5/6"></div>
                        </div>
                    ) : (
                        text
                    )}
                </div>

                <div className="mt-6 flex justify-end">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 bg-gray-900 text-white rounded hover:bg-gray-700 transition"
                    >
                        閉じる
                    </button>
                </div>
            </div>
        </div>
    );
}
