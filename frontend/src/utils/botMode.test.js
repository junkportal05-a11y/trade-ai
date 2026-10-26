import { describe, it, expect } from 'vitest';
import { buildBotStartPayload } from './botMode';

describe('buildBotStartPayload', () => {
  it('always requests paper mode, regardless of caller', () => {
    expect(buildBotStartPayload()).toEqual({ paper: true });
  });
});
