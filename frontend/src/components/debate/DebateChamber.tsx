import React from 'react';
import { Interactive3DChamber } from './Interactive3DChamber';

/**
 * Re-exporting Interactive3DChamber as DebateChamber for backwards compatibility
 * while fulfilling the signature 3D AI Debate Chamber specifications.
 */
export const DebateChamber: React.FC = () => {
  return <Interactive3DChamber />;
};

export default DebateChamber;
