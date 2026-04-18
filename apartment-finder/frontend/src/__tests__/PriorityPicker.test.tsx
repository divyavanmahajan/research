import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import PriorityPicker from '../components/PriorityPicker';
import type { Priority } from '../types';

describe('PriorityPicker', () => {
  it('renders all three priority options', () => {
    render(<PriorityPicker value="unranked" onChange={() => {}} />);
    expect(screen.getByText(/must see/i)).toBeInTheDocument();
    expect(screen.getByText(/nice/i)).toBeInTheDocument();
    expect(screen.getByText(/skip/i)).toBeInTheDocument();
  });

  it('calls onChange with must_see when Must see is clicked', async () => {
    const onChange = vi.fn<[Priority], void>();
    render(<PriorityPicker value="unranked" onChange={onChange} />);
    await userEvent.click(screen.getByText(/must see/i));
    expect(onChange).toHaveBeenCalledWith('must_see');
  });

  it('calls onChange with nice when Nice is clicked', async () => {
    const onChange = vi.fn<[Priority], void>();
    render(<PriorityPicker value="unranked" onChange={onChange} />);
    await userEvent.click(screen.getByText(/nice/i));
    expect(onChange).toHaveBeenCalledWith('nice');
  });

  it('calls onChange with skip when Skip is clicked', async () => {
    const onChange = vi.fn<[Priority], void>();
    render(<PriorityPicker value="unranked" onChange={onChange} />);
    await userEvent.click(screen.getByText(/skip/i));
    expect(onChange).toHaveBeenCalledWith('skip');
  });

  it('highlights the current priority', () => {
    render(<PriorityPicker value="must_see" onChange={() => {}} />);
    const active = screen.getByText(/must see/i).closest('button');
    expect(active).toHaveAttribute('aria-pressed', 'true');
  });

  it('non-active buttons have aria-pressed false', () => {
    render(<PriorityPicker value="must_see" onChange={() => {}} />);
    const niceBtn = screen.getByText(/nice/i).closest('button');
    expect(niceBtn).toHaveAttribute('aria-pressed', 'false');
  });
});
