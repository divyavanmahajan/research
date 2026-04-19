import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MyList } from '../../../components/mylist/MyList';

const mockSetSelectedId = vi.fn();

const makeState = (apartments: any[]) => ({
  apartments,
  selectedApartmentId: null,
  setSelectedApartment: mockSetSelectedId,
});

vi.mock('../../../store/useAppStore', () => ({
  useAppStore: (selector: Function) => selector(makeState([])),
}));

vi.mock('../../../components/mylist/ApartmentCard', () => ({
  ApartmentCard: ({ apartment }: any) => <div data-testid="apt-card">{apartment.id}</div>,
}));

vi.mock('../../../components/mylist/ApartmentDetail', () => ({
  ApartmentDetail: () => null,
}));

vi.mock('../../../components/common/ImportExport', () => ({
  ImportExport: () => null,
}));

describe('MyList', () => {
  it('shows empty state when no apartments are saved', () => {
    render(<MyList />);
    expect(screen.getByText(/Your list is empty/)).toBeDefined();
  });
});
