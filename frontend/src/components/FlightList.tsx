'use client';

import FlightCard from './FlightCard';

export default function FlightList({ offers, exchangeRate }: { offers: any[]; exchangeRate: number }) {
    if (!offers.length) return null;

    return (
        <div className="mt-8">
            <h2 className="text-xl font-bold mb-4 text-gray-800 flex items-center gap-2">
                <span>✈️</span>
                {offers.length} 便が見つかりました
            </h2>
            <div className="space-y-4">
                {offers.map((offer) => (
                    <FlightCard key={offer.id} offer={offer} exchangeRate={exchangeRate} />
                ))}
            </div>
        </div>
    );
}
