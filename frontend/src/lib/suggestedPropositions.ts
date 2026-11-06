import { DocumentMetadata } from '../types/document';

/**
 * Extracts 3-5 sharp, document-grounded debate propositions strictly specific
 * to the selected document and its whole-document knowledge representation.
 * Completely eliminates generic/legal boilerplate for unrelated documents.
 */
export function getDocumentSuggestedPropositions(
  document: DocumentMetadata | null,
  knowledge: any | null
): string[] {
  if (!document) return [];

  const docName = (document.name || '').toLowerCase();
  const docId = document.id || '';
  const isImage = ['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes((document.fileType || '').toLowerCase());

  // 0. Use image-specific suggested propositions if available
  if (isImage && document.suggestedQuestions && document.suggestedQuestions.length > 0) {
    return document.suggestedQuestions;
  }

  // 1. Attention Is All You Need (Transformers research paper)
  if (
    docName.includes('attention') ||
    docName.includes('transformer') ||
    docId === 'b69f7cf1-68ae-48b0-94b5-468422800899' ||
    knowledge?.document_name?.toLowerCase().includes('attention')
  ) {
    return [
      'The Transformer architecture is superior to recurrent and convolutional neural networks for sequence transduction tasks.',
      'Self-attention eliminates the need for recurrence in sequence transduction, but introduces severe memory bottlenecks that make it inferior for long streaming contexts.',
      'Multi-head attention prevents attention from being dominated by a single averaging operation, enabling distinct representation subspaces.',
      'The big Transformer model\'s state-of-the-art BLEU score is driven primarily by parallel GPU training efficiency rather than architectural expressiveness.',
      'Restricted self-attention with local neighborhood r fails to preserve the global constant-time path length advantages of full self-attention.',
    ];
  }

  // 2. Autonomous Clinical Triage paper
  if (docName.includes('triage') || docName.includes('clinical') || docId === 'doc-triage') {
    return [
      'The 41-minute median latency reduction in ICU transfers justifies deploying automated Bayesian triage during respiratory surge.',
      'Algorithmic triage systems cannot safely replace bedside clinical gestalt due to systemic under-triage in atypical comorbid cohorts.',
      'Deterministic physiological stabilization floors adequately prevent premature ICU discharge in automated triage protocols.',
      'Non-delegable physician liability makes autonomous algorithmic triage rationing legally and ethically unacceptable.',
    ];
  }

  // 3. AI in High-Stakes Law paper
  if (docName.includes('law') || docName.includes('judicial') || docId === 'doc-ai-law') {
    return [
      'Autonomous Bayesian priors achieving a 32% reduction in sentencing variance justify replacing discretionary human panels in appellate liability rulings.',
      'Procedural due process demands non-delegable moral accountability that mathematical constraint solvers cannot constitutionally provide.',
      'A 91% false confidence rate on non-precedential black-swan dilemmas renders neural legal classifiers unfit for high-stakes adjudication.',
      'Coupling generative deliberation with formal SMT constraint solvers guarantees sufficient statutory compliance for judicial decision support.',
    ];
  }

  // 4. Dynamic extraction from active whole-document knowledge representation
  const propositions: string[] = [];

  if (knowledge) {
    // A. Use structured argument theses if available
    if (Array.isArray(knowledge.arguments) && knowledge.arguments.length > 0) {
      for (const arg of knowledge.arguments) {
        if (arg.claim && !propositions.includes(arg.claim)) {
          propositions.push(arg.claim);
        }
      }
    }

    // B. Use complexity and benchmark facts
    if (Array.isArray(knowledge.facts) && knowledge.facts.length > 0) {
      for (const fact of knowledge.facts) {
        if (fact.fact_statement && propositions.length < 5) {
          const prop = fact.fact_statement.endsWith('.') ? fact.fact_statement : `${fact.fact_statement}.`;
          if (!propositions.includes(prop)) {
            propositions.push(prop);
          }
        }
      }
    }

    // C. Use section takeaways
    if (Array.isArray(knowledge.sections) && knowledge.sections.length > 0 && propositions.length < 3) {
      for (const sec of knowledge.sections) {
        if (sec.key_takeaway && propositions.length < 5) {
          const prop = sec.key_takeaway;
          if (!propositions.includes(prop)) {
            propositions.push(prop);
          }
        }
      }
    }
  }

  // 5. Fallback for custom uploaded documents using document-specific metadata
  if (propositions.length === 0) {
    if (document.sections && document.sections.length > 0) {
      document.sections.forEach((sec) => {
        if (sec.summary && propositions.length < 4) {
          propositions.push(`Regarding ${sec.title}: ${sec.summary}`);
        }
      });
    }
  }

  if (propositions.length === 0) {
    return [
      `The empirical evidence presented in "${document.name}" substantiates its primary conclusions.`,
      `The methodological limitations identified in "${document.name}" undermine its general applicability.`,
      `The theoretical claims in "${document.name}" fail when applied outside controlled benchmark conditions.`,
    ];
  }

  return propositions.slice(0, 5);
}
