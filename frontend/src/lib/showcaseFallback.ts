import { ShowcaseDebate } from '../types/debate';

/**
 * Curated illustrative debate examples used strictly as fallback
 * when no qualifying completed debates exist in the database.
 * 
 * Rules:
 * - isReal: false
 * - No fabricated document names, citations, page numbers, or scores.
 * - Clearly distinguished from real historical debates.
 */
export const ILLUSTRATIVE_SHOWCASE_DEBATES: ShowcaseDebate[] = [
  {
    id: 'illustrative-ai-employment',
    topic: 'Will generative AI systems cause widespread net technological unemployment across knowledge-work sectors?',
    createdAt: 'Preview Dataset',
    documentName: null,
    documentId: null,
    isReal: false,
    roundsCount: 1,
    proArguments: [
      {
        speaker: 'PRO',
        roundNumber: 1,
        roundLabel: 'ROUND 01 • PRO (AFFIRMATIVE)',
        title: 'Cognitive Automation & Rapid Labor Displacement',
        content:
          'Advanced generative models and autonomous agents can automate high-order reasoning, synthesis, and programming tasks at near-zero marginal cost. Historical automation replaced manual labor while expanding cognitive roles; modern AI directly targets cognitive work, outpacing the velocity of novel job creation in information sectors.',
      },
    ],
    conArguments: [
      {
        speaker: 'CON',
        roundNumber: 1,
        roundLabel: 'ROUND 01 • CON (CHALLENGING)',
        title: 'Jevons Paradox & High-Leverage Strategic Demand',
        content:
          'Technological revolutions consistently trigger the Jevons paradox: drastically reducing the cost of cognitive tasks expands total market demand and unlocks entirely new industries. Rather than replacing workers, agentic tools augment human judgment, shifting labor demand toward oversight, contextual evaluation, and multi-domain strategy.',
      },
    ],
    judgeWinner: 'DRAW',
    judgeProScore: null,
    judgeConScore: null,
    judgeVerdict:
      'Equally balanced on technological acceleration versus macro-economic absorption dynamics. Both sides present substantiated economic models without establishing unconditional dominance.',
    judgeReasoning:
      'PRO demonstrates that generative models compress entry-level knowledge workflows at unprecedented velocity. However, CON effectively illustrates historical labor adaptation and the emergence of high-leverage supervisory roles. Current empirical consensus indicates significant task transformation rather than catastrophic net job destruction.',
    judgeModel: 'Independent Dialectic Arbiter',
    judgeProvider: 'Multi-Agent Judicial Framework',
  },
  {
    id: 'illustrative-ai-education',
    topic: 'Should generative AI tutoring agents replace conventional standardized classroom instruction?',
    createdAt: 'Preview Dataset',
    documentName: null,
    documentId: null,
    isReal: false,
    roundsCount: 1,
    proArguments: [
      {
        speaker: 'PRO',
        roundNumber: 1,
        roundLabel: 'ROUND 01 • PRO (AFFIRMATIVE)',
        title: 'Personalized Pedagogical Adaptation & Mastery Learning',
        content:
          'AI tutors provide instantaneous 1-on-1 Socratic dialogue tailored to each student\'s mastery level and learning pace, overcoming the fundamental limitation of one-size-fits-all classrooms described in Bloom\'s 2 Sigma Problem.',
      },
    ],
    conArguments: [
      {
        speaker: 'CON',
        roundNumber: 1,
        roundLabel: 'ROUND 01 • CON (CHALLENGING)',
        title: 'Social Cognition, Mentorship & Epistemic Fragility',
        content:
          'Classroom education is fundamentally social and developmental. Over-reliance on AI tutors risks epistemic complacency, diminishes critical peer collaboration, and introduces subtle hallucinated misconceptions that unguided students cannot detect.',
      },
    ],
    judgeWinner: 'CON',
    judgeProScore: null,
    judgeConScore: null,
    judgeVerdict:
      'CON prevails by establishing that interpersonal social grounding and collaborative human mentorship are indispensable to holistic cognitive development.',
    judgeReasoning:
      'While PRO presents a compelling case for mastery-based personalization, CON substantiates critical developmental imperatives: human mentorship, peer dialectic, and the prevention of automated cognitive dependence. Hybrid models outperform complete replacement.',
    judgeModel: 'Independent Dialectic Arbiter',
    judgeProvider: 'Multi-Agent Judicial Framework',
  },
  {
    id: 'illustrative-transformer-architecture',
    topic: 'Are pure self-attention architectures superior to recurrent and convolutional neural networks for all sequence transduction tasks?',
    createdAt: 'Preview Dataset',
    documentName: null,
    documentId: null,
    isReal: false,
    roundsCount: 1,
    proArguments: [
      {
        speaker: 'PRO',
        roundNumber: 1,
        roundLabel: 'ROUND 01 • PRO (AFFIRMATIVE)',
        title: 'End-to-End Parallelization & Unbounded Context Routing',
        content:
          'Self-attention models eliminate recurrent sequential dependencies, allowing end-to-end tensor parallelization across GPUs and capturing arbitrary long-range token relationships in O(1) sequential steps, dominating natural language and multimodal benchmarks.',
      },
    ],
    conArguments: [
      {
        speaker: 'CON',
        roundNumber: 1,
        roundLabel: 'ROUND 01 • CON (CHALLENGING)',
        title: 'Quadratic Memory Scaling & Streaming Latency Bottlenecks',
        content:
          'Standard full self-attention scales quadratically O(n^2) with context length, imposing prohibitive memory overhead for real-time edge processing and infinite streaming audio/sensor streams where recurrent architectures maintain constant memory footprint.',
      },
    ],
    judgeWinner: 'PRO',
    judgeProScore: null,
    judgeConScore: null,
    judgeVerdict:
      'PRO wins on empirical performance dominance and scalability across foundation model benchmarks, though CON correctly identifies hardware memory boundary conditions.',
    judgeReasoning:
      'PRO successfully proves that Transformer parallelization and representation capacity outweigh recurrence on large-scale benchmarks. However, CON rightly notes that quadratic memory scaling necessitates state-space or linear attention approximations for extreme streaming contexts.',
    judgeModel: 'Independent Dialectic Arbiter',
    judgeProvider: 'Multi-Agent Judicial Framework',
  },
  {
    id: 'illustrative-renewable-energy',
    topic: 'Can a 100% renewable power grid maintain industrial-grade baseload reliability without nuclear fission?',
    createdAt: 'Preview Dataset',
    documentName: null,
    documentId: null,
    isReal: false,
    roundsCount: 1,
    proArguments: [
      {
        speaker: 'PRO',
        roundNumber: 1,
        roundLabel: 'ROUND 01 • PRO (AFFIRMATIVE)',
        title: 'Distributed Storage, Overbuilding & Dynamic Demand Response',
        content:
          'Rapid declines in battery storage costs, combined with geographically distributed wind-solar overbuilding, green hydrogen peakers, and smart dynamic demand response, can achieve five-nines grid reliability without the multi-decade capital lead times of nuclear plants.',
      },
    ],
    conArguments: [
      {
        speaker: 'CON',
        roundNumber: 1,
        roundLabel: 'ROUND 01 • CON (CHALLENGING)',
        title: 'Multi-Week Dunkelflaute Lulls & Land-Density Constraints',
        content:
          'Extended multi-week weather lulls (Dunkelflaute) require terawatt-hour duration storage that electrochemical batteries cannot economically sustain. Nuclear fission delivers high-energy-density, continuous zero-carbon baseload power independent of meteorology.',
      },
    ],
    judgeWinner: 'CON',
    judgeProScore: null,
    judgeConScore: null,
    judgeVerdict:
      'CON wins on grid resilience metrics during extended seasonal generation shortfalls and multi-week weather anomalies.',
    judgeReasoning:
      'CON establishes the technical bottleneck of long-duration seasonal intermittency under extreme weather anomalies. While PRO shows daily balancing feasibility, the macroeconomic cost of multi-week seasonal storage justifies firm nuclear baseload generation.',
    judgeModel: 'Independent Dialectic Arbiter',
    judgeProvider: 'Multi-Agent Judicial Framework',
  },
  {
    id: 'illustrative-data-privacy',
    topic: 'Does zero-knowledge cryptographic proof eliminate the need for centralized government identity registries?',
    createdAt: 'Preview Dataset',
    documentName: null,
    documentId: null,
    isReal: false,
    roundsCount: 1,
    proArguments: [
      {
        speaker: 'PRO',
        roundNumber: 1,
        roundLabel: 'ROUND 01 • PRO (AFFIRMATIVE)',
        title: 'Mathematical Self-Sovereignty & Zero Information Leakage',
        content:
          'Zero-knowledge cryptography (ZK-SNARKs) enables individuals to prove identity claims (such as age, citizenship, or regulatory accreditation) mathematically without exposing personal identifiers or creating honeypot centralized databases vulnerable to breach.',
      },
    ],
    conArguments: [
      {
        speaker: 'CON',
        roundNumber: 1,
        roundLabel: 'ROUND 01 • CON (CHALLENGING)',
        title: 'Attestation Roots of Trust & Civil Legal Recourse',
        content:
          'Cryptographic proofs require an authoritative root of trust for initial credential attestation. Without legal arbitration mechanisms and centralized verification infrastructure, decentralized identity systems cannot resolve credential theft, coercion, or Sybil attacks.',
      },
    ],
    judgeWinner: 'DRAW',
    judgeProScore: null,
    judgeConScore: null,
    judgeVerdict:
      'Neither side establishes total dominance: cryptographic privacy requires institutional trust anchors, and institutional registries require cryptographic safeguards.',
    judgeReasoning:
      'PRO demonstrates the unprecedented mathematical privacy guarantees of zero-knowledge verification, eliminating unnecessary data exposure. However, CON rightly demonstrates that initial attestation and civil recourse inherently require trusted institutional issuers. A dual-layer framework combining institutional roots with zero-knowledge presentation represents the viable equilibrium.',
    judgeModel: 'Independent Dialectic Arbiter',
    judgeProvider: 'Multi-Agent Judicial Framework',
  },
];

