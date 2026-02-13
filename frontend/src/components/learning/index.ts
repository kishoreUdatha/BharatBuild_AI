/**
 * Learning Mode Components
 *
 * Components for the Learning Mode feature that:
 * 1. Explains code concepts during generation
 * 2. Quizzes students on what was generated
 * 3. Gates download until student demonstrates understanding
 */

export { FileExplanation, FileExplanationList } from './FileExplanation'
export type { FileExplanationData } from './FileExplanation'

export { ConceptQuiz } from './ConceptQuiz'
export type { QuizQuestion, QuizResult, QuizResultItem } from './ConceptQuiz'
