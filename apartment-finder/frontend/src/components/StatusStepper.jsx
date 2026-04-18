const STEPS = [
  { value: 'new',       label: 'New' },
  { value: 'contacted', label: 'Contacted' },
  { value: 'viewing',   label: 'Viewing' },
  { value: 'applied',   label: 'Applied' },
  { value: 'rejected',  label: 'Rejected' },
];

export default function StatusStepper({ value, onChange }) {
  const activeIndex = STEPS.findIndex(s => s.value === value);

  return (
    <div className="flex items-center gap-1 flex-wrap">
      {STEPS.map((step, i) => {
        const isPast = i < activeIndex;
        const isActive = step.value === value;
        return (
          <button
            key={step.value}
            data-status={step.value}
            data-active={isActive ? 'true' : 'false'}
            onClick={() => { if (!isActive) onChange(step.value); }}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              isActive  ? 'bg-blue-600 text-white' :
              isPast    ? 'bg-blue-100 text-blue-600' :
                          'bg-gray-100 text-gray-500 hover:bg-gray-200'
            }`}
          >
            {step.label}
          </button>
        );
      })}
    </div>
  );
}
