import { useState } from 'react';
import { createPortal } from 'react-dom';
import { v4 as uuidv4 } from 'uuid';
import { useAppStore } from '../../store/useAppStore';
import { geocodeAddress } from '../../api/qasaApi';
import type { QasaListingData } from '../../types';

interface Props {
  onClose: () => void;
}

export function AddManualForm({ onClose }: Props) {
  const addApartment = useAppStore(state => state.addApartment);
  const apartments = useAppStore(state => state.apartments);
  const showToast = useAppStore(state => state.showToast);
  const setActiveTab = useAppStore(state => state.setActiveTab);

  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    street: '',
    city: 'Göteborg',
    rent: '',
    sqm: '',
    rooms: '',
    availableFrom: '',   // YYYY-MM from <input type="month">
    description: '',
    photosUrl: '',
  });

  const set = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm(prev => ({ ...prev, [field]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const address = [form.street, form.city].filter(Boolean).join(', ');
      const { latitude, longitude } = await geocodeAddress(address);

      const data: QasaListingData = {
        id: `manual-${uuidv4()}`,
        rent: Number(form.rent),
        currency: 'SEK',
        squareMeters: Number(form.sqm),
        roomCount: form.rooms ? Number(form.rooms) : 1,
        floor: null,
        buildingFloors: null,
        tenureType: 'rental',
        rentalType: 'long_term',
        shared: false,
        description: form.description,
        publishedAt: new Date().toISOString(),
        status: 'normal',
        location: {
          id: '',
          latitude: latitude ?? 0,
          longitude: longitude ?? 0,
          locality: form.city,
          route: form.street,
          streetNumber: null,
          postalCode: '',
          countryCode: 'SE',
          country: 'Sverige',
        },
        uploads: [],
        duration: {
          startOptimal: form.availableFrom ? `${form.availableFrom}-01T00:00:00Z` : null,
          endOptimal: null,
          startAsap: !form.availableFrom,
          endUfn: true,
          possibilityOfExtension: false,
        },
        traits: [],
        landlord: { uid: 'manual', firstName: 'Manual entry', professional: false, premium: false },
        homeTemplates: [],
      };

      if (apartments.some(a => a.id === data.id)) {
        showToast('Already in your list', 'info');
      } else {
        addApartment(data, form.photosUrl);
        setActiveTab('mylist');
        showToast('Apartment added', 'success');
        onClose();
      }
    } catch {
      showToast('Failed to save — check required fields', 'error');
    } finally {
      setSaving(false);
    }
  };

  const label: React.CSSProperties = { fontSize: '0.75rem', fontWeight: 500, display: 'block', marginBottom: '0.25rem' };
  const row: React.CSSProperties = { marginBottom: '0.875rem' };
  const grid2: React.CSSProperties = { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.875rem' };

  return createPortal(
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 10000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      onClick={onClose}
    >
      <div
        style={{ background: 'var(--bg-card)', borderRadius: '0.75rem', padding: '1.5rem', width: '90%', maxWidth: '440px', boxShadow: 'var(--shadow-md)', maxHeight: '90vh', overflowY: 'auto' }}
        onClick={e => e.stopPropagation()}
      >
        <p style={{ fontWeight: 600, marginBottom: '1.25rem' }}>Add listing manually</p>

        <form onSubmit={handleSubmit}>
          <div style={row}>
            <label style={label}>Street address *</label>
            <input className="input-field" placeholder="Hjalmar Brantingsgatan 15B" value={form.street} onChange={set('street')} required />
          </div>

          <div style={row}>
            <label style={label}>City *</label>
            <input className="input-field" placeholder="Göteborg" value={form.city} onChange={set('city')} required />
          </div>

          <div style={grid2}>
            <div>
              <label style={label}>Rent (SEK) *</label>
              <input className="input-field" type="number" min="0" placeholder="14000" value={form.rent} onChange={set('rent')} required />
            </div>
            <div>
              <label style={label}>Size (m²) *</label>
              <input className="input-field" type="number" min="0" placeholder="50" value={form.sqm} onChange={set('sqm')} required />
            </div>
          </div>

          <div style={grid2}>
            <div>
              <label style={label}>Rooms</label>
              <input className="input-field" type="number" min="0" step="0.5" placeholder="2" value={form.rooms} onChange={set('rooms')} />
            </div>
            <div>
              <label style={label}>Available from</label>
              <input className="input-field" type="month" value={form.availableFrom} onChange={set('availableFrom')} />
            </div>
          </div>

          <div style={row}>
            <label style={label}>Description</label>
            <textarea
              className="input-field"
              rows={4}
              placeholder="Two room apartment, fully furnished…"
              value={form.description}
              onChange={set('description')}
              style={{ resize: 'vertical' }}
            />
          </div>

          <div style={row}>
            <label style={label}>Photos / listing URL</label>
            <input className="input-field" type="url" placeholder="https://www.dropbox.com/…" value={form.photosUrl} onChange={set('photosUrl')} />
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
            <button type="button" className="btn" style={{ flex: 1, background: 'var(--bg-app)' }} onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" style={{ flex: 1 }} disabled={saving}>
              {saving ? 'Saving…' : 'Add to list'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body,
  );
}
