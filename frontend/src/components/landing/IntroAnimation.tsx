import React from 'react';
import { AIReasoningIntro, AIReasoningIntroProps } from './intro/AIReasoningIntro';

export type IntroAnimationProps = AIReasoningIntroProps;

/**
 * Unified AI Debate Simulator Intro Experience
 * Encapsulates the next-generation 3D AI reasoning cinematic intro.
 */
export const IntroAnimation: React.FC<IntroAnimationProps> = (props) => {
  return <AIReasoningIntro {...props} />;
};

export default IntroAnimation;
