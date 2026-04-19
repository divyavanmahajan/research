import { useAppStore } from '../../store/useAppStore';

export function Toast() {
  const toasts = useAppStore(state => state.toasts);
  const dismissToast = useAppStore(state => state.dismissToast);

  if (toasts.length === 0) return null;

  return (
    <div style={{
      position: 'fixed',
      bottom: '1.5rem',
      left: '50%',
      transform: 'translateX(-50%)',
      zIndex: 9999,
      display: 'flex',
      flexDirection: 'column',
      gap: '0.5rem',
      alignItems: 'center',
      pointerEvents: 'none',
    }}>
      {toasts.map(toast => (
        <div
          key={toast.id}
          role="alert"
          onClick={() => dismissToast(toast.id)}
          style={{
            padding: '0.75rem 1.25rem',
            borderRadius: '0.5rem',
            color: 'white',
            fontSize: '0.875rem',
            cursor: 'pointer',
            maxWidth: '420px',
            textAlign: 'center',
            pointerEvents: 'auto',
            boxShadow: 'var(--shadow-md)',
            backgroundColor:
              toast.type === 'error' ? 'var(--tag-red)' :
              toast.type === 'success' ? 'var(--tag-green)' :
              'var(--primary)',
          }}
        >
          {toast.message}
        </div>
      ))}
    </div>
  );
}
