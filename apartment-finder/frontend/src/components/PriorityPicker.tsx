import type { Priority } from '../types';

interface Option {
  value: Priority;
  label: string;
  active: string;
  idle: string;
}

const OPTIONS: Option[] = [
  { value: 'must_see', label: 'Must see', active: 'bg-green-500 text-white', idle: 'bg-green-50 text-green-700 hover:bg-green-100' },
  { value: 'nice',     label: 'Nice',     active: 'bg-amber-400 text-white', idle: 'bg-amber-50 text-amber-700 hover:bg-amber-100' },
  { value: 'skip',     label: 'Skip',     active: 'bg-gray-400 text-white',  idle: 'bg-gray-100 text-gray-600 hover:bg-gray-200' },
];

interface Props {
  value: Priority;
  onChange: (value: Priority) => void;
}

export default function PriorityPicker({ value, onChange }: Props) {
  return (
    <div className="flex gap-2">
      {OPTIONS.map(opt => (
        <button
          key={opt.value}
          aria-pressed={value === opt.value ? 'true' : 'false'}
          onClick={() => onChange(opt.value)}
          className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${value === opt.value ? opt.active : opt.idle}`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
