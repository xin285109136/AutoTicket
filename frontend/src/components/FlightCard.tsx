'use client';

// Update Interface
interface Segment {
    departure_iata: string;
    arrival_iata: string;
    departure_time: string;
    arrival_time: string;
    carrier_code: string;
    flight_number: string;
    duration_minutes: number;
    // New Fields
    aircraft?: string;
    terminal?: string;
    seats_available?: number;
    cabin_class?: string;
}

interface Offer {
    id: string;
    price: number;
    currency: string;
    total_duration_minutes: number;
    stops: number;
    carrier_main: string;
    segments: Segment[];
    score: number;
    score_breakdown: Record<string, string>;
}

export default function FlightCard({ offer, exchangeRate }: { offer: Offer; exchangeRate: number }) {
    const formatTime = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Helper for rich data display
    const seg = offer.segments[0];
    const lastSeg = offer.segments[offer.segments.length - 1];

    // Price Logic
    const isEur = offer.currency === 'EUR';
    const displayPrice = isEur ? offer.price * exchangeRate : offer.price;
    const currencyLabel = isEur ? 'JPY (換算)' : offer.currency;

    return (
        <div className="border rounded-lg p-5 bg-white shadow-sm hover:shadow-md transition mb-3 flex flex-col md:flex-row justify-between items-center group relative overflow-hidden">
            {/* Left Border for best score visual could go here */}

            {/* Flight Info */}
            <div className="flex-1 w-full">
                {/* Header Line: Airline, Flight No, Tags */}
                <div className="flex items-center gap-3 mb-3">
                    <span className="font-bold text-xl text-blue-900">{offer.carrier_main}</span>
                    <span className="text-sm font-mono text-gray-500 bg-gray-100 px-2 py-0.5 rounded">{seg.flight_number}</span>

                    {offer.stops === 0 ? (
                        <span className="bg-emerald-100 text-emerald-700 text-xs px-2 py-0.5 rounded font-bold">直行便</span>
                    ) : (
                        <span className="bg-orange-100 text-orange-800 text-xs px-2 py-0.5 rounded">{offer.stops} 経由</span>
                    )}

                    {/* Rich Data Tags */}
                    {seg.aircraft && <span className="text-xs text-gray-500 border border-gray-200 px-1.5 rounded">✈️ {seg.aircraft}</span>}
                    {seg.seats_available && seg.seats_available <= 9 && (
                        <span className="text-xs text-red-600 bg-red-50 px-1.5 rounded">残席 {seg.seats_available}</span>
                    )}
                </div>

                {/* Main Time & Route */}
                <div className="flex items-center gap-8 mb-2">
                    <div className="text-center min-w-[80px]">
                        <div className="text-2xl font-bold text-gray-800">{formatTime(seg.departure_time)}</div>
                        <div className="text-gray-500 text-sm font-medium">
                            {seg.departure_iata} {seg.terminal && <span className="text-xs bg-gray-200 px-1 rounded ml-1">{seg.terminal}</span>}
                        </div>
                    </div>

                    <div className="flex-1 flex flex-col items-center">
                        <div className="text-xs text-gray-400 mb-1">
                            {Math.floor(offer.total_duration_minutes / 60)}h {offer.total_duration_minutes % 60}m
                        </div>
                        <div className="w-full h-[1px] bg-gray-300 relative">
                            <div className="absolute -top-1 right-0 text-gray-300">▶</div>
                        </div>
                        <div className="text-xs text-gray-400 mt-1">{seg.cabin_class || 'ECONOMY'}</div>
                    </div>

                    <div className="text-center min-w-[80px]">
                        <div className="text-2xl font-bold text-gray-800">{formatTime(lastSeg.arrival_time)}</div>
                        <div className="text-gray-500 text-sm font-medium">
                            {lastSeg.arrival_iata} {lastSeg.terminal && <span className="text-xs bg-gray-200 px-1 rounded ml-1">{lastSeg.terminal}</span>}
                        </div>
                    </div>
                </div>
            </div>

            {/* Price section */}
            <div className="flex flex-col items-end gap-1 mt-4 md:mt-0 md:pl-8 border-l-0 md:border-l border-gray-100 min-w-[140px]">
                <div className="text-3xl font-bold text-gray-900 tracking-tight">
                    ¥{displayPrice.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </div>
                {isEur && (
                    <div className="text-xs text-gray-500">
                        ({offer.price.toFixed(2)} EUR)
                    </div>
                )}
                {!isEur && <div className="text-xs text-gray-400">総額 (JPY)</div>}

                {offer.score && <div className="text-xs text-blue-400 mt-2 font-mono">Score: {offer.score?.toFixed(0)}</div>}
            </div>
        </div>
    );
}
