import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import AdvisoryBanner from './AdvisoryBanner';

describe('AdvisoryBanner Component', () => {
  it('renders mandatory safety protocol badges', () => {
    render(<AdvisoryBanner />);
    expect(screen.getByText('Mandatory Safety Protocol')).toBeDefined();
    expect(screen.getByText('Zero Auto-Execution Invariant')).toBeDefined();
  });

  it('renders default advisory disclaimer text', () => {
    render(<AdvisoryBanner />);
    expect(screen.getByText(/ADVISORY, requires qualified engineer review/i)).toBeDefined();
    expect(screen.getByText(/Never auto-execute/i)).toBeDefined();
  });

  it('renders custom advisory message when provided', () => {
    const customMsg = "Custom advisory notice: Physical lock-out mandatory before line reclosing.";
    render(<AdvisoryBanner message={customMsg} />);
    expect(screen.getByText(customMsg)).toBeDefined();
  });
});
