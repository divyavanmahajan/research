import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ImportExport } from '../../../components/common/ImportExport';

const mockImportDb = vi.fn().mockReturnValue({ imported: 2, existing: 1 });
const mockShowToast = vi.fn();

vi.mock('../../../store/useAppStore', () => ({
  useAppStore: (selector: Function) => selector({
    apartments: [],
    savedSearches: [],
    importDb: mockImportDb,
    showToast: mockShowToast,
  }),
}));

vi.mock('../../../utils/db', () => ({
  DB_KEY: 'apartment-finder-db',
  CURRENT_VERSION: 1,
  DEFAULT_DB: { version: 1, exportedAt: null, apartments: [], savedSearches: [] },
  readDb: vi.fn(),
  writeDb: vi.fn(),
  migrateDb: vi.fn(),
}));

describe('ImportExport', () => {
  beforeEach(() => {
    mockImportDb.mockClear();
    mockShowToast.mockClear();
  });

  it('renders Export JSON and Import JSON buttons', () => {
    render(<ImportExport />);
    expect(screen.getByText('Export JSON')).toBeDefined();
    expect(screen.getByText('Import JSON')).toBeDefined();
  });

  it('triggers a file download on Export click', () => {
    const createObjectURL = vi.fn().mockReturnValue('blob:url');
    const revokeObjectURL = vi.fn();
    global.URL.createObjectURL = createObjectURL;
    global.URL.revokeObjectURL = revokeObjectURL;

    const clickMock = vi.fn();
    const origCreate = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation((tag) => {
      const el = origCreate(tag);
      if (tag === 'a') el.click = clickMock;
      return el;
    });

    render(<ImportExport />);
    fireEvent.click(screen.getByText('Export JSON'));

    expect(createObjectURL).toHaveBeenCalled();
    expect(clickMock).toHaveBeenCalled();
    vi.restoreAllMocks();
  });

  it('shows import mode dialog after a valid file is loaded', async () => {
    render(<ImportExport />);

    const validDb = JSON.stringify({ apartments: [{ id: '1' }], savedSearches: [], version: 1, exportedAt: null });
    const file = new File([validDb], 'backup.json', { type: 'application/json' });

    const input = screen.getByText('Import JSON').closest('label')!.querySelector('input')!;
    fireEvent.change(input, { target: { files: [file] } });

    await screen.findByText(/Import 1 apartment/);
    expect(screen.getByRole('button', { name: 'Merge' })).toBeDefined();
    expect(screen.getByRole('button', { name: 'Replace All' })).toBeDefined();
  });
});
