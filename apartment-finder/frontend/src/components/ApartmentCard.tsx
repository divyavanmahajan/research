import { Link } from 'react-router-dom';
import type { Apartment } from '../types';

const PRIORITY_STYLES: Record<string, string> = {
  must_see: 'bg-green-100 text-green-800',
  nice: 'bg-amber-100 text-amber-800',
  skip: 'bg-gray-100 text-gray-500',
  unranked: 'bg-gray-100 text-gray-400',
};

const PRIORITY_LABELS: Record<string, string> = {
  must_see: 'Must see',
  nice: 'Nice',
  skip: 'Skip',
  unranked: 'Unranked',
};

interface Props {
  apartment: Apartment;
}

export default function ApartmentCard({ apartment }: Props) {
  const { id, address, price, size, rooms, photos, priority, addedAt } = apartment;
  const added = new Date(addedAt).toLocaleDateString('sv-SE');

  return (
    <Link to={`/apartment/${id}`} className="block bg-white rounded-xl shadow hover:shadow-md transition-shadow overflow-hidden">
      <div className="h-36 bg-gray-100 overflow-hidden">
        {photos.length > 0 ? (
          <img src={photos[0]} alt={address} className="w-full h-full object-cover" />
        ) : (
          <div data-testid="no-photo" className="w-full h-full flex items-center justify-center text-gray-300 text-sm">
            No photo
          </div>
        )}
      </div>
      <div className="p-3 space-y-1">
        <p className="font-medium text-gray-900 text-sm truncate">{address}</p>
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>{price.toLocaleString('sv-SE')} kr/mån</span>
          <span>{size} m² · {rooms} rum</span>
        </div>
        <div className="flex items-center justify-between">
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PRIORITY_STYLES[priority] ?? PRIORITY_STYLES.unranked}`}>
            {PRIORITY_LABELS[priority] ?? 'Unranked'}
          </span>
          <span className="text-xs text-gray-400">{added}</span>
        </div>
      </div>
    </Link>
  );
}
