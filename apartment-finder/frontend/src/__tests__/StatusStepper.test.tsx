import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import StatusStepper from '../components/StatusStepper';
import type { Status } from '../types';

describe('StatusStepper', () => {
  it('renders all status labels', () => {
    render(<StatusStepper value="new" onChange={() => {}} />);
    expect(screen.getByText(/new/i)).toBeInTheDocument();
    expect(screen.getByText(/contacted/i)).toBeInTheDocument();
    expect(screen.getByText(/viewing/i)).toBeInTheDocument();
    expect(screen.getByText(/applied/i)).toBeInTheDocument();
    expect(screen.getByText(/rejected/i)).toBeInTheDocument();
  });

  it('marks current status as active', () => {
    render(<StatusStepper value="viewing" onChange={() => {}} />);
    const active = screen.getByText(/viewing/i).closest('[data-status]');
    expect(active).toHaveAttribute('data-active', 'true');
  });

  it('calls onChange when a different status is clicked', async () => {
    const onChange = vi.fn<[Status], void>();
    render(<StatusStepper value="new" onChange={onChange} />);
    await userEvent.click(screen.getByText(/contacted/i));
    expect(onChange).toHaveBeenCalledWith('contacted');
  });

  it('does not call onChange when current status is clicked again', async () => {
    const onChange = vi.fn<[Status], void>();
    render(<StatusStepper value="new" onChange={onChange} />);
    await userEvent.click(screen.getByText(/new/i));
    expect(onChange).not.toHaveBeenCalled();
  });
});
