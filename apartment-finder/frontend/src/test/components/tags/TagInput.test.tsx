import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { TagInput } from '../../../components/tags/TagInput';

describe('TagInput', () => {
  it('renders tags', () => {
    render(<TagInput tags={['interested', 'favourite']} onChange={() => {}} />);
    expect(screen.getByText('interested')).toBeDefined();
    expect(screen.getByText('favourite')).toBeDefined();
  });

  it('adds a tag when selected from quick list', () => {
    const handleChange = vi.fn();
    render(<TagInput tags={[]} onChange={handleChange} />);
    
    // Quick list buttons are usually specific colors/text
    fireEvent.click(screen.getByText('favourite'));
    expect(handleChange).toHaveBeenCalledWith(['favourite']);
  });

  it('removes a tag when clicked', () => {
    const handleChange = vi.fn();
    render(<TagInput tags={['interested']} onChange={handleChange} />);
    
    fireEvent.click(screen.getByText('interested'));
    expect(handleChange).toHaveBeenCalledWith([]);
  });
});
